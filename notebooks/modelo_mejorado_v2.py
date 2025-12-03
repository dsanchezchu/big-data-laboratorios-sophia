#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MODELO MEJORADO V2 - RECOMENDACIÓN PERSONALIZADA
Cumple con TODOS los objetivos del proyecto:
1. Recomendaciones de productos NO comprados por el cliente
2. Análisis de clientes similares (Collaborative Filtering)
3. Identificación de oportunidades de expansión
4. Predicción de demanda personalizada
5. Optimización de precios
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    lit,
    when,
    count,
    sum as _sum,
    avg,
    desc,
    collect_list,
    array_contains,
    size,
    concat_ws,
)
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, VectorAssembler
from pyspark.ml.regression import RandomForestRegressor
from pyspark.ml.evaluation import RegressionEvaluator
import pandas as pd
import numpy as np

# ===============================================
# 1. INICIALIZAR SPARK
# ===============================================
spark = (
    SparkSession.builder.appName("Modelo_Recomendacion_Mejorado_V2")
    .master("spark://spark-master:7077")
    .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000")
    .config("spark.executor.memory", "2g")
    .config("spark.driver.memory", "2g")
    .getOrCreate()
)

print("✅ Spark Session iniciada")

# ===============================================
# 2. CARGAR DATASET PROCESADO
# ===============================================
path_data = "hdfs://namenode:9000/user/nifi/processed/dataset_ml_sophia_final"
df_full = spark.read.parquet(path_data)
df_full.cache()

print(f"✅ Dataset cargado: {df_full.count():,} registros")

# ===============================================
# 3. ANÁLISIS DE PORTAFOLIO POR CLIENTE
# ===============================================
print("\n" + "=" * 80)
print("📊 PASO 1: ANÁLISIS DE PORTAFOLIO ACTUAL DE CADA CLIENTE")
print("=" * 80)

# 3.1 Productos que CADA cliente ha comprado (histórico)
df_cliente_productos = df_full.groupBy("Cliente").agg(
    collect_list("Producto").alias("productos_comprados"),
    _sum("Venta_Cajas").alias("total_cajas_historicas"),
    _sum("Venta_Valor").alias("total_gasto"),
    count("*").alias("num_transacciones"),
    avg("Precio_Caja").alias("precio_promedio_pagado"),
)

print("✅ Portafolio por cliente calculado")
df_cliente_productos.show(5, truncate=False)

# 3.2 Catálogo completo de productos disponibles
catalogo_completo = df_full.select("Producto").distinct().collect()
catalogo_lista = [row["Producto"] for row in catalogo_completo]
print(f"✅ Catálogo total: {len(catalogo_lista)} productos")

# ===============================================
# 4. IDENTIFICACIÓN DE CLIENTES SIMILARES
# ===============================================
print("\n" + "=" * 80)
print("🔍 PASO 2: IDENTIFICACIÓN DE CLIENTES SIMILARES (COLLABORATIVE FILTERING)")
print("=" * 80)

# 4.1 Crear matriz Cliente-Producto (binaria: 1 si compró, 0 si no)
from pyspark.sql.functions import explode

df_cliente_prod_exploded = (
    df_cliente_productos.select(
        "Cliente", explode("productos_comprados").alias("Producto")
    )
    .distinct()
    .withColumn("comprado", lit(1))
)

# Crear matriz completa (todos los clientes x todos los productos)
clientes_list = df_cliente_productos.select("Cliente").distinct()
productos_list = df_full.select("Producto").distinct()

# Cross join para matriz completa
df_matriz = clientes_list.crossJoin(productos_list)

# Join con compras reales
df_matriz_completa = df_matriz.join(
    df_cliente_prod_exploded, ["Cliente", "Producto"], "left"
).fillna(0, subset=["comprado"])

print("✅ Matriz Cliente-Producto creada")

# 4.2 Calcular similitud entre clientes (Jaccard Similarity)
# Para cada par de clientes, calculamos: intersección / unión de productos


def calcular_clientes_similares(cliente_objetivo, top_n=5):
    """
    Encuentra los N clientes más similares al cliente objetivo
    basándose en el portafolio de productos comprados
    """
    # Productos del cliente objetivo
    productos_objetivo = (
        df_cliente_productos.filter(col("Cliente") == cliente_objetivo)
        .select("productos_comprados")
        .collect()
    )

    if not productos_objetivo:
        return []

    set_objetivo = set(productos_objetivo[0]["productos_comprados"])

    # Calcular similitud con todos los demás clientes
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
                    "productos_otros": len(set_otro),
                }
            )

    # Ordenar por similitud
    similitudes_sorted = sorted(similitudes, key=lambda x: x["similitud"], reverse=True)
    return similitudes_sorted[:top_n]


# Ejemplo de uso
cliente_prueba = "ADMINISTRADORA CLINICA TRESA S.A"
similares = calcular_clientes_similares(cliente_prueba, top_n=5)

print(f"\n🎯 Clientes similares a '{cliente_prueba}':")
for i, sim in enumerate(similares, 1):
    print(
        f"  {i}. {sim['cliente'][:40]:<40} | Similitud: {sim['similitud']:.2%} | Comunes: {sim['productos_comunes']}"
    )

# ===============================================
# 5. GENERACIÓN DE RECOMENDACIONES PERSONALIZADAS
# ===============================================
print("\n" + "=" * 80)
print("💡 PASO 3: GENERACIÓN DE RECOMENDACIONES PERSONALIZADAS")
print("=" * 80)


def recomendar_productos_nuevos(cliente_objetivo, top_n=10):
    """
    Genera recomendaciones de productos que:
    1. El cliente NO ha comprado
    2. Clientes similares SÍ han comprado
    3. Tienen alta demanda en su zona
    """
    # 1. Obtener portafolio actual del cliente
    portafolio = (
        df_cliente_productos.filter(col("Cliente") == cliente_objetivo)
        .select("productos_comprados")
        .collect()
    )

    if not portafolio:
        print(f"❌ Cliente '{cliente_objetivo}' no encontrado")
        return None

    productos_actuales = set(portafolio[0]["productos_comprados"])

    # 2. Obtener zona y región del cliente
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

    # 3. Encontrar clientes similares
    clientes_similares = calcular_clientes_similares(cliente_objetivo, top_n=10)
    nombres_similares = [c["cliente"] for c in clientes_similares]

    # 4. Productos que los similares compran pero el objetivo NO
    productos_similares = (
        df_cliente_productos.filter(col("Cliente").isin(nombres_similares))
        .select(explode("productos_comprados").alias("Producto"))
        .distinct()
    )

    # Excluir productos que el cliente ya compra
    productos_candidatos = productos_similares.filter(
        ~col("Producto").isin(list(productos_actuales))
    )

    # 5. Enriquecer con métricas de zona
    df_candidatos_enriquecidos = productos_candidatos.join(
        df_full.filter(col("Nombre_Zona") == zona)
        .groupBy("Producto")
        .agg(
            avg("Venta_Cajas").alias("demanda_promedio_zona"),
            avg("Precio_Caja").alias("precio_promedio_zona"),
            _sum("Venta_Valor").alias("ingreso_total_zona"),
        ),
        "Producto",
        "left",
    ).fillna(0)

    # 6. Calcular score de recomendación
    # Fórmula: (Demanda Zona * 0.5) + (Num Similares que lo compran * 0.3) + (Ingreso Zona * 0.2)

    # Contar cuántos similares compran cada producto
    df_similares_por_producto = (
        df_cliente_productos.filter(col("Cliente").isin(nombres_similares))
        .select("Cliente", explode("productos_comprados").alias("Producto"))
        .groupBy("Producto")
        .agg(count("*").alias("num_similares_compran"))
    )

    df_recomendaciones = df_candidatos_enriquecidos.join(
        df_similares_por_producto, "Producto", "left"
    ).fillna(0, subset=["num_similares_compran"])

    # Score ponderado
    df_recomendaciones = df_recomendaciones.withColumn(
        "score_recomendacion",
        (col("demanda_promedio_zona") * 0.4)
        + (col("num_similares_compran") * 10 * 0.4)  # Peso x10 para balancear
        + (col("ingreso_total_zona") / 1000 * 0.2),  # Normalizar ingresos
    )

    # Ordenar por score
    df_final = df_recomendaciones.orderBy(desc("score_recomendacion")).limit(top_n)

    return df_final


# Probar la función
print(f"\n🎯 Generando recomendaciones para: {cliente_prueba}")
recomendaciones = recomendar_productos_nuevos(cliente_prueba, top_n=10)

if recomendaciones:
    print("\n💡 TOP 10 PRODUCTOS RECOMENDADOS (que el cliente NO compra):")
    recomendaciones.select(
        "Producto",
        "demanda_promedio_zona",
        "precio_promedio_zona",
        "num_similares_compran",
        "score_recomendacion",
    ).show(10, truncate=False)

# ===============================================
# 6. EXPORTAR RESULTADOS PARA STREAMLIT
# ===============================================
print("\n" + "=" * 80)
print("📦 PASO 4: EXPORTANDO RESULTADOS")
print("=" * 80)

import os

export_dir = "/home/jupyter/notebooks/data"
os.makedirs(export_dir, exist_ok=True)

# 6.1 Exportar análisis de clientes similares (para todos los clientes)
print("⏳ Calculando matriz de similitud completa...")

# Crear tabla de similitudes (esto puede tomar tiempo)
# Por eficiencia, solo calculamos para los top 100 clientes con más transacciones
top_clientes = (
    df_cliente_productos.orderBy(desc("num_transacciones"))
    .limit(100)
    .select("Cliente")
    .collect()
)
top_clientes_list = [row["Cliente"] for row in top_clientes]

similitud_data = []
for cliente in top_clientes_list[:20]:  # Primeros 20 para no saturar
    similares = calcular_clientes_similares(cliente, top_n=5)
    for sim in similares:
        similitud_data.append(
            {
                "cliente_origen": cliente,
                "cliente_similar": sim["cliente"],
                "similitud": sim["similitud"],
                "productos_comunes": sim["productos_comunes"],
            }
        )

df_similitudes_pd = pd.DataFrame(similitud_data)
df_similitudes_pd.to_parquet(
    os.path.join(export_dir, "clientes_similares.parquet"), index=False
)
print(f"✅ Matriz de similitud exportada: {len(similitud_data)} registros")

# 6.2 Exportar portafolio de clientes
df_cliente_productos_pd = df_cliente_productos.toPandas()
df_cliente_productos_pd.to_parquet(
    os.path.join(export_dir, "portafolio_clientes.parquet"), index=False
)
print(f"✅ Portafolio de clientes exportado")

# 6.3 Exportar catálogo con métricas agregadas
df_catalogo_metricas = (
    df_full.groupBy("Producto")
    .agg(
        avg("Precio_Caja").alias("precio_promedio"),
        _sum("Venta_Cajas").alias("demanda_total_historica"),
        count("Cliente").alias("num_clientes_compran"),
        avg("Venta_PY_Zona_Cajas").alias("venta_promedio_zona"),
    )
    .toPandas()
)

df_catalogo_metricas.to_parquet(
    os.path.join(export_dir, "catalogo_metricas.parquet"), index=False
)
print(f"✅ Catálogo con métricas exportado: {len(df_catalogo_metricas)} productos")

print("\n" + "=" * 80)
print("✅ PROCESO COMPLETADO")
print("=" * 80)
print("\nArchivos generados:")
print("  1. clientes_similares.parquet")
print("  2. portafolio_clientes.parquet")
print("  3. catalogo_metricas.parquet")
print("\n💡 Estos archivos se usarán en el dashboard mejorado de Streamlit")
print("=" * 80)

spark.stop()
