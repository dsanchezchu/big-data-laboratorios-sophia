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

# Configuración
MODEL_PATH = os.environ.get(
    "MODEL_PATH", "hdfs://namenode:9000/user/nifi/models/best_rf_calibrated"
)
DATA_PATH = os.environ.get(
    "DATA_PATH", "hdfs://namenode:9000/user/nifi/processed/dataset_ml_sophia_final"
)
SPARK_MASTER = os.environ.get("SPARK_MASTER", "spark://spark-master:7077")

st.set_page_config(
    page_title="Sistema de Ofertas Dinámicas - Sophia Labs",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="💊",
)

# CSS
st.markdown(
    """
<style>
    .oferta-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #0066cc;
        margin: 10px 0;
    }
    .precio-input {
        font-size: 18px;
        font-weight: bold;
        color: #0066cc;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ===============================================
# INICIALIZACIÓN
# ===============================================


@st.cache_resource(ttl=3600)
def init_spark():
    for i in range(20):
        try:
            spark = (
                SparkSession.builder.appName("streamlit-sophia-dinamico")
                .master(SPARK_MASTER)
                .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000")
                .getOrCreate()
            )
            return spark
        except Exception:
            time.sleep(3)
    raise RuntimeError("No se pudo conectar a Spark")


@st.cache_resource(ttl=3600)
def load_resources():
    df = spark.read.parquet(DATA_PATH).cache()
    try:
        model = PipelineModel.load(MODEL_PATH)
    except Exception:
        model = None

    # Cargar portafolio
    data_dir = "/home/jupyter/notebooks/data"
    try:
        df_portafolio = pd.read_parquet(
            os.path.join(data_dir, "portafolio_clientes.parquet")
        )
    except:
        df_portafolio = None

    return df, model, df_portafolio


spark = init_spark()
df_full, model, df_portafolio = load_resources()

if df_full is None:
    st.error("❌ No se pudo cargar el dataset desde HDFS.")
    st.stop()

if model is None:
    st.error("❌ Modelo no disponible. Ejecuta primero `proyecto.py`")
    st.stop()

# ===============================================
# FUNCIONES DE NEGOCIO
# ===============================================


def calcular_clientes_similares(cliente_objetivo, top_n=10):
    """Encuentra clientes con portafolio similar"""
    if df_portafolio is None:
        return []

    cliente_row = df_portafolio[df_portafolio["Cliente"] == cliente_objetivo]
    if cliente_row.empty:
        return []

    productos_objetivo = set(cliente_row.iloc[0]["productos_comprados"])

    similitudes = []
    for _, row in df_portafolio[
        df_portafolio["Cliente"] != cliente_objetivo
    ].iterrows():
        productos_otro = set(row["productos_comprados"])
        interseccion = len(productos_objetivo.intersection(productos_otro))
        union = len(productos_objetivo.union(productos_otro))

        if union > 0:
            similitud = interseccion / union
            similitudes.append({"cliente": row["Cliente"], "similitud": similitud})

    return sorted(similitudes, key=lambda x: x["similitud"], reverse=True)[:top_n]


def obtener_productos_candidatos(cliente_sel, zona, region):
    """Obtiene productos que el cliente NO ha comprado"""
    # Productos actuales del cliente
    if df_portafolio is not None:
        cliente_row = df_portafolio[df_portafolio["Cliente"] == cliente_sel]
        if not cliente_row.empty:
            productos_actuales = set(cliente_row.iloc[0]["productos_comprados"])
        else:
            productos_actuales = set()
    else:
        productos_actuales = set()

    # Clientes similares
    similares = calcular_clientes_similares(cliente_sel, top_n=10)

    if similares and df_portafolio is not None:
        nombres_similares = [s["cliente"] for s in similares]

        # Productos que similares compran
        productos_similares = set()
        for nombre in nombres_similares:
            row = df_portafolio[df_portafolio["Cliente"] == nombre]
            if not row.empty:
                productos_similares.update(row.iloc[0]["productos_comprados"])

        # Productos candidatos (NO comprados por el cliente)
        candidatos = list(productos_similares - productos_actuales)
    else:
        # Si no hay similares, usar productos populares de la zona
        productos_zona = (
            df_full.filter(col("Nombre_Zona") == zona)
            .groupBy("Producto")
            .agg(_sum("Venta_Cajas").alias("total"))
            .orderBy(desc("total"))
            .limit(50)
            .select("Producto")
            .collect()
        )

        candidatos = [
            row["Producto"]
            for row in productos_zona
            if row["Producto"] not in productos_actuales
        ]

    return candidatos[:20] if candidatos else []


def predecir_demanda_dinamica(
    cliente_sel, zona, region, producto, mes_sel, precio_caja
):
    """Predice demanda usando el modelo ML con parámetros dinámicos"""
    mes_num = [
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
    ].index(mes_sel) + 1

    # Obtener métricas base del producto en la zona
    metricas = (
        df_full.filter((col("Nombre_Zona") == zona) & (col("Producto") == producto))
        .select(
            "Venta_PY_Zona_Cajas",
            "Venta_PY_Familia_Cajas",
            "Meta_Zona_Cajas",
            "Precio_Promedio_PY_Caja",
        )
        .limit(1)
        .collect()
    )

    if metricas:
        venta_py_zona = metricas[0]["Venta_PY_Zona_Cajas"] or 0
        venta_py_familia = metricas[0]["Venta_PY_Familia_Cajas"] or 0
        meta_zona = metricas[0]["Meta_Zona_Cajas"] or 0
        precio_promedio_py = metricas[0]["Precio_Promedio_PY_Caja"] or precio_caja
    else:
        # Valores por defecto
        venta_py_zona = 10
        venta_py_familia = 50
        meta_zona = 20
        precio_promedio_py = precio_caja

    # Crear DataFrame para predicción
    data = [
        (
            cliente_sel,
            producto,
            zona,
            region,
            mes_sel,
            mes_num,
            float(precio_caja),
            float(venta_py_zona),
            float(venta_py_familia),
            float(meta_zona),
            float(precio_promedio_py),
        )
    ]

    columns = [
        "Cliente",
        "Producto",
        "Nombre_Zona",
        "Region",
        "Mes",
        "Mes_Num",
        "Precio_Caja",
        "Venta_PY_Zona_Cajas",
        "Venta_PY_Familia_Cajas",
        "Meta_Zona_Cajas",
        "Precio_Promedio_PY_Caja",
    ]

    df_pred = spark.createDataFrame(data, columns)

    # Predecir
    try:
        resultado = model.transform(df_pred)
        pred = resultado.select("prediction_final").collect()
        demanda_cajas = max(0, pred[0]["prediction_final"]) if pred else 0
    except Exception as e:
        st.error(f"Error en predicción: {e}")
        demanda_cajas = 10

    return demanda_cajas


def generar_descuentos_volumen(precio_base, demanda_base):
    """Genera escala de descuentos por volumen"""
    nivel_1 = int(demanda_base * 0.5) if demanda_base > 0 else 10
    nivel_2 = int(demanda_base * 1.0) if demanda_base > 0 else 25
    nivel_3 = int(demanda_base * 2.0) if demanda_base > 0 else 50

    return [
        {
            "nivel": "Básico",
            "desde": 1,
            "hasta": nivel_1,
            "descuento": 0,
            "precio": precio_base,
        },
        {
            "nivel": "Mayorista",
            "desde": nivel_1 + 1,
            "hasta": nivel_2,
            "descuento": 5,
            "precio": precio_base * 0.95,
        },
        {
            "nivel": "Corporativo",
            "desde": nivel_2 + 1,
            "hasta": 99999,
            "descuento": 10,
            "precio": precio_base * 0.90,
        },
    ]


# ===============================================
# SIDEBAR
# ===============================================

st.sidebar.title("⚙️ Configuración")
st.sidebar.markdown("---")

# Cliente
zonas_df = df_full.select("Nombre_Zona", "Cliente", "Region").distinct().toPandas()
clientes = sorted(zonas_df["Cliente"].unique().tolist())
cliente_sel = st.sidebar.selectbox("🏥 Cliente", clientes, key="cliente")

# Obtener zona y región
info_cliente = zonas_df[zonas_df["Cliente"] == cliente_sel].iloc[0]
zona = info_cliente["Nombre_Zona"]
region = info_cliente["Region"]

st.sidebar.info(f"📍 **Zona:** {zona}\n\n🗺️ **Región:** {region}")

st.sidebar.markdown("---")

# Mes
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
mes_sel = st.sidebar.select_slider(
    "📅 Mes de Proyección", options=meses, value="NOV", key="mes"
)

st.sidebar.markdown("---")

# Número de productos
num_productos = st.sidebar.slider("📦 Productos a mostrar", 3, 10, 5, key="num_prods")

# ===============================================
# HEADER
# ===============================================

st.title("💊 Sistema de Ofertas Dinámicas")
st.markdown("### Predicciones en Tiempo Real - Laboratorios Sophia")
st.markdown("---")

# ===============================================
# INFORMACIÓN DEL CLIENTE
# ===============================================

if df_portafolio is not None:
    cliente_info = df_portafolio[df_portafolio["Cliente"] == cliente_sel]
    if not cliente_info.empty:
        info = cliente_info.iloc[0]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            gasto = info.get("total_gasto", 0)
            categoria = (
                "GRANDE" if gasto > 50000 else "MEDIANO" if gasto > 20000 else "PEQUEÑO"
            )
            st.metric("🏥 Categoría", categoria)
        with col2:
            st.metric("💰 Gasto Histórico", f"S/. {gasto:,.0f}")
        with col3:
            st.metric(
                "📦 Volumen", f"{info.get('total_cajas_historicas', 0):,.0f} cajas"
            )
        with col4:
            st.metric("🛒 Productos", len(info.get("productos_comprados", [])))

st.markdown("---")

# ===============================================
# OBTENER PRODUCTOS CANDIDATOS
# ===============================================

with st.spinner("🔍 Identificando productos recomendados..."):
    productos_candidatos = obtener_productos_candidatos(cliente_sel, zona, region)

if not productos_candidatos:
    st.warning("⚠️ No se encontraron productos candidatos para este cliente")
    st.stop()

# ===============================================
# GENERAR OFERTAS DINÁMICAS
# ===============================================

st.header(f"🎯 Ofertas Personalizadas - {mes_sel} 2025")
st.markdown("💡 **Ajusta el precio y mes para ver predicciones en tiempo real**")

ofertas_dinamicas = []

for idx, producto in enumerate(productos_candidatos[:num_productos], 1):
    # Obtener precio base del mercado
    precio_mercado = (
        df_full.filter(col("Producto") == producto)
        .select(avg("Precio_Caja").alias("precio_avg"))
        .collect()
    )

    precio_base = (
        precio_mercado[0]["precio_avg"]
        if precio_mercado and precio_mercado[0]["precio_avg"]
        else 40.0
    )

    with st.expander(f"#{idx} - {producto}", expanded=(idx <= 3)):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("#### Parámetros de Oferta")

            # Input de precio (DINÁMICO)
            precio_oferta = st.number_input(
                "💰 Precio por Caja (S/.)",
                min_value=float(precio_base * 0.7),
                max_value=float(precio_base * 1.3),
                value=float(precio_base),
                step=0.5,
                key=f"precio_{idx}",
            )

            st.caption(f"Precio mercado: S/. {precio_base:.2f}")

            # Predecir demanda (SE ACTUALIZA CON EL PRECIO)
            demanda_cajas = predecir_demanda_dinamica(
                cliente_sel, zona, region, producto, mes_sel, precio_oferta
            )

            st.metric("📦 Demanda Predicha", f"{demanda_cajas:.0f} cajas")
            st.metric("💊 Piezas", f"{demanda_cajas * 20:.0f} unidades")

            valor_total = precio_oferta * demanda_cajas
            st.metric("💰 Valor Total", f"S/. {valor_total:,.2f}")

        with col2:
            st.markdown("#### Descuentos por Volumen")

            # Generar escala de descuentos
            descuentos = generar_descuentos_volumen(precio_oferta, demanda_cajas)

            df_desc = pd.DataFrame(descuentos)
            df_desc["Rango"] = df_desc.apply(
                lambda x: f"{x['desde']}-{x['hasta'] if x['hasta'] < 99999 else '∞'} cajas",
                axis=1,
            )
            df_desc["Descuento"] = df_desc["descuento"].apply(lambda x: f"{x}%")
            df_desc["Precio Final"] = df_desc["precio"].apply(lambda x: f"S/. {x:.2f}")

            st.dataframe(
                df_desc[["nivel", "Rango", "Descuento", "Precio Final"]],
                use_container_width=True,
                hide_index=True,
            )

            # Gráfico de precio vs volumen
            fig = px.line(
                df_desc,
                x=[d["desde"] for d in descuentos],
                y=[d["precio"] for d in descuentos],
                title="Curva de Precio por Volumen",
                labels={"x": "Cantidad (cajas)", "y": "Precio (S/.)"},
                markers=True,
            )
            fig.update_layout(height=250, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # Bonificación
        st.markdown("#### 🎁 Bonificación")
        col1, col2 = st.columns(2)
        with col1:
            st.success("Por cada **100 cajas** → **5 GRATIS** (5% ahorro)")
        with col2:
            if demanda_cajas >= 100:
                bonificacion = int(demanda_cajas / 100) * 5
                st.info(f"✅ En esta compra: **{bonificacion} cajas gratis**")

        ofertas_dinamicas.append(
            {
                "producto": producto,
                "precio": precio_oferta,
                "demanda": demanda_cajas,
                "valor": valor_total,
            }
        )

# ===============================================
# RESUMEN TOTAL
# ===============================================

st.markdown("---")
st.header("📊 Resumen de la Oferta")

total_cajas = sum(o["demanda"] for o in ofertas_dinamicas)
total_valor = sum(o["valor"] for o in ofertas_dinamicas)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📦 Total Cajas", f"{total_cajas:.0f}")
with col2:
    st.metric("💊 Total Piezas", f"{total_cajas * 20:.0f}")
with col3:
    st.metric("💰 Valor Total", f"S/. {total_valor:,.2f}")
with col4:
    precio_promedio = total_valor / total_cajas if total_cajas > 0 else 0
    st.metric("💵 Precio Promedio", f"S/. {precio_promedio:.2f}")

# Gráfico comparativo
st.subheader("Comparación de Productos")

df_resumen = pd.DataFrame(ofertas_dinamicas)
df_resumen["producto_corto"] = df_resumen["producto"].str[:30]

fig = go.Figure()
fig.add_trace(
    go.Bar(
        name="Valor Total",
        x=df_resumen["producto_corto"],
        y=df_resumen["valor"],
        marker_color="blue",
    )
)

fig.update_layout(
    title="Valor Estimado por Producto",
    xaxis_title="Producto",
    yaxis_title="Valor (S/.)",
    height=400,
)

st.plotly_chart(fig, use_container_width=True)

# ===============================================
# FOOTER
# ===============================================

st.markdown("---")
st.markdown(
    """
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><strong>Laboratorios Sophia</strong> | Sistema de Predicción Dinámica</p>
    <p>✨ Las predicciones se actualizan en tiempo real según precio y mes seleccionados</p>
</div>
""",
    unsafe_allow_html=True,
)
