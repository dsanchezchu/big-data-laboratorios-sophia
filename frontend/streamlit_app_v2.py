import os
import time
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import (
    lit,
    desc,
    col,
    collect_list,
    explode,
    count,
    sum as _sum,
    avg,
)

# Configuración de rutas
MODEL_PATH = os.environ.get(
    "MODEL_PATH", "hdfs://namenode:9000/user/nifi/models/best_rf_calibrated"
)
DATA_PATH = os.environ.get(
    "DATA_PATH", "hdfs://namenode:9000/user/nifi/processed/dataset_ml_sophia_final"
)
SPARK_MASTER = os.environ.get("SPARK_MASTER", "spark://spark-master:7077")

st.set_page_config(
    page_title="Sistema de Recomendación - Sophia Labs",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===============================================
# FUNCIONES DE INICIALIZACIÓN
# ===============================================


@st.cache_resource(ttl=3600)
def init_spark():
    for i in range(20):
        try:
            spark = (
                SparkSession.builder.appName("streamlit-sophia-recomendador")
                .master(SPARK_MASTER)
                .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000")
                .getOrCreate()
            )
            return spark
        except Exception as e:
            time.sleep(3)
    raise RuntimeError("No se pudo conectar a Spark")


@st.cache_resource(ttl=3600)
def load_resources():
    df = spark.read.parquet(DATA_PATH).cache()
    try:
        model = PipelineModel.load(MODEL_PATH)
    except Exception:
        model = None

    # Cargar archivos auxiliares si existen
    data_dir = "/home/jupyter/notebooks/data"
    try:
        df_similares = pd.read_parquet(
            os.path.join(data_dir, "clientes_similares.parquet")
        )
        df_portafolio = pd.read_parquet(
            os.path.join(data_dir, "portafolio_clientes.parquet")
        )
        df_catalogo = pd.read_parquet(
            os.path.join(data_dir, "catalogo_metricas.parquet")
        )
    except:
        df_similares = None
        df_portafolio = None
        df_catalogo = None

    return df, model, df_similares, df_portafolio, df_catalogo


# ===============================================
# FUNCIONES DE ANÁLISIS
# ===============================================


def calcular_clientes_similares(cliente_objetivo, df_portafolio, top_n=5):
    """Calcula clientes similares basándose en el portafolio"""
    if df_portafolio is None:
        return []

    # Obtener productos del cliente objetivo
    cliente_row = df_portafolio[df_portafolio["Cliente"] == cliente_objetivo]
    if cliente_row.empty:
        return []

    productos_objetivo = set(cliente_row.iloc[0]["productos_comprados"])

    # Calcular similitud con otros clientes
    similitudes = []
    for _, row in df_portafolio[
        df_portafolio["Cliente"] != cliente_objetivo
    ].iterrows():
        productos_otro = set(row["productos_comprados"])
        interseccion = len(productos_objetivo.intersection(productos_otro))
        union = len(productos_objetivo.union(productos_otro))

        if union > 0:
            similitud = interseccion / union
            similitudes.append(
                {
                    "cliente": row["Cliente"],
                    "similitud": similitud,
                    "productos_comunes": interseccion,
                    "total_gasto": row.get("total_gasto", 0),
                }
            )

    return sorted(similitudes, key=lambda x: x["similitud"], reverse=True)[:top_n]


def obtener_productos_no_comprados(cliente_objetivo, df_full_spark, df_portafolio):
    """Identifica productos que el cliente NO ha comprado"""
    # Productos del cliente
    cliente_row = df_portafolio[df_portafolio["Cliente"] == cliente_objetivo]
    if cliente_row.empty:
        return []

    productos_actuales = set(cliente_row.iloc[0]["productos_comprados"])

    # Catálogo completo
    catalogo_completo = df_full_spark.select("Producto").distinct().collect()
    catalogo_lista = [row["Producto"] for row in catalogo_completo]

    # Productos NO comprados
    productos_nuevos = [p for p in catalogo_lista if p not in productos_actuales]

    return productos_nuevos


# ===============================================
# INICIALIZACIÓN
# ===============================================

spark = init_spark()
df_full, model, df_similares, df_portafolio, df_catalogo = load_resources()

if df_full is None:
    st.error("❌ No se pudo cargar el dataset desde HDFS.")
    st.stop()

# ===============================================
# SIDEBAR
# ===============================================

st.sidebar.image(
    "https://via.placeholder.com/200x80/0066CC/FFFFFF?text=Sophia+Labs",
    use_container_width=True,
)
st.sidebar.title("⚙️ Configuración")
st.sidebar.markdown("---")

# Información del sistema
with st.sidebar.expander("📊 Info del Sistema"):
    st.write(f"**Modelo:** Random Forest Regressor")
    st.write(f"**Registros:** {df_full.count():,}")
    st.write(f"**Spark Master:** {SPARK_MASTER}")

# Filtros principales
zonas_df = df_full.select("Nombre_Zona", "Cliente").distinct().toPandas()
zonas = ["Todas"] + sorted(zonas_df["Nombre_Zona"].unique().tolist())

zona_sel = st.sidebar.selectbox("🌍 Zona", options=zonas, index=0)

if zona_sel == "Todas":
    clientes = sorted(zonas_df["Cliente"].unique().tolist())
else:
    clientes = sorted(
        zonas_df[zonas_df["Nombre_Zona"] == zona_sel]["Cliente"].unique().tolist()
    )

cliente_sel = st.sidebar.selectbox("🏥 Cliente", options=clientes, index=0)

st.sidebar.markdown("---")

# Selector de mes
meses = [
    "ENE",
    "FEB",
    "MAR",
    "ABR",
    "MAY",
    "JUN",
    "JUL",
    "AGO",
    "SEP",
    "OCT",
    "NOV",
    "DIC",
]
mes_sel = st.sidebar.select_slider("📅 Mes de Proyección", options=meses, value="OCT")
mes_num = meses.index(mes_sel) + 1

# Parámetros de recomendación
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Parámetros")
top_n = st.sidebar.slider("Top N Productos", 5, 50, 10)
mostrar_solo_nuevos = st.sidebar.checkbox("Solo productos NO comprados", value=True)

# ===============================================
# HEADER PRINCIPAL
# ===============================================

st.title("🏥 Sistema de Recomendación de Productos")
st.markdown(
    "### Laboratorios Sophia - Análisis Predictivo y Recomendaciones Personalizadas"
)
st.markdown("---")

# ===============================================
# INFORMACIÓN DEL CLIENTE
# ===============================================

info_cliente = (
    df_full.filter(df_full.Cliente == cliente_sel)
    .select("Region", "Nombre_Zona")
    .limit(1)
    .collect()
)

if not info_cliente:
    st.error(f"❌ Cliente '{cliente_sel}' no encontrado")
    st.stop()

region = info_cliente[0]["Region"]
zona = info_cliente[0]["Nombre_Zona"]

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        "🏥 Cliente", cliente_sel[:30] + "..." if len(cliente_sel) > 30 else cliente_sel
    )
with col2:
    st.metric("🌍 Zona", zona)
with col3:
    st.metric("📍 Región", region)

st.markdown("---")

# ===============================================
# TABS PRINCIPALES
# ===============================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🎯 Recomendaciones",
        "👥 Clientes Similares",
        "📊 Análisis de Portafolio",
        "💰 Optimización de Precios",
        "📈 Proyección de Demanda",
    ]
)

# ===============================================
# TAB 1: RECOMENDACIONES
# ===============================================

with tab1:
    st.header("🎯 Productos Recomendados")
    st.markdown(f"**Mes de proyección:** {mes_sel} 2025")

    if st.button(
        "🚀 Generar Recomendaciones", type="primary", use_container_width=True
    ):
        with st.spinner("Generando recomendaciones inteligentes..."):
            # Obtener productos que el cliente NO ha comprado
            if mostrar_solo_nuevos and df_portafolio is not None:
                productos_no_comprados = obtener_productos_no_comprados(
                    cliente_sel, df_full, df_portafolio
                )

                if not productos_no_comprados:
                    st.warning(
                        "⚠️ El cliente ya ha comprado todos los productos del catálogo"
                    )
                    productos_no_comprados = None
            else:
                productos_no_comprados = None

            # Preparar catálogo
            catalogo = df_full.select(
                "Producto",
                "Precio_Caja",
                "ID_Articulo",
                "Venta_PY_Zona_Cajas",
                "Venta_PY_Familia_Cajas",
                "Meta_Zona_Cajas",
                "Precio_Promedio_PY_Caja",
            ).dropDuplicates(["Producto"])

            # Filtrar solo productos NO comprados si está activado
            if productos_no_comprados:
                catalogo = catalogo.filter(col("Producto").isin(productos_no_comprados))

            catalogo = catalogo.orderBy(desc("Venta_PY_Zona_Cajas")).limit(200)

            # Crear simulación
            df_sim = (
                catalogo.withColumn("Cliente", lit(cliente_sel))
                .withColumn("Region", lit(region))
                .withColumn("Nombre_Zona", lit(zona))
                .withColumn("Mes", lit(mes_sel))
                .withColumn("Mes_Num", lit(mes_num))
            )

            if model is None:
                st.error("❌ Modelo no disponible")
            else:
                # Ejecutar predicciones
                preds = model.transform(df_sim)
                pdf = (
                    preds.select(
                        "Producto",
                        "Precio_Caja",
                        "prediction_final",
                        "prediction_piezas",
                        "Venta_PY_Zona_Cajas",
                    )
                    .orderBy(desc("prediction_final"))
                    .limit(top_n)
                    .toPandas()
                )

                # Calcular métricas
                pdf["ingreso_estimado"] = pdf["Precio_Caja"] * pdf["prediction_final"]
                pdf["potencial_crecimiento"] = (
                    (pdf["prediction_final"] - pdf["Venta_PY_Zona_Cajas"])
                    / (pdf["Venta_PY_Zona_Cajas"] + 1)
                    * 100
                )

                # Métricas resumen
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📦 Total Cajas", f"{pdf['prediction_final'].sum():.0f}")
                with col2:
                    st.metric(
                        "💰 Ingreso Estimado",
                        f"S/. {pdf['ingreso_estimado'].sum():,.0f}",
                    )
                with col3:
                    st.metric(
                        "📈 Precio Promedio", f"S/. {pdf['Precio_Caja'].mean():.2f}"
                    )
                with col4:
                    st.metric("🎯 Productos", len(pdf))

                st.markdown("---")

                # Tabla de recomendaciones
                st.subheader("📋 Detalle de Recomendaciones")
                pdf_display = pdf.copy()
                pdf_display = pdf_display.rename(
                    columns={
                        "Producto": "Producto",
                        "Precio_Caja": "Precio/Caja (S/.)",
                        "prediction_final": "Demanda (Cajas)",
                        "prediction_piezas": "Demanda (Piezas)",
                        "ingreso_estimado": "Ingreso Est. (S/.)",
                        "potencial_crecimiento": "Crecimiento vs PY (%)",
                    }
                )

                # Formatear números
                pdf_display["Precio/Caja (S/.)"] = pdf_display[
                    "Precio/Caja (S/.)"
                ].round(2)
                pdf_display["Demanda (Cajas)"] = pdf_display["Demanda (Cajas)"].round(0)
                pdf_display["Demanda (Piezas)"] = pdf_display["Demanda (Piezas)"].round(
                    0
                )
                pdf_display["Ingreso Est. (S/.)"] = pdf_display[
                    "Ingreso Est. (S/.)"
                ].round(2)
                pdf_display["Crecimiento vs PY (%)"] = pdf_display[
                    "Crecimiento vs PY (%)"
                ].round(1)

                st.dataframe(pdf_display, use_container_width=True, hide_index=True)

                # Gráficos
                st.markdown("---")
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📊 Demanda Estimada")
                    fig1 = px.bar(
                        pdf.head(10),
                        x="Producto",
                        y="prediction_final",
                        title=f"Top 10 Productos - Demanda Proyectada ({mes_sel})",
                        labels={"prediction_final": "Cajas", "Producto": "Producto"},
                        color="prediction_final",
                        color_continuous_scale="Blues",
                    )
                    fig1.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig1, use_container_width=True)

                with col2:
                    st.subheader("💰 Ingreso Estimado")
                    fig2 = px.bar(
                        pdf.head(10),
                        x="Producto",
                        y="ingreso_estimado",
                        title="Ingreso Proyectado por Producto",
                        labels={
                            "ingreso_estimado": "Ingresos (S/.)",
                            "Producto": "Producto",
                        },
                        color="ingreso_estimado",
                        color_continuous_scale="Greens",
                    )
                    fig2.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig2, use_container_width=True)

# ===============================================
# TAB 2: CLIENTES SIMILARES
# ===============================================

with tab2:
    st.header("👥 Análisis de Clientes Similares")
    st.markdown(
        "**Identificación de oportunidades basadas en clientes con perfiles similares**"
    )

    if df_portafolio is not None:
        similares = calcular_clientes_similares(cliente_sel, df_portafolio, top_n=10)

        if similares:
            # Tabla de clientes similares
            df_similares_display = pd.DataFrame(similares)
            df_similares_display["similitud"] = (
                df_similares_display["similitud"] * 100
            ).round(1)
            df_similares_display = df_similares_display.rename(
                columns={
                    "cliente": "Cliente Similar",
                    "similitud": "Similitud (%)",
                    "productos_comunes": "Productos en Común",
                    "total_gasto": "Gasto Total (S/.)",
                }
            )

            st.subheader("🎯 Top 10 Clientes Más Similares")
            st.dataframe(
                df_similares_display, use_container_width=True, hide_index=True
            )

            # Gráfico de similitud
            fig = px.bar(
                df_similares_display.head(5),
                x="Cliente Similar",
                y="Similitud (%)",
                title="Índice de Similitud (Top 5)",
                color="Similitud (%)",
                color_continuous_scale="Viridis",
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            st.info(
                "💡 **Insight:** Estos clientes tienen patrones de compra similares. Los productos que ellos compran son candidatos ideales para recomendar."
            )
        else:
            st.warning("⚠️ No se encontraron clientes similares")
    else:
        st.warning(
            "⚠️ Datos de portafolio no disponibles. Ejecuta primero `modelo_mejorado_v2.py`"
        )

# ===============================================
# TAB 3: ANÁLISIS DE PORTAFOLIO
# ===============================================

with tab3:
    st.header("📊 Análisis de Portafolio Actual")

    if df_portafolio is not None:
        cliente_info = df_portafolio[df_portafolio["Cliente"] == cliente_sel]

        if not cliente_info.empty:
            info = cliente_info.iloc[0]

            # Métricas del cliente
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📦 Productos Comprados", len(info["productos_comprados"]))
            with col2:
                st.metric("💰 Gasto Total", f"S/. {info.get('total_gasto', 0):,.0f}")
            with col3:
                st.metric("📊 Transacciones", f"{info.get('num_transacciones', 0):,}")
            with col4:
                st.metric(
                    "💵 Precio Promedio",
                    f"S/. {info.get('precio_promedio_pagado', 0):.2f}",
                )

            # Lista de productos
            st.subheader("🛒 Productos en Portafolio")
            productos_list = info["productos_comprados"]
            df_productos = pd.DataFrame({"Producto": productos_list})

            # Enriquecer con datos del catálogo si está disponible
            if df_catalogo is not None:
                df_productos = df_productos.merge(
                    df_catalogo[
                        ["Producto", "precio_promedio", "demanda_total_historica"]
                    ],
                    on="Producto",
                    how="left",
                )
                df_productos = df_productos.rename(
                    columns={
                        "precio_promedio": "Precio Prom. (S/.)",
                        "demanda_total_historica": "Demanda Total",
                    }
                )

            st.dataframe(df_productos, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ No se encontró información de portafolio para este cliente")
    else:
        st.warning("⚠️ Datos de portafolio no disponibles")

# ===============================================
# TAB 4: OPTIMIZACIÓN DE PRECIOS
# ===============================================

with tab4:
    st.header("💰 Análisis de Elasticidad y Optimización de Precios")
    st.markdown("**Simulación de escenarios de precios para maximizar ingresos**")

    # Selector de producto
    productos_cliente = (
        df_full.filter(col("Cliente") == cliente_sel)
        .select("Producto")
        .distinct()
        .limit(50)
        .collect()
    )
    productos_lista = [row["Producto"] for row in productos_cliente]

    if productos_lista:
        producto_sel = st.selectbox("📦 Seleccionar Producto", productos_lista)

        if st.button("🔍 Analizar Elasticidad", use_container_width=True):
            with st.spinner("Simulando escenarios de precios..."):
                # Obtener precio actual
                precio_info = (
                    df_full.filter(
                        (col("Cliente") == cliente_sel)
                        & (col("Producto") == producto_sel)
                    )
                    .select("Precio_Caja")
                    .limit(1)
                    .collect()
                )

                if precio_info:
                    precio_base = precio_info[0]["Precio_Caja"]

                    # Generar escenarios (-30% a +30%)
                    ajustes = list(range(-30, 35, 5))
                    resultados = []

                    for ajuste in ajustes:
                        nuevo_precio = precio_base * (1 + ajuste / 100)

                        # Crear escenario
                        df_escenario = (
                            df_full.filter(
                                (col("Cliente") == cliente_sel)
                                & (col("Producto") == producto_sel)
                            )
                            .limit(1)
                            .withColumn("Precio_Caja", lit(nuevo_precio))
                            .withColumn("Mes", lit(mes_sel))
                            .withColumn("Mes_Num", lit(mes_num))
                        )

                        # Predecir
                        if model:
                            pred = (
                                model.transform(df_escenario)
                                .select("prediction_final")
                                .collect()
                            )
                            if pred:
                                demanda = pred[0]["prediction_final"]
                                ingreso = nuevo_precio * demanda

                                resultados.append(
                                    {
                                        "Ajuste (%)": ajuste,
                                        "Precio (S/.)": nuevo_precio,
                                        "Demanda (Cajas)": demanda,
                                        "Ingreso (S/.)": ingreso,
                                    }
                                )

                    if resultados:
                        df_resultados = pd.DataFrame(resultados)

                        # Encontrar óptimo
                        idx_optimo = df_resultados["Ingreso (S/.)"].idxmax()
                        optimo = df_resultados.iloc[idx_optimo]

                        # Mostrar recomendación
                        st.success(
                            f"🏆 **Precio Óptimo:** S/. {optimo['Precio (S/.)']: .2f} ({optimo['Ajuste (%)']:+.0f}%)"
                        )
                        st.info(
                            f"📈 **Ingreso Máximo:** S/. {optimo['Ingreso (S/.)']: ,.2f} | **Demanda:** {optimo['Demanda (Cajas)']:.0f} cajas"
                        )

                        # Gráficos
                        col1, col2 = st.columns(2)

                        with col1:
                            fig1 = px.line(
                                df_resultados,
                                x="Precio (S/.)",
                                y="Demanda (Cajas)",
                                title="Curva de Demanda",
                                markers=True,
                            )
                            fig1.add_vline(
                                x=precio_base,
                                line_dash="dash",
                                line_color="red",
                                annotation_text="Precio Actual",
                            )
                            fig1.add_vline(
                                x=optimo["Precio (S/.)"],
                                line_dash="dash",
                                line_color="green",
                                annotation_text="Óptimo",
                            )
                            st.plotly_chart(fig1, use_container_width=True)

                        with col2:
                            fig2 = px.line(
                                df_resultados,
                                x="Precio (S/.)",
                                y="Ingreso (S/.)",
                                title="Curva de Ingresos",
                                markers=True,
                            )
                            fig2.add_vline(
                                x=precio_base, line_dash="dash", line_color="red"
                            )
                            fig2.add_vline(
                                x=optimo["Precio (S/.)"],
                                line_dash="dash",
                                line_color="green",
                            )
                            st.plotly_chart(fig2, use_container_width=True)

                        # Tabla de escenarios
                        st.subheader("📊 Tabla de Escenarios")
                        st.dataframe(
                            df_resultados, use_container_width=True, hide_index=True
                        )
    else:
        st.warning("⚠️ No hay productos en el historial de este cliente")

# ===============================================
# TAB 5: PROYECCIÓN DE DEMANDA
# ===============================================

with tab5:
    st.header("📈 Proyección de Demanda Multi-Periodo")
    st.markdown("**Proyección de demanda para los próximos 12 meses**")

    if st.button("🚀 Generar Proyección Anual", use_container_width=True):
        with st.spinner("Calculando proyecciones..."):
            # Seleccionar top 5 productos del cliente
            top_productos = (
                df_full.filter(col("Cliente") == cliente_sel)
                .groupBy("Producto")
                .agg(_sum("Venta_Cajas").alias("total"))
                .orderBy(desc("total"))
                .limit(5)
                .collect()
            )

            if top_productos:
                proyecciones = []

                for mes_idx, mes in enumerate(meses, 1):
                    for prod_row in top_productos:
                        producto = prod_row["Producto"]

                        # Crear escenario
                        df_escenario = (
                            df_full.filter(
                                (col("Cliente") == cliente_sel)
                                & (col("Producto") == producto)
                            )
                            .limit(1)
                            .withColumn("Mes", lit(mes))
                            .withColumn("Mes_Num", lit(mes_idx))
                        )

                        # Predecir
                        if model:
                            pred = (
                                model.transform(df_escenario)
                                .select("prediction_final")
                                .collect()
                            )
                            if pred:
                                demanda = pred[0]["prediction_final"]
                                proyecciones.append(
                                    {
                                        "Mes": mes,
                                        "Producto": producto,
                                        "Demanda (Cajas)": demanda,
                                    }
                                )

                if proyecciones:
                    df_proy = pd.DataFrame(proyecciones)

                    # Gráfico de tendencia
                    fig = px.line(
                        df_proy,
                        x="Mes",
                        y="Demanda (Cajas)",
                        color="Producto",
                        title="Proyección de Demanda Anual - Top 5 Productos",
                        markers=True,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Tabla pivote
                    df_pivot = df_proy.pivot(
                        index="Producto", columns="Mes", values="Demanda (Cajas)"
                    )
                    st.subheader("📊 Tabla de Proyecciones")
                    st.dataframe(df_pivot, use_container_width=True)
            else:
                st.warning("⚠️ No hay suficientes datos para generar proyecciones")

# ===============================================
# FOOTER
# ===============================================

st.markdown("---")
st.markdown(
    """
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><strong>Laboratorios Sophia</strong> | Sistema de Recomendación Inteligente</p>
    <p>Modelo: Random Forest Regressor | Tecnología: Apache Spark + Streamlit</p>
</div>
""",
    unsafe_allow_html=True,
)
