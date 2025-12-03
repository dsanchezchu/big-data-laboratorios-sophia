import os
import time
import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import lit, desc, col

# Configuración
MODEL_PATH = os.environ.get(
    "MODEL_PATH", "hdfs://namenode:9000/user/nifi/models/best_rf_calibrated"
)
DATA_PATH = os.environ.get(
    "DATA_PATH", "hdfs://namenode:9000/user/nifi/processed/dataset_ml_sophia_final"
)
SPARK_MASTER = os.environ.get("SPARK_MASTER", "spark://spark-master:7077")

st.set_page_config(
    page_title="Sistema de Ofertas - Sophia Labs",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="💊",
)

# Custom CSS
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
    .precio-destacado {
        font-size: 28px;
        font-weight: bold;
        color: #0066cc;
    }
    .descuento-badge {
        background-color: #ff4b4b;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .combo-badge {
        background-color: #00cc66;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ===============================================
# FUNCIONES DE INICIALIZACIÓN
# ===============================================


@st.cache_resource(ttl=3600)
def init_spark():
    for i in range(20):
        try:
            spark = (
                SparkSession.builder.appName("streamlit-sophia-ofertas")
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

    data_dir = "/home/jupyter/notebooks/data"

    # Cargar ofertas pregeneradas
    try:
        with open(
            os.path.join(data_dir, "ofertas_generadas.json"), "r", encoding="utf-8"
        ) as f:
            ofertas = json.load(f)
    except:
        ofertas = None

    # Cargar portafolio
    try:
        df_portafolio = pd.read_parquet(
            os.path.join(data_dir, "portafolio_clientes.parquet")
        )
    except:
        df_portafolio = None

    return df, model, ofertas, df_portafolio


spark = init_spark()
df_full, model, ofertas_pregeneradas, df_portafolio = load_resources()

if df_full is None:
    st.error("❌ No se pudo cargar el dataset desde HDFS.")
    st.stop()

# ===============================================
# SIDEBAR
# ===============================================

st.sidebar.title("⚙️ Configuración")
st.sidebar.markdown("---")

# Selección de cliente
if ofertas_pregeneradas:
    clientes_con_ofertas = [o["cliente"] for o in ofertas_pregeneradas]
    cliente_sel = st.sidebar.selectbox("🏥 Cliente", clientes_con_ofertas)
else:
    zonas_df = df_full.select("Cliente").distinct().toPandas()
    clientes = sorted(zonas_df["Cliente"].unique().tolist())
    cliente_sel = st.sidebar.selectbox("🏥 Cliente", clientes)

st.sidebar.markdown("---")

# Mes de proyección
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
mes_sel = st.sidebar.select_slider("📅 Mes de Proyección", options=meses, value="NOV")

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Tip:** Las ofertas combinan precio óptimo + descuentos por volumen + bonificaciones"
)

# ===============================================
# HEADER
# ===============================================

st.title("💊 Sistema de Ofertas Inteligentes")
st.markdown("### Laboratorios Sophia - Recomendaciones Comerciales Personalizadas")
st.markdown("---")

# ===============================================
# OBTENER OFERTA DEL CLIENTE
# ===============================================

oferta_cliente = None
if ofertas_pregeneradas:
    for oferta in ofertas_pregeneradas:
        if oferta["cliente"] == cliente_sel:
            oferta_cliente = oferta
            break

if not oferta_cliente:
    st.warning(
        "⚠️ No hay oferta pregenerada para este cliente. Ejecuta `generador_ofertas_v3.py` primero."
    )
    st.stop()

# ===============================================
# INFORMACIÓN DEL CLIENTE
# ===============================================

perfil = oferta_cliente["perfil_cliente"]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🏥 Categoría", perfil["categoria"])
with col2:
    st.metric("💰 Gasto Histórico", f"S/. {perfil['gasto_historico_total']:,.0f}")
with col3:
    st.metric("📦 Volumen Total", f"{perfil['volumen_historico_cajas']:,} cajas")
with col4:
    st.metric("🛒 Productos Actuales", perfil["productos_en_portafolio"])

st.markdown("---")

# ===============================================
# TABS PRINCIPALES
# ===============================================

tab1, tab2, tab3 = st.tabs(
    ["🎯 Ofertas Recomendadas", "📊 Análisis Comparativo", "📄 Propuesta Comercial"]
)

# ===============================================
# TAB 1: OFERTAS RECOMENDADAS
# ===============================================

with tab1:
    st.header("🎯 Ofertas Personalizadas para el Cliente")
    st.markdown(f"**Mes de proyección:** {mes_sel} 2025")

    # Filtro de productos
    num_productos = st.slider("Número de productos a mostrar", 3, 10, 5)

    productos_mostrar = oferta_cliente["productos_ofertas"][:num_productos]

    for oferta in productos_mostrar:
        with st.container():
            st.markdown(
                f"""
            <div class="oferta-card">
                <h3>#{oferta["posicion"]} - {oferta["producto"]}</h3>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Métricas principales
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(
                    f"<p class='precio-destacado'>S/. {oferta['precio_sugerido']:.2f}</p>",
                    unsafe_allow_html=True,
                )
                st.caption("Precio por caja")
            with col2:
                st.metric(
                    "📦 Demanda Est.", f"{oferta['demanda_estimada_cajas']} cajas"
                )
            with col3:
                st.metric(
                    "💊 Demanda Est.", f"{oferta['demanda_estimada_piezas']:,} piezas"
                )
            with col4:
                st.metric(
                    "👥 Similares compran", oferta["num_clientes_similares_compran"]
                )

            # Expandibles con detalles
            with st.expander("💰 Ver Descuentos por Volumen"):
                st.markdown("**Escala de Precios:**")
                for nivel in oferta["descuentos_por_volumen"]:
                    if nivel["descuento_porcentaje"] > 0:
                        badge = f"<span class='descuento-badge'>-{nivel['descuento_porcentaje']}%</span>"
                    else:
                        badge = ""

                    st.markdown(
                        f"""
                    - **Nivel {nivel["nivel"]}:** {nivel["desde_cajas"]} - {nivel["hasta_cajas"] if nivel["hasta_cajas"] < 99999 else "∞"} cajas 
                      → **S/. {nivel["precio_por_caja"]:.2f}/caja** {badge}
                    """,
                        unsafe_allow_html=True,
                    )

            with st.expander("🎁 Ver Bonificación"):
                bonif = oferta["bonificacion"]
                if bonif["activa"]:
                    st.success(f"✅ {bonif['mensaje']}")
                    st.info(f"💡 Ahorro efectivo: {bonif['porcentaje_ahorro']:.1f}%")
                else:
                    st.warning("No hay bonificación disponible para este producto")

            if oferta["combo_estrategico"]:
                with st.expander("🔗 Ver Combo Estratégico"):
                    combo = oferta["combo_estrategico"]
                    st.markdown(
                        f"""
                    <span class='combo-badge'>COMBO ESPECIAL</span><br><br>
                    <strong>{combo["mensaje"]}</strong><br>
                    Ahorro adicional: {combo["descuento_combo"]}%
                    """,
                        unsafe_allow_html=True,
                    )

            with st.expander("💳 Ver Términos de Pago"):
                terminos = oferta["terminos_pago"]
                st.markdown("**Opciones de pago:**")
                for key, value in terminos.items():
                    if key != "recomendacion":
                        emoji = "⭐" if key == terminos["recomendacion"] else "▪️"
                        st.markdown(
                            f"{emoji} **{key.replace('_', ' ').title()}:** {value}"
                        )

            st.markdown("---")

    # Resumen de la oferta
    st.subheader("📊 Resumen de la Oferta")

    total_cajas = sum(o["demanda_estimada_cajas"] for o in productos_mostrar)
    total_piezas = sum(o["demanda_estimada_piezas"] for o in productos_mostrar)
    valor_total = sum(
        o["precio_sugerido"] * o["demanda_estimada_cajas"] for o in productos_mostrar
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📦 Total Cajas", f"{total_cajas:,}")
    with col2:
        st.metric("💊 Total Piezas", f"{total_piezas:,}")
    with col3:
        st.metric("💰 Valor Estimado", f"S/. {valor_total:,.2f}")

# ===============================================
# TAB 2: ANÁLISIS COMPARATIVO
# ===============================================

with tab2:
    st.header("📊 Análisis Comparativo de Ofertas")

    # Gráfico de precios
    st.subheader("Comparación de Precios")

    df_precios = pd.DataFrame(
        [
            {
                "Producto": o["producto"][:30],
                "Precio Base": o["precio_base"],
                "Precio Sugerido": o["precio_sugerido"],
                "Con Descuento Max": o["descuentos_por_volumen"][-1]["precio_por_caja"],
            }
            for o in productos_mostrar
        ]
    )

    fig1 = go.Figure()
    fig1.add_trace(
        go.Bar(
            name="Precio Base",
            x=df_precios["Producto"],
            y=df_precios["Precio Base"],
            marker_color="lightgray",
        )
    )
    fig1.add_trace(
        go.Bar(
            name="Precio Sugerido",
            x=df_precios["Producto"],
            y=df_precios["Precio Sugerido"],
            marker_color="blue",
        )
    )
    fig1.add_trace(
        go.Bar(
            name="Precio con Desc. Máx",
            x=df_precios["Producto"],
            y=df_precios["Con Descuento Max"],
            marker_color="green",
        )
    )

    fig1.update_layout(
        barmode="group",
        title="Comparación de Precios por Producto",
        xaxis_title="Producto",
        yaxis_title="Precio (S/./caja)",
        height=400,
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Gráfico de demanda
    st.subheader("Proyección de Demanda")

    df_demanda = pd.DataFrame(
        [
            {
                "Producto": o["producto"][:30],
                "Cajas": o["demanda_estimada_cajas"],
                "Piezas": o["demanda_estimada_piezas"],
            }
            for o in productos_mostrar
        ]
    )

    fig2 = px.bar(
        df_demanda,
        x="Producto",
        y="Cajas",
        title="Demanda Estimada por Producto (Cajas)",
        color="Cajas",
        color_continuous_scale="Blues",
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Tabla comparativa
    st.subheader("Tabla Comparativa Detallada")

    df_comparativa = pd.DataFrame(
        [
            {
                "Producto": o["producto"],
                "Precio (S/.)": o["precio_sugerido"],
                "Demanda (Cajas)": o["demanda_estimada_cajas"],
                "Bonificación": f"{o['bonificacion']['porcentaje_ahorro']:.1f}%",
                "Desc. Max": f"{o['descuentos_por_volumen'][-1]['descuento_porcentaje']}%",
                "Score": o["score_prioridad"],
            }
            for o in productos_mostrar
        ]
    )

    st.dataframe(df_comparativa, use_container_width=True, hide_index=True)

# ===============================================
# TAB 3: PROPUESTA COMERCIAL
# ===============================================

with tab3:
    st.header("📄 Propuesta Comercial Formal")
    st.markdown("**Documento listo para enviar al cliente**")

    st.markdown(f"""
    ---
    
    ## PROPUESTA COMERCIAL
    
    **Para:** {oferta_cliente["cliente"]}  
    **Zona:** {oferta_cliente["zona"]} - {oferta_cliente["region"]}  
    **Fecha:** {time.strftime("%d de %B, %Y")}  
    **Válido hasta:** {mes_sel} 2025  
    
    ---
    
    ### Estimado Cliente:
    
    En **Laboratorios Sophia** nos complace presentarle nuestra propuesta comercial personalizada 
    para el mes de **{mes_sel} 2025**, basada en un análisis detallado de su perfil de compra y 
    las tendencias del mercado farmacéutico en su zona.
    
    ### Perfil del Cliente
    
    - **Categoría:** {perfil["categoria"]}
    - **Histórico de Compras:** S/. {perfil["gasto_historico_total"]:,.2f}
    - **Volumen Anual:** {perfil["volumen_historico_cajas"]:,} cajas
    
    ---
    
    ### Productos Recomendados
    """)

    for i, oferta in enumerate(productos_mostrar, 1):
        st.markdown(f"""
        #### {i}. {oferta["producto"]}
        
        **Precio por Caja:** S/. {oferta["precio_sugerido"]:.2f}  
        **Demanda Estimada:** {oferta["demanda_estimada_cajas"]} cajas ({oferta["demanda_estimada_piezas"]:,} piezas)
        
        **Beneficios Especiales:**
        
        ✅ **Descuentos por Volumen:**
        """)

        for nivel in oferta["descuentos_por_volumen"]:
            if nivel["descuento_porcentaje"] > 0:
                st.markdown(
                    f"   - Compra {nivel['desde_cajas']}+ cajas: **{nivel['descuento_porcentaje']}% de descuento** (S/. {nivel['precio_por_caja']:.2f}/caja)"
                )

        st.markdown(f"""
        ✅ **Bonificación:** {oferta["bonificacion"]["mensaje"]}
        """)

        if oferta["combo_estrategico"]:
            st.markdown(f"""
        ✅ **Combo Especial:** {oferta["combo_estrategico"]["mensaje"]}
            """)

        st.markdown("---")

    # Términos generales
    st.markdown(f"""
    ### Términos de Pago
    
    Ofrecemos las siguientes opciones:
    """)

    terminos_ejemplo = productos_mostrar[0]["terminos_pago"]
    for key, value in terminos_ejemplo.items():
        if key != "recomendacion":
            st.markdown(f"- **{key.replace('_', ' ').title()}:** {value}")

    st.markdown(f"""
    ---
    
    ### Valor Total de la Propuesta
    
    - **Total Cajas:** {total_cajas:,}
    - **Total Piezas:** {total_piezas:,}
    - **Valor Estimado:** S/. {valor_total:,.2f}
    
    ---
    
    ### Contacto
    
    Para aceptar esta oferta o solicitar ajustes, por favor contacte a su ejecutivo de ventas.
    
    **Laboratorios Sophia**  
    *Comprometidos con su salud*
    
    ---
    """)

    # Botón de descarga (simulado)
    if st.button("📥 Descargar Propuesta (PDF)", use_container_width=True):
        st.success("✅ Funcionalidad de descarga disponible próximamente")

# ===============================================
# FOOTER
# ===============================================

st.markdown("---")
st.markdown(
    """
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><strong>Laboratorios Sophia</strong> | Sistema de Ofertas Inteligentes</p>
    <p>Modelo: Random Forest + Análisis de Similitud | Tecnología: Apache Spark + Streamlit</p>
</div>
""",
    unsafe_allow_html=True,
)
