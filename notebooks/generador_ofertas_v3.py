#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SISTEMA DE GENERACIÓN DE OFERTAS INTELIGENTES V3
Solución al problema: El área de ventas no sabe QUÉ productos recomendar ni A QUÉ PRECIO

Funcionalidades:
1. Recomendación de productos NO comprados (basado en clientes similares)
2. Precio óptimo por producto
3. OFERTAS ESTRATÉGICAS:
   - Descuentos por volumen
   - Bonificaciones (2x1, 3x2, etc.)
   - Combos por familia de productos
   - Sugerencias de financiamiento
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    lit,
    count,
    sum as _sum,
    avg,
    desc,
    collect_list,
    explode,
    round as spark_round,
    max as spark_max,
)
import pandas as pd
import os

# ===============================================
# 1. INICIALIZAR SPARK
# ===============================================
spark = (
    SparkSession.builder.appName("Sistema_Ofertas_Inteligentes_V3")
    .master("spark://spark-master:7077")
    .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000")
    .config("spark.executor.memory", "2g")
    .config("spark.driver.memory", "2g")
    .getOrCreate()
)

print("✅ Spark Session iniciada")

# ===============================================
# 2. CARGAR DATOS
# ===============================================
path_data = "hdfs://namenode:9000/user/nifi/processed/dataset_ml_sophia_final"
df_full = spark.read.parquet(path_data)
df_full.cache()

print(f"✅ Dataset cargado: {df_full.count():,} registros")

# ===============================================
# 3. ANÁLISIS DE PORTAFOLIO Y SIMILITUD
# ===============================================
print("\n" + "=" * 80)
print("📊 PASO 1: ANÁLISIS DE PORTAFOLIO Y CLIENTES SIMILARES")
print("=" * 80)

# Portafolio por cliente
df_cliente_productos = df_full.groupBy("Cliente").agg(
    collect_list("Producto").alias("productos_comprados"),
    _sum("Venta_Cajas").alias("total_cajas_historicas"),
    _sum("Venta_Valor").alias("total_gasto"),
    count("*").alias("num_transacciones"),
    avg("Precio_Caja").alias("precio_promedio_pagado"),
)

print("✅ Portafolio calculado")


def calcular_clientes_similares(cliente_objetivo, top_n=5):
    """Encuentra clientes con perfil de compra similar"""
    productos_objetivo = (
        df_cliente_productos.filter(col("Cliente") == cliente_objetivo)
        .select("productos_comprados")
        .collect()
    )

    if not productos_objetivo:
        return []

    set_objetivo = set(productos_objetivo[0]["productos_comprados"])

    similitudes = []
    otros_clientes = df_cliente_productos.filter(
        col("Cliente") != cliente_objetivo
    ).collect()

    for row in otros_clientes:
        set_otro = set(row["productos_comprados"])
        interseccion = len(set_objetivo.intersection(set_otro))
        union = len(set_objetivo.union(set_otro))

        if union > 0:
            similitud = interseccion / union
            similitudes.append(
                {
                    "cliente": row["Cliente"],
                    "similitud": similitud,
                    "productos_comunes": interseccion,
                    "total_gasto": row["total_gasto"],
                }
            )

    return sorted(similitudes, key=lambda x: x["similitud"], reverse=True)[:top_n]


# ===============================================
# 4. MOTOR DE GENERACIÓN DE OFERTAS
# ===============================================
print("\n" + "=" * 80)
print("💰 PASO 2: GENERACIÓN DE OFERTAS ESTRATÉGICAS")
print("=" * 80)


def generar_oferta_completa(cliente_objetivo, mes_objetivo="OCT"):
    """
    Genera una oferta comercial completa para un cliente:
    1. Productos recomendados (NO comprados)
    2. Precio sugerido por producto
    3. Descuentos por volumen
    4. Bonificaciones
    5. Combos estratégicos
    6. Términos de pago
    """

    # ============================================================
    # A. IDENTIFICAR PRODUCTOS CANDIDATOS
    # ============================================================
    portafolio = (
        df_cliente_productos.filter(col("Cliente") == cliente_objetivo)
        .select("productos_comprados", "total_gasto", "total_cajas_historicas")
        .collect()
    )

    if not portafolio:
        print(f"❌ Cliente '{cliente_objetivo}' no encontrado")
        return None

    productos_actuales = set(portafolio[0]["productos_comprados"])
    gasto_historico = portafolio[0]["total_gasto"]
    volumen_historico = portafolio[0]["total_cajas_historicas"]

    # Información geográfica
    info_cliente = (
        df_full.filter(col("Cliente") == cliente_objetivo)
        .select("Nombre_Zona", "Region")
        .limit(1)
        .collect()
    )

    if not info_cliente:
        return None

    zona = info_cliente[0]["Nombre_Zona"]
    region = info_cliente[0]["Region"]

    # Clientes similares
    clientes_similares = calcular_clientes_similares(cliente_objetivo, top_n=10)
    nombres_similares = [c["cliente"] for c in clientes_similares]

    # Productos que similares compran pero el cliente NO
    from pyspark.sql.functions import explode

    productos_similares = (
        df_cliente_productos.filter(col("Cliente").isin(nombres_similares))
        .select(explode("productos_comprados").alias("Producto"))
        .distinct()
    )

    productos_candidatos = productos_similares.filter(
        ~col("Producto").isin(list(productos_actuales))
    )

    # Enriquecer con métricas
    df_candidatos = productos_candidatos.join(
        df_full.filter(col("Nombre_Zona") == zona)
        .groupBy("Producto")
        .agg(
            avg("Venta_Cajas").alias("demanda_promedio_zona"),
            avg("Precio_Caja").alias("precio_promedio_zona"),
            _sum("Venta_Valor").alias("ingreso_total_zona"),
            spark_max("Venta_Cajas").alias("venta_maxima_zona"),
        ),
        "Producto",
        "left",
    ).fillna(0)

    # Agregar familia del producto
    df_candidatos = df_candidatos.join(
        df_full.select("Producto", "Venta_PY_Familia_Cajas").dropDuplicates(
            ["Producto"]
        ),
        "Producto",
        "left",
    )

    # Score de prioridad
    df_similares_count = (
        df_cliente_productos.filter(col("Cliente").isin(nombres_similares))
        .select("Cliente", explode("productos_comprados").alias("Producto"))
        .groupBy("Producto")
        .agg(count("*").alias("num_similares"))
    )

    df_candidatos = df_candidatos.join(df_similares_count, "Producto", "left").fillna(0)

    df_candidatos = df_candidatos.withColumn(
        "score_prioridad",
        (col("demanda_promedio_zona") * 0.4)
        + (col("num_similares") * 10 * 0.4)
        + (col("ingreso_total_zona") / 1000 * 0.2),
    )

    # Top 10 productos
    top_productos = df_candidatos.orderBy(desc("score_prioridad")).limit(10).collect()

    if not top_productos:
        print("⚠️ No se encontraron productos candidatos")
        return None

    # ============================================================
    # B. GENERAR ESTRUCTURA DE OFERTA
    # ============================================================
    ofertas = []

    for idx, row in enumerate(top_productos, 1):
        producto = row["Producto"]
        precio_base = row["precio_promedio_zona"]
        demanda_estimada = row["demanda_promedio_zona"]

        # --------------------------------------------------------
        # 1. PRECIO SUGERIDO (con margen de negociación)
        # --------------------------------------------------------
        precio_sugerido = precio_base
        precio_minimo = precio_base * 0.85  # Margen mínimo: -15%
        precio_maximo = precio_base * 1.10  # Margen máximo: +10%

        # --------------------------------------------------------
        # 2. DESCUENTO POR VOLUMEN (Escala de 3 niveles)
        # --------------------------------------------------------
        # Basado en la demanda promedio de la zona
        nivel_1_cajas = int(demanda_estimada * 0.5)  # 50% de la demanda promedio
        nivel_2_cajas = int(demanda_estimada * 1.0)  # 100% de la demanda
        nivel_3_cajas = int(demanda_estimada * 2.0)  # 200% de la demanda

        desc_vol_nivel_1 = 0  # Sin descuento
        desc_vol_nivel_2 = 5  # 5% descuento
        desc_vol_nivel_3 = 10  # 10% descuento

        descuentos_volumen = [
            {
                "nivel": 1,
                "desde_cajas": 1,
                "hasta_cajas": nivel_1_cajas,
                "descuento_porcentaje": desc_vol_nivel_1,
                "precio_por_caja": precio_sugerido,
                "mensaje": f"Precio estándar: S/. {precio_sugerido:.2f}/caja",
            },
            {
                "nivel": 2,
                "desde_cajas": nivel_1_cajas + 1,
                "hasta_cajas": nivel_2_cajas,
                "descuento_porcentaje": desc_vol_nivel_2,
                "precio_por_caja": precio_sugerido * 0.95,
                "mensaje": f"Compra {nivel_1_cajas + 1}-{nivel_2_cajas} cajas: -{desc_vol_nivel_2}% = S/. {precio_sugerido * 0.95:.2f}/caja",
            },
            {
                "nivel": 3,
                "desde_cajas": nivel_2_cajas + 1,
                "hasta_cajas": 99999,
                "descuento_porcentaje": desc_vol_nivel_3,
                "precio_por_caja": precio_sugerido * 0.90,
                "mensaje": f"Compra +{nivel_2_cajas + 1} cajas: -{desc_vol_nivel_3}% = S/. {precio_sugerido * 0.90:.2f}/caja",
            },
        ]

        # --------------------------------------------------------
        # 3. BONIFICACIÓN (X + Y gratis)
        # --------------------------------------------------------
        # Ejemplo: Por cada 100 cajas, regala 5 (5%)
        bonificacion_cada = 100
        bonificacion_gratis = 5
        bonificacion_porcentaje = (bonificacion_gratis / bonificacion_cada) * 100

        bonificacion = {
            "activa": True,
            "cada_cajas": bonificacion_cada,
            "unidades_gratis": bonificacion_gratis,
            "porcentaje_ahorro": bonificacion_porcentaje,
            "mensaje": f"¡BONIFICACIÓN! Por cada {bonificacion_cada} cajas, recibe {bonificacion_gratis} GRATIS",
        }

        # --------------------------------------------------------
        # 4. COMBO ESTRATÉGICO (Solo si hay productos de familia)
        # --------------------------------------------------------
        # Buscar productos de la misma familia que el cliente YA compra
        familia_key = producto.split(" ")[0] if " " in producto else producto[:5]

        productos_familia_cliente = [p for p in productos_actuales if familia_key in p]

        combo = None
        if productos_familia_cliente:
            producto_combo = productos_familia_cliente[0]
            combo = {
                "activa": True,
                "producto_principal": producto,
                "producto_combo": producto_combo,
                "descuento_combo": 15,  # 15% descuento en el combo
                "mensaje": f"COMBO: Compra {producto} + {producto_combo} con 15% descuento en ambos",
            }

        # --------------------------------------------------------
        # 5. TÉRMINOS DE PAGO
        # --------------------------------------------------------
        # Basado en el gasto histórico del cliente
        if gasto_historico > 50000:  # Cliente grande
            terminos_pago = {
                "contado": "Pago inmediato: 2% descuento adicional",
                "credito_30": "Pago a 30 días: Sin interés",
                "credito_60": "Pago a 60 días: 1% interés mensual",
                "recomendacion": "credito_30",
            }
        elif gasto_historico > 20000:  # Cliente mediano
            terminos_pago = {
                "contado": "Pago inmediato: 3% descuento adicional",
                "credito_30": "Pago a 30 días: Sin interés",
                "recomendacion": "contado",
            }
        else:  # Cliente pequeño
            terminos_pago = {
                "contado": "Pago inmediato: Precio estándar",
                "credito_15": "Pago a 15 días: Precio estándar",
                "recomendacion": "contado",
            }

        # --------------------------------------------------------
        # ESTRUCTURA FINAL DE LA OFERTA
        # --------------------------------------------------------
        oferta = {
            "posicion": idx,
            "producto": producto,
            "precio_base": round(precio_base, 2),
            "precio_sugerido": round(precio_sugerido, 2),
            "precio_minimo_negociable": round(precio_minimo, 2),
            "precio_maximo_negociable": round(precio_maximo, 2),
            "demanda_estimada_cajas": int(demanda_estimada),
            "demanda_estimada_piezas": int(demanda_estimada * 20),
            "descuentos_por_volumen": descuentos_volumen,
            "bonificacion": bonificacion,
            "combo_estrategico": combo,
            "terminos_pago": terminos_pago,
            "num_clientes_similares_compran": int(row["num_similares"]),
            "score_prioridad": round(row["score_prioridad"], 2),
        }

        ofertas.append(oferta)

    # ============================================================
    # C. RESUMEN EJECUTIVO DE LA OFERTA
    # ============================================================
    resumen = {
        "cliente": cliente_objetivo,
        "zona": zona,
        "region": region,
        "mes_proyeccion": mes_objetivo,
        "perfil_cliente": {
            "gasto_historico_total": round(gasto_historico, 2),
            "volumen_historico_cajas": int(volumen_historico),
            "productos_en_portafolio": len(productos_actuales),
            "categoria": "GRANDE"
            if gasto_historico > 50000
            else "MEDIANO"
            if gasto_historico > 20000
            else "PEQUEÑO",
        },
        "num_clientes_similares_analizados": len(clientes_similares),
        "total_productos_recomendados": len(ofertas),
        "productos_ofertas": ofertas,
    }

    return resumen


# ===============================================
# 5. GENERAR OFERTAS PARA CLIENTES DE PRUEBA
# ===============================================
print("\n" + "=" * 80)
print("🎯 PASO 3: GENERANDO OFERTAS PARA CLIENTES DE PRUEBA")
print("=" * 80)

# Cliente de prueba
cliente_prueba = "ADMINISTRADORA CLINICA TRESA S.A"
oferta_completa = generar_oferta_completa(cliente_prueba, mes_objetivo="NOV")

if oferta_completa:
    print(f"\n✅ OFERTA GENERADA PARA: {oferta_completa['cliente']}")
    print(f"   Zona: {oferta_completa['zona']} ({oferta_completa['region']})")
    print(f"   Perfil: {oferta_completa['perfil_cliente']['categoria']}")
    print(
        f"   Gasto Histórico: S/. {oferta_completa['perfil_cliente']['gasto_historico_total']:,.2f}"
    )
    print(
        f"\n   📦 Total de productos recomendados: {oferta_completa['total_productos_recomendados']}"
    )

    print("\n   🏆 TOP 3 OFERTAS:")
    for oferta in oferta_completa["productos_ofertas"][:3]:
        print(f"\n   {oferta['posicion']}. {oferta['producto']}")
        print(f"      💰 Precio sugerido: S/. {oferta['precio_sugerido']:.2f}/caja")
        print(
            f"      📊 Demanda estimada: {oferta['demanda_estimada_cajas']} cajas ({oferta['demanda_estimada_piezas']} piezas)"
        )
        print(f"      🎁 {oferta['bonificacion']['mensaje']}")
        if oferta["combo_estrategico"]:
            print(f"      🔗 {oferta['combo_estrategico']['mensaje']}")

# ===============================================
# 6. EXPORTAR OFERTAS PARA STREAMLIT
# ===============================================
print("\n" + "=" * 80)
print("📦 PASO 4: EXPORTANDO OFERTAS")
print("=" * 80)

export_dir = "/home/jupyter/notebooks/data"
os.makedirs(export_dir, exist_ok=True)

# Exportar función como módulo para Streamlit
import json

# Generar ofertas para top 20 clientes
top_clientes = (
    df_cliente_productos.orderBy(desc("total_gasto"))
    .limit(20)
    .select("Cliente")
    .collect()
)
todas_ofertas = []

print("⏳ Generando ofertas para top 20 clientes...")
for cliente_row in top_clientes:
    cliente = cliente_row["Cliente"]
    oferta = generar_oferta_completa(cliente, mes_objetivo="NOV")
    if oferta:
        todas_ofertas.append(oferta)

# Guardar como JSON
with open(
    os.path.join(export_dir, "ofertas_generadas.json"), "w", encoding="utf-8"
) as f:
    json.dump(todas_ofertas, f, ensure_ascii=False, indent=2)

print(f"✅ Ofertas exportadas: {len(todas_ofertas)} clientes")

# También exportar portafolio (para el dashboard)
df_cliente_productos_pd = df_cliente_productos.toPandas()
df_cliente_productos_pd.to_parquet(
    os.path.join(export_dir, "portafolio_clientes.parquet"), index=False
)
print("✅ Portafolio de clientes exportado")

print("\n" + "=" * 80)
print("✅ PROCESO COMPLETADO")
print("=" * 80)
print("\nArchivos generados:")
print("  1. ofertas_generadas.json (Ofertas completas)")
print("  2. portafolio_clientes.parquet")
print("\n💡 Usa estos archivos en el dashboard de Streamlit")
print("=" * 80)

spark.stop()
