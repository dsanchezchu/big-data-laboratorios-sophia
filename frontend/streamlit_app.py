import os
import time
import streamlit as st
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import lit, desc

MODEL_PATH = os.environ.get("MODEL_PATH", "hdfs://namenode:9000/user/nifi/models/best_rf_calibrated")
DATA_PATH  = os.environ.get("DATA_PATH",  "hdfs://namenode:9000/user/nifi/processed/dataset_ml_sophia_final")
SPARK_MASTER= os.environ.get("SPARK_MASTER","spark://spark-master:7077")

st.set_page_config(page_title="Recomendador RF - Sophia", layout="wide")

@st.cache_resource(ttl=3600)
def init_spark():
    for i in range(20):
        try:
            spark = SparkSession.builder \
                .appName("streamlit-frontend") \
                .master(SPARK_MASTER) \
                .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
                .getOrCreate()
            return spark
        except Exception as e:
            time.sleep(3)
    raise RuntimeError("No se pudo conectar a Spark")

spark = init_spark()

@st.cache_resource(ttl=3600)
def load_resources():
    df = spark.read.parquet(DATA_PATH).cache()
    try:
        model = PipelineModel.load(MODEL_PATH)
    except Exception:
        model = None
    return df, model

df_full, model = load_resources()

if df_full is None:
    st.error("No se pudo cargar el dataset desde HDFS.")
    st.stop()

# Cargar lista de zonas y clientes
zonas_df = df_full.select("Nombre_Zona", "Cliente").distinct().toPandas()
zonas = ["Todas"] + sorted(zonas_df["Nombre_Zona"].unique().tolist())

# Sidebar con configuración
st.sidebar.title("Configuración")
st.sidebar.write("**Año:** 2025")
st.sidebar.write("**Modelo:** " + MODEL_PATH)
st.sidebar.write("**Dataset:** " + DATA_PATH)
st.sidebar.markdown("---")

# Filtro por zona
zona_sel = st.sidebar.selectbox(
    "Zona",
    options=zonas,
    index=0,
    key="zona_selectbox"
)

# Filtrar clientes según zona seleccionada
if zona_sel == "Todas":
    clientes = sorted(zonas_df["Cliente"].unique().tolist())
else:
    clientes = sorted(zonas_df[zonas_df["Nombre_Zona"] == zona_sel]["Cliente"].unique().tolist())

# Widgets con keys únicos
cliente_sel = st.sidebar.selectbox(
    "Cliente", 
    options=clientes, 
    index=0,
    key="cliente_selectbox"
)

top_n = st.sidebar.slider(
    "Top N productos", 
    1, 20, 5,
    key="top_n_slider"
)

# Header principal
st.title("Recomendador - Random Forest")
st.markdown("### Sistema de Recomendación de Productos - Sophia Labs")
st.markdown("---")

# Información del cliente seleccionado
st.markdown("#### Cliente seleccionado")
st.info(f"**{cliente_sel}**")

# Obtener información del cliente para mostrar contexto
info = df_full.filter(df_full.Cliente == cliente_sel).select("Region","Nombre_Zona").limit(1).collect()

if not info:
    st.error("Cliente no encontrado")
    st.stop()

region = info[0]["Region"]
zona = info[0]["Nombre_Zona"]

# Mostrar contexto del cliente
st.success(f"Zona: {zona} | Región: {region}")

# Lista de meses para la barra de selección
meses = ["ENE","FEB","MAR","ABR","MAY","JUN","JUL","AGO","SEP","OCT","NOV","DIC"]

# Selector de mes como barra horizontal
st.markdown("---")
st.markdown("### Seleccione el mes para generar recomendaciones")
mes_sel = st.radio(
    "Mes",
    options=meses,
    index=9,  # OCT por defecto
    horizontal=True,
    key="mes_radio",
    label_visibility="collapsed"
)

mes_num = meses.index(mes_sel) + 1

# Botón de generación
if st.button("Generar recomendaciones", key="generar_button"):
    with st.spinner("Generando recomendaciones..."):
        # Preparar catálogo
        catalogo = df_full.select(
            "Producto","Precio_Caja","ID_Articulo",
            "Venta_PY_Zona_Cajas","Venta_PY_Familia_Cajas",
            "Meta_Zona_Cajas","Precio_Promedio_PY_Caja"
        ).dropDuplicates(["Producto"]).orderBy(desc("Venta_PY_Zona_Cajas")).limit(200)
        
        df_sim = catalogo.withColumn("Cliente", lit(cliente_sel)) \
                         .withColumn("Region", lit(region)) \
                         .withColumn("Nombre_Zona", lit(zona)) \
                         .withColumn("Mes", lit(mes_sel)) \
                         .withColumn("Mes_Num", lit(mes_num))
        
        if model is None:
            st.warning("Modelo no cargado. Mostrando catálogo sin predicción.")
            df_out = df_sim.toPandas()
            st.dataframe(df_out.head(top_n), use_container_width=True)
        else:
            # Ejecutar predicciones
            preds = model.transform(df_sim)
            cols = ["Producto","Precio_Caja","prediction_final","prediction_piezas"]
            pdf = preds.select(*cols).orderBy(desc("prediction_final")).limit(top_n).toPandas()
            
            # Calcular ingreso estimado
            pdf["ingreso_estimado"] = pdf["Precio_Caja"] * pdf["prediction_final"]
            pdf = pdf.round(2)
            
            # Renombrar columnas para mejor visualización
            pdf_display = pdf.rename(columns={
                "Producto": "Producto",
                "Precio_Caja": "Precio/Caja",
                "prediction_final": "Demanda (Cajas)",
                "prediction_piezas": "Demanda (Piezas)",
                "ingreso_estimado": "Ingreso Estimado"
            })
            
            # Tabs para diferentes vistas
            tab1, tab2, tab3 = st.tabs(["Tabla", "Gráficos", "Análisis de Ingresos"])
            
            with tab1:
                st.subheader(f"Top {top_n} Productos Recomendados - {mes_sel} 2025")
                st.dataframe(
                    pdf_display,
                    use_container_width=True,
                    hide_index=True
                )
            
            with tab2:
                st.subheader("Demanda Estimada por Producto")
                
                # Gráfico de barras
                st.markdown("##### Gráfico de Barras")
                st.bar_chart(
                    pdf.set_index("Producto")["prediction_final"],
                    use_container_width=True
                )
                
                # Gráfico lineal
                st.markdown("##### Tendencia de Demanda")
                st.line_chart(
                    pdf.set_index("Producto")["prediction_final"],
                    use_container_width=True
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Total Cajas Estimadas",
                        f"{pdf['prediction_final'].sum():.0f}"
                    )
                with col2:
                    st.metric(
                        "Precio Promedio",
                        f"${pdf['Precio_Caja'].mean():.2f}"
                    )
            
            with tab3:
                st.subheader("Ingreso Estimado por Producto")
                pdf_ingresos = pdf[["Producto","ingreso_estimado"]].sort_values(
                    "ingreso_estimado", 
                    ascending=False
                )
                
                st.bar_chart(
                    pdf_ingresos.set_index("Producto")["ingreso_estimado"],
                    use_container_width=True
                )
                
                st.metric(
                    "Ingreso Total Estimado",
                    f"${pdf['ingreso_estimado'].sum():,.2f}"
                )
                
                st.table(pdf_ingresos)

# Footer
st.markdown("---")
st.markdown("**Sophia Labs** | Sistema de Recomendación con Random Forest")