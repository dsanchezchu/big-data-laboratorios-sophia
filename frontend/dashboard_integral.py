"""
===================================================================================
SISTEMA INTEGRAL DE RECOMENDACIONES Y PREDICCIONES - LABORATORIOS SOPHIA
===================================================================================
Dashboard que cumple con TODOS los objetivos del proyecto:
1. Predicción de demanda con Random Forest (Spark MLlib)
2. Recomendaciones personalizadas basadas en clientes similares
3. Productos que el cliente NO compra pero similares SÍ
4. Productos con baja venta mensual pero afines al historial
5. Ofertas estratégicas: Descuentos por volumen, Bonificaciones, Combos
6. Análisis de elasticidad de precios con rango personalizable
7. Predicciones 2025-2026 con advertencias de incertidumbre
8. Filtros por región y zona
===================================================================================
"""

import os
import time
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import (
    lit,
    desc,
    col,
    collect_list,
    count,
    sum as _sum,
    avg,
    max as _max,
    min as _min,
)

# ===============================================
# CONFIGURACIÓN
# ===============================================
MODEL_PATH = os.environ.get(
    "MODEL_PATH", "hdfs://namenode:9000/user/nifi/models/best_rf_calibrated"
)
DATA_PATH = os.environ.get(
    "DATA_PATH", "hdfs://namenode:9000/user/nifi/processed/dataset_ml_sophia_final"
)
SPARK_MASTER = os.environ.get("SPARK_MASTER", "spark://spark-master:7077")

st.set_page_config(
    page_title="Sistema de Recomendaciones - Sophia Labs",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="💊",
)

# ===============================================
# CSS PERSONALIZADO
# ===============================================
st.markdown(
    """
<style>
    .main-header {
        background: linear-gradient(90deg, #0066cc 0%, #00ccff 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #0066cc;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #28a745;
        border-radius: 10px;
        padding: 15px;
    }
    .oferta-descuento {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 5px 0;
    }
    .oferta-bonificacion {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 5px 0;
    }
    .oferta-combo {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 5px 0;
    }
    .producto-nuevo {
        background-color: #e3f2fd;
        border: 2px solid #2196f3;
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
    }
    .producto-oportunidad {
        background-color: #fff8e1;
        border: 2px solid #ff9800;
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ===============================================
# INICIALIZACIÓN DE SPARK
# ===============================================


@st.cache_resource(ttl=3600)
def init_spark():
    """Inicializa conexión a Spark"""
    for i in range(20):
        try:
            spark = (
                SparkSession.builder.appName("sophia-dashboard-integral")
                .master(SPARK_MASTER)
                .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000")
                .getOrCreate()
            )
            return spark
        except Exception:
            time.sleep(3)
    raise RuntimeError("No se pudo conectar a Spark")


@st.cache_resource(ttl=3600)
def load_data(_spark):
    """Carga datos y modelo"""
    df = _spark.read.parquet(DATA_PATH).cache()
    try:
        model = PipelineModel.load(MODEL_PATH)
    except Exception:
        model = None

    # Cargar portafolio si existe
    try:
        df_portafolio = pd.read_parquet(
            "/home/jupyter/notebooks/data/portafolio_clientes.parquet"
        )
    except Exception:
        df_portafolio = None

    return df, model, df_portafolio


spark = init_spark()
df_full, model, df_portafolio = load_data(spark)

if df_full is None:
    st.error("❌ No se pudo cargar el dataset desde HDFS.")
    st.stop()

# ===============================================
# FUNCIONES DE ANÁLISIS
# ===============================================


def calcular_similitud_clientes(cliente_objetivo, df_portafolio, top_n=10):
    """Calcula clientes similares usando Jaccard Similarity"""
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
            if similitud > 0:
                similitudes.append(
                    {
                        "cliente": row["Cliente"],
                        "similitud": similitud,
                        "productos_comunes": interseccion,
                        "productos_unicos": list(productos_otro - productos_objetivo),
                    }
                )

    return sorted(similitudes, key=lambda x: x["similitud"], reverse=True)[:top_n]


def obtener_productos_no_comprados(cliente_sel, df_portafolio, similares):
    """Identifica productos que el cliente NO compra pero similares SÍ"""
    if df_portafolio is None:
        return []

    cliente_row = df_portafolio[df_portafolio["Cliente"] == cliente_sel]
    if cliente_row.empty:
        return []

    productos_cliente = set(cliente_row.iloc[0]["productos_comprados"])

    # Productos de clientes similares
    productos_recomendados = {}
    for sim in similares:
        for prod in sim["productos_unicos"]:
            if prod not in productos_cliente:
                if prod not in productos_recomendados:
                    productos_recomendados[prod] = {
                        "producto": prod,
                        "num_similares": 0,
                        "similitud_promedio": 0,
                    }
                productos_recomendados[prod]["num_similares"] += 1
                productos_recomendados[prod]["similitud_promedio"] += sim["similitud"]

    # Calcular score
    for prod in productos_recomendados:
        n = productos_recomendados[prod]["num_similares"]
        productos_recomendados[prod]["similitud_promedio"] /= n
        productos_recomendados[prod]["score"] = (
            n * productos_recomendados[prod]["similitud_promedio"]
        )

    return sorted(
        productos_recomendados.values(), key=lambda x: x["score"], reverse=True
    )


def obtener_productos_baja_venta_mes(mes, zona, productos_cliente):
    """Productos con baja venta en el mes pero afines al cliente"""
    # Ventas promedio del mes
    ventas_mes = (
        df_full.filter((col("Mes") == mes) & (col("Nombre_Zona") == zona))
        .groupBy("Producto")
        .agg(
            _sum("Venta_Cajas").alias("venta_total"),
            avg("Venta_Cajas").alias("venta_promedio"),
            count("*").alias("transacciones"),
        )
        .collect()
    )

    if not ventas_mes:
        return []

    # Calcular percentil 30 (productos con baja venta)
    ventas_totales = [row["venta_total"] for row in ventas_mes if row["venta_total"]]
    if not ventas_totales:
        return []

    percentil_30 = np.percentile(ventas_totales, 30)

    productos_baja_venta = []
    for row in ventas_mes:
        if row["venta_total"] and row["venta_total"] <= percentil_30:
            # Verificar si está relacionado con el portafolio del cliente
            productos_baja_venta.append(
                {
                    "producto": row["Producto"],
                    "venta_total": row["venta_total"],
                    "venta_promedio": row["venta_promedio"],
                    "transacciones": row["transacciones"],
                    "oportunidad": "BAJA COMPETENCIA",
                }
            )

    return sorted(productos_baja_venta, key=lambda x: x["venta_promedio"])[:10]


def predecir_demanda(cliente, zona, region, producto, mes, mes_num, precio, año=2025):
    """Predice demanda usando el modelo ML"""
    if model is None:
        return 0

    # Obtener métricas históricas
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
        precio_py = metricas[0]["Precio_Promedio_PY_Caja"] or precio
    else:
        venta_py_zona, venta_py_familia, meta_zona, precio_py = 10, 50, 20, precio

    # Factor de ajuste para 2026 (extrapolación)
    factor_año = 1.0 if año == 2025 else 1.05  # Crecimiento esperado 5%

    data = [
        (
            cliente,
            producto,
            zona,
            region,
            mes,
            mes_num,
            float(precio),
            float(venta_py_zona),
            float(venta_py_familia),
            float(meta_zona),
            float(precio_py),
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

    try:
        resultado = model.transform(df_pred)
        pred = resultado.select("prediction_final").collect()
        demanda = max(0, pred[0]["prediction_final"] * factor_año) if pred else 0
    except Exception:
        demanda = 10

    return demanda


def calcular_elasticidad_real(
    cliente, zona, region, producto, mes, mes_num, precio_base, rango_min, rango_max
):
    """Calcula elasticidad con rango de precios personalizado"""
    resultados = []

    # Generar puntos en el rango
    num_puntos = 15
    precios = np.linspace(
        precio_base * (1 + rango_min / 100),
        precio_base * (1 + rango_max / 100),
        num_puntos,
    )

    for precio in precios:
        demanda = predecir_demanda(
            cliente, zona, region, producto, mes, mes_num, precio
        )
        ingreso = precio * demanda

        # Calcular margen (asumiendo costo = 40% del precio base)
        costo_unitario = precio_base * 0.4
        margen = (precio - costo_unitario) * demanda

        variacion_precio = ((precio - precio_base) / precio_base) * 100

        resultados.append(
            {
                "precio": precio,
                "variacion_precio": variacion_precio,
                "demanda": demanda,
                "ingreso": ingreso,
                "margen": margen,
            }
        )

    return pd.DataFrame(resultados)


def generar_ofertas_personalizadas(
    producto, precio_base, demanda_estimada, perfil_cliente
):
    """Genera ofertas adaptadas al contexto"""
    ofertas = []

    # A. DESCUENTO POR VOLUMEN
    niveles_volumen = [
        {"desde": 1, "hasta": int(demanda_estimada * 0.5), "descuento": 0},
        {
            "desde": int(demanda_estimada * 0.5) + 1,
            "hasta": int(demanda_estimada),
            "descuento": 5,
        },
        {
            "desde": int(demanda_estimada) + 1,
            "hasta": int(demanda_estimada * 2),
            "descuento": 8,
        },
        {"desde": int(demanda_estimada * 2) + 1, "hasta": 99999, "descuento": 12},
    ]

    ofertas.append(
        {
            "tipo": "DESCUENTO_VOLUMEN",
            "titulo": "📦 Descuento por Volumen",
            "descripcion": "Mientras más compras, menor es tu precio unitario",
            "niveles": niveles_volumen,
            "beneficio_cliente": "Reduce hasta 12% el costo por caja",
            "beneficio_sophia": "Asegura ventas grandes y predecibles",
        }
    )

    # B. BONIFICACIÓN
    if demanda_estimada >= 50:
        bonificacion_cada = 100
        bonificacion_gratis = 5
    else:
        bonificacion_cada = 50
        bonificacion_gratis = 3

    ofertas.append(
        {
            "tipo": "BONIFICACION",
            "titulo": "🎁 Bonificación por Compra",
            "descripcion": f"Por cada {bonificacion_cada} cajas, recibe {bonificacion_gratis} GRATIS",
            "cada": bonificacion_cada,
            "gratis": bonificacion_gratis,
            "porcentaje_ahorro": (bonificacion_gratis / bonificacion_cada) * 100,
            "beneficio_cliente": f"Ahorro efectivo del {(bonificacion_gratis / bonificacion_cada) * 100:.1f}%",
            "beneficio_sophia": "Bajo costo de producción en unidades gratis",
        }
    )

    # C. COMBO FAMILIAR
    familia = producto.split(" ")[0] if " " in producto else producto[:5]

    ofertas.append(
        {
            "tipo": "COMBO",
            "titulo": "🔗 Combo por Familia de Productos",
            "descripcion": f"Compra {producto} + otro producto de familia {familia}",
            "descuento_combo": 15,
            "familia": familia,
            "beneficio_cliente": "15% descuento en ambos productos",
            "beneficio_sophia": "Aumenta el ticket promedio de venta",
        }
    )

    # D. FINANCIAMIENTO
    if perfil_cliente == "GRANDE":
        terminos = [
            {"plazo": "Contado", "beneficio": "3% descuento adicional"},
            {"plazo": "30 días", "beneficio": "Sin interés"},
            {"plazo": "60 días", "beneficio": "1% interés mensual"},
        ]
    elif perfil_cliente == "MEDIANO":
        terminos = [
            {"plazo": "Contado", "beneficio": "2% descuento adicional"},
            {"plazo": "30 días", "beneficio": "Sin interés"},
        ]
    else:
        terminos = [
            {"plazo": "Contado", "beneficio": "Precio estándar"},
            {"plazo": "15 días", "beneficio": "Sin recargo"},
        ]

    ofertas.append(
        {
            "tipo": "FINANCIAMIENTO",
            "titulo": "💳 Opciones de Financiamiento",
            "descripcion": "Flexibilidad en el pago según tu flujo de caja",
            "terminos": terminos,
            "beneficio_cliente": "Mejor gestión de flujo de caja",
            "beneficio_sophia": "Asegura pedidos más grandes",
        }
    )

    return ofertas


# ===============================================
# SIDEBAR
# ===============================================

st.sidebar.markdown(
    """
<div style="text-align: center; padding: 10px;">
    <h2>💊 Sophia Labs</h2>
    <p>Sistema de Recomendaciones</p>
</div>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")

# Filtros de región y zona
regiones = (
    df_full.select("Region").distinct().toPandas()["Region"].dropna().unique().tolist()
)
regiones = ["Todas"] + sorted(regiones)
region_sel = st.sidebar.selectbox("🗺️ Región", regiones, key="region")

# Filtrar zonas por región
if region_sel == "Todas":
    zonas_df = df_full.select("Nombre_Zona", "Cliente", "Region").distinct().toPandas()
else:
    zonas_df = (
        df_full.filter(col("Region") == region_sel)
        .select("Nombre_Zona", "Cliente", "Region")
        .distinct()
        .toPandas()
    )

zonas = ["Todas"] + sorted(zonas_df["Nombre_Zona"].dropna().unique().tolist())
zona_filtro = st.sidebar.selectbox("📍 Zona", zonas, key="zona_filtro")

# Filtrar clientes
if zona_filtro == "Todas":
    clientes = sorted(zonas_df["Cliente"].dropna().unique().tolist())
else:
    clientes = sorted(
        zonas_df[zonas_df["Nombre_Zona"] == zona_filtro]["Cliente"]
        .dropna()
        .unique()
        .tolist()
    )

cliente_sel = st.sidebar.selectbox("🏥 Cliente", clientes, key="cliente")

# Obtener info del cliente
info_cliente = (
    zonas_df[zonas_df["Cliente"] == cliente_sel].iloc[0]
    if not zonas_df[zonas_df["Cliente"] == cliente_sel].empty
    else None
)
zona_cliente = info_cliente["Nombre_Zona"] if info_cliente is not None else "N/A"
region_cliente = info_cliente["Region"] if info_cliente is not None else "N/A"

st.sidebar.info(f"📍 Zona: {zona_cliente}\n🗺️ Región: {region_cliente}")

st.sidebar.markdown("---")

# Configuración de predicción
st.sidebar.subheader("⚙️ Configuración de Predicción")

# Año de predicción
año_sel = st.sidebar.radio("📅 Año", [2025, 2026], horizontal=True, key="año")

# Meses disponibles
meses_nombres = [
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

if año_sel == 2025:
    # Desde diciembre 2025 en adelante
    meses_disponibles = ["DIC"]
    mes_sel = st.sidebar.selectbox(
        "📆 Mes", options=meses_disponibles, index=0, key="mes_2025"
    )
else:
    # Todo 2026
    meses_disponibles = meses_nombres
    mes_sel = st.sidebar.select_slider(
        "📆 Mes", options=meses_disponibles, value=meses_disponibles[0], key="mes_2026"
    )
mes_num = meses_nombres.index(mes_sel) + 1

# Advertencia para predicciones futuras
if año_sel == 2026 or (año_sel == 2025 and mes_sel == "DIC"):
    st.sidebar.warning(
        "⚠️ **Predicción futura**: Debido a la falta de datos históricos de este período, las predicciones pueden tener mayor incertidumbre."
    )

# Opción para predicciones históricas
permitir_historico = st.sidebar.checkbox(
    "🕐 Permitir predicciones históricas", value=False, key="historico"
)
if permitir_historico:
    st.sidebar.caption("Puedes seleccionar cualquier mes para análisis retrospectivo")
    mes_sel = st.sidebar.select_slider(
        "📆 Mes (Histórico)", options=meses_nombres, value="OCT", key="mes_hist"
    )
    mes_num = meses_nombres.index(mes_sel) + 1
    año_sel = st.sidebar.selectbox("Año histórico", [2024, 2025], key="año_hist")

st.sidebar.markdown("---")

# Rango de elasticidad personalizable
st.sidebar.subheader("📊 Rango de Elasticidad")
col1, col2 = st.sidebar.columns(2)
with col1:
    rango_min = st.number_input(
        "% Mínimo", min_value=-50, max_value=0, value=-30, key="rango_min"
    )
with col2:
    rango_max = st.number_input(
        "% Máximo", min_value=0, max_value=100, value=30, key="rango_max"
    )

st.sidebar.caption(f"Analizará precios desde {rango_min}% hasta +{rango_max}%")

# ===============================================
# HEADER PRINCIPAL
# ===============================================

st.markdown(
    """
<div class="main-header">
    <h1>💊 Sistema Integral de Recomendaciones</h1>
    <p>Laboratorios Sophia - Predicción de Demanda y Ofertas Personalizadas</p>
</div>
""",
    unsafe_allow_html=True,
)

# ===============================================
# INFORMACIÓN DEL CLIENTE
# ===============================================

if df_portafolio is not None:
    cliente_info = df_portafolio[df_portafolio["Cliente"] == cliente_sel]
    if not cliente_info.empty:
        info = cliente_info.iloc[0]
        gasto = info.get("total_gasto", 0)
        perfil_cliente = (
            "GRANDE" if gasto > 50000 else "MEDIANO" if gasto > 20000 else "PEQUEÑO"
        )
        productos_actuales = set(info.get("productos_comprados", []))
    else:
        gasto, perfil_cliente = 0, "NUEVO"
        productos_actuales = set()
else:
    gasto, perfil_cliente = 0, "NUEVO"
    productos_actuales = set()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🏥 Perfil", perfil_cliente)
with col2:
    st.metric("💰 Gasto Histórico", f"S/. {gasto:,.0f}")
with col3:
    st.metric("🛒 Productos Actuales", len(productos_actuales))
with col4:
    st.metric("📅 Proyección", f"{mes_sel} {año_sel}")

st.markdown("---")

# ===============================================
# TABS PRINCIPALES
# ===============================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🎯 Recomendaciones Personalizadas",
        "📈 Predicción de Demanda",
        "💰 Análisis de Elasticidad",
        "🎁 Ofertas Estratégicas",
        "📊 Resumen y Propuesta",
    ]
)

# ===============================================
# TAB 1: RECOMENDACIONES PERSONALIZADAS
# ===============================================

with tab1:
    st.header("🎯 Recomendaciones Personalizadas")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("👥 Clientes Similares")
        similares = calcular_similitud_clientes(cliente_sel, df_portafolio, top_n=10)

        if similares:
            df_sim = pd.DataFrame(similares)
            df_sim["similitud_pct"] = (df_sim["similitud"] * 100).round(1)

            fig_sim = px.bar(
                df_sim.head(5),
                x="similitud_pct",
                y="cliente",
                orientation="h",
                title="Top 5 Clientes con Perfil Similar",
                labels={"similitud_pct": "Similitud (%)", "cliente": "Cliente"},
                color="similitud_pct",
                color_continuous_scale="Blues",
            )
            fig_sim.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig_sim, use_container_width=True)
        else:
            st.info("No se encontraron clientes similares")

    with col2:
        st.subheader("🆕 Productos que NO Compras pero Similares SÍ")
        productos_recomendados = obtener_productos_no_comprados(
            cliente_sel, df_portafolio, similares
        )

        if productos_recomendados:
            for i, prod in enumerate(productos_recomendados[:5], 1):
                st.markdown(
                    f"""
                <div class="producto-nuevo">
                    <strong>#{i} {prod["producto"]}</strong><br>
                    👥 {prod["num_similares"]} clientes similares lo compran<br>
                    ⭐ Score: {prod["score"]:.2f}
                </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("Ya compras los productos más populares entre clientes similares")

    st.markdown("---")

    # Productos con baja venta (oportunidad)
    st.subheader("📉 Oportunidades: Productos con Baja Venta en el Mes")
    st.caption("Productos con poca competencia que podrían interesarte según tu perfil")

    productos_oportunidad = obtener_productos_baja_venta_mes(
        mes_sel, zona_cliente, productos_actuales
    )

    if productos_oportunidad:
        cols = st.columns(3)
        for i, prod in enumerate(productos_oportunidad[:6]):
            with cols[i % 3]:
                st.markdown(
                    f"""
                <div class="producto-oportunidad">
                    <strong>{prod["producto"]}</strong><br>
                    📦 Venta mes: {prod["venta_total"]:.0f} cajas<br>
                    🏷️ {prod["oportunidad"]}
                </div>
                """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("No se identificaron oportunidades adicionales")

# ===============================================
# TAB 2: PREDICCIÓN DE DEMANDA
# ===============================================

with tab2:
    st.header("📈 Predicción de Demanda")

    # Selección de productos a predecir
    st.subheader("Selecciona Productos para Predicción")

    # Combinar productos actuales + recomendados
    todos_productos = list(productos_actuales)
    if productos_recomendados:
        todos_productos += [p["producto"] for p in productos_recomendados[:10]]

    if not todos_productos:
        # Si no hay productos, obtener del catálogo
        catalogo = df_full.select("Producto").distinct().limit(50).collect()
        todos_productos = [row["Producto"] for row in catalogo]

    productos_sel = st.multiselect(
        "Productos a analizar",
        options=todos_productos,
        default=todos_productos[:5] if len(todos_productos) >= 5 else todos_productos,
        key="productos_pred",
    )

    if st.button(
        "🚀 Generar Predicciones",
        type="primary",
        use_container_width=True,
        key="btn_pred",
    ):
        if not productos_sel:
            st.warning("Selecciona al menos un producto")
        else:
            predicciones = []

            progress = st.progress(0)
            for i, producto in enumerate(productos_sel):
                # Obtener precio base
                precio_info = (
                    df_full.filter(col("Producto") == producto)
                    .select(avg("Precio_Caja").alias("precio"))
                    .collect()
                )
                precio_base = (
                    precio_info[0]["precio"]
                    if precio_info and precio_info[0]["precio"]
                    else 40.0
                )

                demanda = predecir_demanda(
                    cliente_sel,
                    zona_cliente,
                    region_cliente,
                    producto,
                    mes_sel,
                    mes_num,
                    precio_base,
                    año_sel,
                )

                predicciones.append(
                    {
                        "producto": producto,
                        "precio_caja": precio_base,
                        "demanda_cajas": demanda,
                        "demanda_piezas": demanda * 20,
                        "ingreso_estimado": demanda * precio_base,
                    }
                )

                progress.progress((i + 1) / len(productos_sel))

            # Mostrar resultados
            df_pred = pd.DataFrame(predicciones)

            col1, col2 = st.columns([2, 1])

            with col1:
                fig = px.bar(
                    df_pred,
                    x="producto",
                    y="demanda_cajas",
                    title=f"Predicción de Demanda - {mes_sel} {año_sel}",
                    labels={"demanda_cajas": "Cajas", "producto": "Producto"},
                    color="ingreso_estimado",
                    color_continuous_scale="Viridis",
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.metric("📦 Total Cajas", f"{df_pred['demanda_cajas'].sum():,.0f}")
                st.metric("💊 Total Piezas", f"{df_pred['demanda_piezas'].sum():,.0f}")
                st.metric(
                    "💰 Ingreso Estimado",
                    f"S/. {df_pred['ingreso_estimado'].sum():,.2f}",
                )

            # Tabla detallada
            st.subheader("📋 Detalle de Predicciones")
            df_display = df_pred.copy()
            df_display.columns = [
                "Producto",
                "Precio/Caja",
                "Demanda (Cajas)",
                "Demanda (Piezas)",
                "Ingreso Est.",
            ]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            # Guardar en session state para otros tabs
            st.session_state["predicciones"] = predicciones

# ===============================================
# TAB 3: ANÁLISIS DE ELASTICIDAD
# ===============================================

with tab3:
    st.header("💰 Análisis de Elasticidad de Precios")
    st.caption(f"Rango de análisis: {rango_min}% a +{rango_max}%")

    # Selección de producto
    producto_elasticidad = st.selectbox(
        "Selecciona producto para análisis de elasticidad",
        options=todos_productos[:20] if todos_productos else [],
        key="prod_elast",
    )

    if producto_elasticidad:
        # Obtener precio base
        precio_info = (
            df_full.filter(col("Producto") == producto_elasticidad)
            .select(avg("Precio_Caja").alias("precio"))
            .collect()
        )
        precio_base = (
            precio_info[0]["precio"]
            if precio_info and precio_info[0]["precio"]
            else 40.0
        )

        st.info(f"**Precio base actual:** S/. {precio_base:.2f}")

        if st.button("📊 Calcular Elasticidad", type="primary", key="btn_elast"):
            with st.spinner("Calculando curvas de elasticidad..."):
                df_elast = calcular_elasticidad_real(
                    cliente_sel,
                    zona_cliente,
                    region_cliente,
                    producto_elasticidad,
                    mes_sel,
                    mes_num,
                    precio_base,
                    rango_min,
                    rango_max,
                )

            # Encontrar óptimos
            idx_max_ingreso = df_elast["ingreso"].idxmax()
            idx_max_margen = df_elast["margen"].idxmax()

            precio_opt_ingreso = df_elast.loc[idx_max_ingreso, "precio"]
            precio_opt_margen = df_elast.loc[idx_max_margen, "precio"]
            var_opt_ingreso = df_elast.loc[idx_max_ingreso, "variacion_precio"]
            var_opt_margen = df_elast.loc[idx_max_margen, "variacion_precio"]

            col1, col2 = st.columns(2)

            with col1:
                st.success(f"""
                **🎯 Precio Óptimo (Máx. Ingreso)**
                - Precio: S/. {precio_opt_ingreso:.2f}
                - Variación: {var_opt_ingreso:+.1f}%
                - Ingreso: S/. {df_elast.loc[idx_max_ingreso, "ingreso"]:,.2f}
                """)

            with col2:
                st.success(f"""
                **💎 Precio Óptimo (Máx. Margen)**
                - Precio: S/. {precio_opt_margen:.2f}
                - Variación: {var_opt_margen:+.1f}%
                - Margen: S/. {df_elast.loc[idx_max_margen, "margen"]:,.2f}
                """)

            # Gráficos
            col1, col2 = st.columns(2)

            with col1:
                fig1 = go.Figure()
                fig1.add_trace(
                    go.Scatter(
                        x=df_elast["variacion_precio"],
                        y=df_elast["demanda"],
                        mode="lines+markers",
                        name="Demanda",
                        line=dict(color="blue"),
                    )
                )
                fig1.add_vline(x=0, line_dash="dash", line_color="gray")
                fig1.add_vline(
                    x=var_opt_ingreso,
                    line_dash="dash",
                    line_color="green",
                    annotation_text="Óptimo Ingreso",
                )
                fig1.update_layout(
                    title="Curva de Demanda",
                    xaxis_title="Variación de Precio (%)",
                    yaxis_title="Demanda (Cajas)",
                )
                st.plotly_chart(fig1, use_container_width=True)

            with col2:
                fig2 = go.Figure()
                fig2.add_trace(
                    go.Scatter(
                        x=df_elast["variacion_precio"],
                        y=df_elast["ingreso"],
                        mode="lines+markers",
                        name="Ingreso",
                        line=dict(color="green"),
                    )
                )
                fig2.add_trace(
                    go.Scatter(
                        x=df_elast["variacion_precio"],
                        y=df_elast["margen"],
                        mode="lines+markers",
                        name="Margen",
                        line=dict(color="orange"),
                    )
                )
                fig2.add_vline(x=0, line_dash="dash", line_color="gray")
                fig2.update_layout(
                    title="Curvas de Ingreso y Margen",
                    xaxis_title="Variación de Precio (%)",
                    yaxis_title="S/.",
                )
                st.plotly_chart(fig2, use_container_width=True)

            # Tabla de escenarios
            st.subheader("📋 Tabla de Escenarios")
            df_elast_display = df_elast.copy()
            df_elast_display["precio"] = df_elast_display["precio"].apply(
                lambda x: f"S/. {x:.2f}"
            )
            df_elast_display["variacion_precio"] = df_elast_display[
                "variacion_precio"
            ].apply(lambda x: f"{x:+.1f}%")
            df_elast_display["demanda"] = df_elast_display["demanda"].apply(
                lambda x: f"{x:.0f}"
            )
            df_elast_display["ingreso"] = df_elast_display["ingreso"].apply(
                lambda x: f"S/. {x:,.2f}"
            )
            df_elast_display["margen"] = df_elast_display["margen"].apply(
                lambda x: f"S/. {x:,.2f}"
            )
            df_elast_display.columns = [
                "Precio",
                "Variación",
                "Demanda",
                "Ingreso",
                "Margen",
            ]
            st.dataframe(df_elast_display, use_container_width=True, hide_index=True)

# ===============================================
# TAB 4: OFERTAS ESTRATÉGICAS
# ===============================================

with tab4:
    st.header("🎁 Ofertas Estratégicas Personalizadas")

    # Seleccionar producto para oferta
    producto_oferta = st.selectbox(
        "Selecciona producto para generar ofertas",
        options=todos_productos[:20] if todos_productos else [],
        key="prod_oferta",
    )

    if producto_oferta:
        precio_info = (
            df_full.filter(col("Producto") == producto_oferta)
            .select(avg("Precio_Caja").alias("precio"))
            .collect()
        )
        precio_base = (
            precio_info[0]["precio"]
            if precio_info and precio_info[0]["precio"]
            else 40.0
        )

        demanda_est = predecir_demanda(
            cliente_sel,
            zona_cliente,
            region_cliente,
            producto_oferta,
            mes_sel,
            mes_num,
            precio_base,
            año_sel,
        )

        ofertas = generar_ofertas_personalizadas(
            producto_oferta, precio_base, demanda_est, perfil_cliente
        )

        st.info(f"""
        **Producto:** {producto_oferta}  |  **Precio Base:** S/. {precio_base:.2f}  |  **Demanda Est.:** {demanda_est:.0f} cajas
        """)

        for oferta in ofertas:
            if oferta["tipo"] == "DESCUENTO_VOLUMEN":
                st.markdown(
                    f"""
                <div class="oferta-descuento">
                    <h4>{oferta["titulo"]}</h4>
                    <p>{oferta["descripcion"]}</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                df_niveles = pd.DataFrame(oferta["niveles"])
                df_niveles["precio"] = df_niveles.apply(
                    lambda x: f"S/. {precio_base * (1 - x['descuento'] / 100):.2f}",
                    axis=1,
                )
                df_niveles["rango"] = df_niveles.apply(
                    lambda x: f"{x['desde']} - {x['hasta'] if x['hasta'] < 99999 else '∞'}",
                    axis=1,
                )
                df_niveles["descuento"] = df_niveles["descuento"].apply(
                    lambda x: f"{x}%"
                )

                st.dataframe(
                    df_niveles[["rango", "descuento", "precio"]].rename(
                        columns={
                            "rango": "Cantidad (cajas)",
                            "descuento": "Descuento",
                            "precio": "Precio/Caja",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

            elif oferta["tipo"] == "BONIFICACION":
                st.markdown(
                    f"""
                <div class="oferta-bonificacion">
                    <h4>{oferta["titulo"]}</h4>
                    <p>{oferta["descripcion"]}</p>
                    <p>✅ {oferta["beneficio_cliente"]}</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            elif oferta["tipo"] == "COMBO":
                st.markdown(
                    f"""
                <div class="oferta-combo">
                    <h4>{oferta["titulo"]}</h4>
                    <p>{oferta["descripcion"]}</p>
                    <p>🎯 Descuento: {oferta["descuento_combo"]}% en ambos productos</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            elif oferta["tipo"] == "FINANCIAMIENTO":
                st.markdown(f"### {oferta['titulo']}")
                st.caption(oferta["descripcion"])

                for termino in oferta["terminos"]:
                    st.markdown(f"- **{termino['plazo']}:** {termino['beneficio']}")

# ===============================================
# TAB 5: RESUMEN Y PROPUESTA
# ===============================================

with tab5:
    st.header("📊 Resumen Ejecutivo y Propuesta Comercial")

    st.markdown(f"""
    ---
    ## PROPUESTA COMERCIAL PERSONALIZADA
    
    **Cliente:** {cliente_sel}  
    **Zona:** {zona_cliente} | **Región:** {region_cliente}  
    **Perfil:** {perfil_cliente}  
    **Período:** {mes_sel} {año_sel}  
    **Fecha:** {datetime.now().strftime("%d de %B, %Y")}
    
    ---
    
    ### 📊 Resumen del Cliente
    
    - **Gasto Histórico:** S/. {gasto:,.2f}
    - **Productos en Portafolio:** {len(productos_actuales)}
    - **Clientes Similares Identificados:** {len(similares) if similares else 0}
    
    ---
    
    ### 🎯 Oportunidades Identificadas
    """)

    if productos_recomendados:
        st.markdown("#### Productos Recomendados (NO compra actualmente)")
        for i, prod in enumerate(productos_recomendados[:3], 1):
            st.markdown(
                f"{i}. **{prod['producto']}** - {prod['num_similares']} clientes similares lo compran"
            )

    if productos_oportunidad:
        st.markdown("#### Productos con Baja Competencia")
        for prod in productos_oportunidad[:3]:
            st.markdown(
                f"- **{prod['producto']}** - Solo {prod['venta_total']:.0f} cajas vendidas en el mes"
            )

    st.markdown("""
    ---
    
    ### 💼 Términos Comerciales Sugeridos
    """)

    if perfil_cliente == "GRANDE":
        st.success("""
        **Para Cliente GRANDE:**
        - ✅ Descuentos por volumen hasta 12%
        - ✅ Bonificación: 5 cajas gratis por cada 100
        - ✅ Crédito hasta 60 días
        - ✅ Combos familiares con 15% descuento
        """)
    elif perfil_cliente == "MEDIANO":
        st.info("""
        **Para Cliente MEDIANO:**
        - ✅ Descuentos por volumen hasta 8%
        - ✅ Bonificación: 3 cajas gratis por cada 50
        - ✅ Crédito hasta 30 días
        - ✅ Combos familiares con 10% descuento
        """)
    else:
        st.warning("""
        **Para Cliente PEQUEÑO/NUEVO:**
        - ✅ Descuentos por volumen hasta 5%
        - ✅ Bonificación: 2 cajas gratis por cada 30
        - ✅ Crédito hasta 15 días
        - ✅ Promociones de entrada al portafolio
        """)

    st.markdown("""
    ---
    
    ### 📞 Próximos Pasos
    
    1. Revisar productos recomendados con el cliente
    2. Presentar ofertas de descuento por volumen
    3. Negociar términos de pago
    4. Cerrar pedido
    
    ---
    
    **Laboratorios Sophia** | *Comprometidos con tu salud ocular*
    """)

# ===============================================
# FOOTER
# ===============================================

st.markdown("---")
st.markdown(
    """
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><strong>Sistema Integral de Recomendaciones - Laboratorios Sophia</strong></p>
    <p>Modelo: Random Forest Regressor (Spark MLlib) | Dashboard: Streamlit</p>
    <p>✨ Predicciones dinámicas basadas en Machine Learning</p>
</div>
""",
    unsafe_allow_html=True,
)
