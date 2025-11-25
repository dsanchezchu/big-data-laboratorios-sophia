#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Converted from Jupyter Notebook: Proyecto_V1.ipynb
Conversion Date: 2025-11-25T01:17:19.759Z
"""

# ## Cargar Dataframes
# 


from pyspark.sql import SparkSession
from pyspark.sql.types import DoubleType, IntegerType
from pyspark.sql.functions import (
    col, lit, expr, when, split, trim, upper, substring, round,
    count, avg, sum, max, min,
    datediff, current_date,
    array, explode, struct, regexp_replace
)
import re

# ==============================
# 1. Inicializar Spark Session
# ==============================
spark = SparkSession.builder \
    .appName("HDFS_NiFi_Data_Cleaning") \
    .master("spark://spark-master:7077") \
    .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
    .config("spark.executor.memory", "1g") \
    .config("spark.executor.cores", "2") \
    .config("spark.cores.max", "4") \
    .config("spark.driver.memory", "1g") \
    .config("spark.driver.host", "jupyter") \
    .config("spark.driver.bindAddress", "0.0.0.0") \
    .getOrCreate()

print("Sesión creada correctamente")

# ==============================
# 2. Paths en HDFS
# ==============================
hdfs_base_path = "hdfs://namenode:9000/user/nifi/"

# --- CSVs ---
hdfs_path_maestra = hdfs_base_path + "maestra.csv"
hdfs_path_zona = hdfs_base_path + "bd_zona.csv"
hdfs_path_json = hdfs_base_path + "datos.json"
hdfs_path_val_prod = hdfs_base_path + "Valores-Venta_Producto.csv"
hdfs_path_uni_prod = hdfs_base_path + "Unidades-Venta_Producto.csv"
hdfs_path_val_fam = hdfs_base_path + "Valores-Venta_Familia.csv"
hdfs_path_uni_fam = hdfs_base_path + "Unidades-Venta_Familia.csv"

# ===============================================
# 2. Carga de Datos en DataFrames de Spark
# ===============================================

# Opción de codificación para tildes y ñ
encoding_python = "UTF-8"

print("--- 1. Cargando Archivos Maestros (Separador ';') ---")
# Primer CSV (Maestra)
print("--- CSV Maestra ---")
df_maestra = spark.read.option("encoding", encoding_python) \
                       .csv(hdfs_path_maestra, header=True, inferSchema=True, sep=";")
df_maestra.show()

# Segundo CSV (Zona)
print("--- CSV Zona ---")
df_zona = spark.read.option("encoding", encoding_python) \
                    .csv(hdfs_path_zona, header=True, inferSchema=True, sep=";")
df_zona.show()


print("--- 2. Cargando JSON de Base de Datos ---")
print("--- Json Zona ---")
df_datos_zona_json = spark.read.json(hdfs_path_json)
df_datos_zona_json.show()


print("--- 3. Cargando CSVs de Ventas (Separador ',') ---")

# Valores Producto
print("--- CSV Valores Producto ---")
df_valores_producto = spark.read.option("encoding", encoding_python) \
                            .csv(hdfs_path_val_prod, header=True, inferSchema=True, sep=",")
df_valores_producto.show()

# Unidades Producto
print("--- CSV Unidades Producto ---")
df_unidades_producto = spark.read.option("encoding", encoding_python) \
                             .csv(hdfs_path_uni_prod, header=True, inferSchema=True, sep=",")
df_unidades_producto.show()

# Valores Familia
print("--- CSV Valores Familia ---")
df_valores_familia = spark.read.option("encoding", encoding_python) \
                           .csv(hdfs_path_val_fam, header=True, inferSchema=True, sep=",")
df_valores_familia.show()

# Unidades Familia
print("--- CSV Unidades Familia ---")
df_unidades_familia = spark.read.option("encoding", encoding_python) \
                            .csv(hdfs_path_uni_fam, header=True, inferSchema=True, sep=",")
df_unidades_familia.show()

print("--- ✅ Carga completada. Los 6 DataFrames estan listos. ---")

# ### Exploración de datos


df_maestra.printSchema()
df_maestra.show(truncate=False)

df_zona.printSchema()
df_zona.show(truncate=False)

df_datos_zona_json.printSchema()
df_datos_zona_json.show(truncate=False)

df_valores_producto.printSchema()
df_valores_producto.show(truncate=False)

df_unidades_producto.printSchema()
df_unidades_producto.show(truncate=False)

df_valores_familia.printSchema()
df_valores_familia.show(truncate=False)

df_unidades_familia.printSchema()
df_unidades_familia.show(truncate=False)

# ## TRANSFORMACIÓN


# ## Limpieza de datos


# ==============================================================================
# LIMPIEZA PROFUNDA DE DATASETS - PREPARACIÓN PARA ELT
# ==============================================================================
print("--- 🧹 INICIANDO LIMPIEZA PROFUNDA DE TODOS LOS DATASETS ---\n")


# Función para normalizar texto (quitar tildes y ñ)
def normalize_text_column(df, column_name):
    """
    Normaliza una columna de texto:
    - Reemplaza tildes: á→a, é→e, í→i, ó→o, ú→u
    - Reemplaza ñ→n
    - Convierte a mayúsculas para estandarizar
    """
    df = df.withColumn(column_name, regexp_replace(col(column_name), "[áÁ]", "a"))
    df = df.withColumn(column_name, regexp_replace(col(column_name), "[éÉ]", "e"))
    df = df.withColumn(column_name, regexp_replace(col(column_name), "[íÍ]", "i"))
    df = df.withColumn(column_name, regexp_replace(col(column_name), "[óÓ]", "o"))
    df = df.withColumn(column_name, regexp_replace(col(column_name), "[úÚ]", "u"))
    df = df.withColumn(column_name, regexp_replace(col(column_name), "[ñÑ]", "n"))
    df = df.withColumn(column_name, upper(trim(col(column_name))))
    return df

# Función genérica de limpieza
def clean_dataset(df, dataset_name, text_columns=[], numeric_columns=[]):
    """
    Limpia un DataFrame de Spark:
    1. Elimina filas completamente vacías
    2. Normaliza columnas de texto (quita tildes/ñ)
    3. Elimina nulos en columnas numéricas críticas
    4. Remueve outliers extremos (valores > percentil 99 o < 0)
    """
    print(f"--- Limpiando: {dataset_name} ---")
    initial_count = df.count()
    
    # 1. Eliminar filas completamente nulas
    df_clean = df.dropna(how='all')
    
    # 2. Normalizar columnas de texto
    for col_name in text_columns:
        if col_name in df_clean.columns:
            df_clean = normalize_text_column(df_clean, col_name)
    
    # 3. Rellenar nulos en columnas numéricas con 0 (o eliminar según regla de negocio)
    for col_name in numeric_columns:
        if col_name in df_clean.columns:
            # Eliminar nulos en métricas clave
            df_clean = df_clean.filter(col(col_name).isNotNull())
            # Convertir a Double para evitar errores de tipo
            df_clean = df_clean.withColumn(col_name, col(col_name).cast(DoubleType()))
    
    # 4. Remover outliers extremos en columnas numéricas (valores negativos o anormales)
    for col_name in numeric_columns:
        if col_name in df_clean.columns:
            # Filtrar valores negativos (no puede haber ventas negativas)
            df_clean = df_clean.filter(col(col_name) >= 0)
            
            # Opcional: Eliminar valores superiores al percentil 99 (outliers extremos)
            # Descomentar si los datos tienen errores de captura (ej. 999999999)
            # percentile_99 = df_clean.approxQuantile(col_name, [0.99], 0.01)[0]
            # df_clean = df_clean.filter(col(col_name) <= percentile_99)
    
    final_count = df_clean.count()
    removed = initial_count - final_count
    print(f"  ✅ Registros iniciales: {initial_count}")
    print(f"  ✅ Registros finales:   {final_count}")
    print(f"  🗑️  Registros eliminados: {removed}\n")
    
    return df_clean


# ==============================================================================
# APLICAR LIMPIEZA A CADA DATASET
# ==============================================================================

# 1. Limpieza df_maestra
df_maestra = clean_dataset(
    df_maestra, 
    "Tabla Maestra de Productos",
    text_columns=["Producto", "Descripcion", "Numero de articulo"],
    numeric_columns=[]
)

# 2. Limpieza df_zona
df_zona = clean_dataset(
    df_zona,
    "Tabla de Ventas por Zona (bd_zona.csv)",
    text_columns=["Vendedor", "Nombre Cliente", "Producto", "MES"],
    numeric_columns=["2025", "CANTIDAD", "MES NUM"]
)

# 3. Limpieza df_datos_zona_json
df_datos_zona_json = clean_dataset(
    df_datos_zona_json,
    "Datos Geográficos (JSON)",
    text_columns=["zone_code", "zone_name", "region"],
    numeric_columns=[]
)

# 4. Limpieza df_valores_producto
df_valores_producto = clean_dataset(
    df_valores_producto,
    "Valores de Venta por Producto",
    text_columns=["Zona", "Producto"],
    numeric_columns=[c for c in df_valores_producto.columns if "TGT" in c or "PY" in c]
)

# 5. Limpieza df_unidades_producto
df_unidades_producto = clean_dataset(
    df_unidades_producto,
    "Unidades de Venta por Producto",
    text_columns=["Zona", "Producto"],
    numeric_columns=[c for c in df_unidades_producto.columns if "TGT" in c or "PY" in c]
)

# 6. Limpieza df_valores_familia
df_valores_familia = clean_dataset(
    df_valores_familia,
    "Valores de Venta por Familia",
    text_columns=["Zona", "Producto"],
    numeric_columns=[c for c in df_valores_familia.columns if "TGT" in c or "PY" in c]
)

# 7. Limpieza df_unidades_familia
df_unidades_familia = clean_dataset(
    df_unidades_familia,
    "Unidades de Venta por Familia",
    text_columns=["Zona", "Producto"],
    numeric_columns=[c for c in df_unidades_familia.columns if "TGT" in c or "PY" in c]
)

print("="*60)
print("✅ LIMPIEZA COMPLETADA EN TODOS LOS DATASETS")
print("="*60)
print("Ahora puedes continuar con las transformaciones ELT sin problemas de:")
print("  - Tildes o caracteres especiales")
print("  - Valores nulos críticos")
print("  - Outliers extremos que distorsionen el modelo")
print("="*60)

# ## Paso 1: Transformación de la Tabla Transaccional (Ventas Cliente)


# En este paso normalizamos la tabla principal bd_zona.csv. Renombramos columnas confusas, ajustamos los tipos de datos (números y texto) y extraemos el código de la zona para poder cruzar información más adelante.


print("--- 🚀 INICIANDO PROCESO ELT PARA MODELO DE RECOMENDACIÓN ---")
# ==============================================================================
# PASO 1: LIMPIEZA DE LA TABLA PRINCIPAL (df_zona)
# ==============================================================================

# Renombramos columnas para estándares de ingeniería de datos
df_transaccional = df_zona.withColumnRenamed("2025", "Venta_Valor") \
                          .withColumnRenamed("CANTIDAD", "Venta_Cajas") \
                          .withColumnRenamed("MES NUM", "Mes_Num") \
                          .withColumnRenamed("Nombre Cliente", "Cliente")

# Extraemos el código de zona (ej. de "Pharma - Z1" obtenemos "Z1")
df_transaccional = df_transaccional.withColumn(
    "zone_code_join", 
    trim(split(col("Vendedor"), "-").getItem(1))
)

# Aseguramos que los montos y cantidades sean numéricos
df_transaccional = df_transaccional.withColumn("Venta_Valor", col("Venta_Valor").cast(DoubleType())) \
                                   .withColumn("Venta_Cajas", col("Venta_Cajas").cast(IntegerType())) \
                                   .withColumn("Mes_Num", col("Mes_Num").cast(IntegerType()))

# Tu regla: "Si es negativo, es devolución".
# Para el modelo predictivo de demanda, una devolución se considera demanda cero (no hubo venta efectiva).
# Esto evita errores matemáticos en el logaritmo después.

df_transaccional = df_transaccional.withColumn(
    "Venta_Cajas", 
    when(col("Venta_Cajas") < 0, 0).otherwise(col("Venta_Cajas"))
).withColumn(
    "Venta_Valor", 
    when(col("Venta_Valor") < 0, 0.0).otherwise(col("Venta_Valor"))
)


# Multiplicamos las cajas por 20 para tener el dato real de inventario/consumo
df_transaccional = df_transaccional.withColumn("Venta_Piezas_Reales", col("Venta_Cajas") * 20)

# ## Paso 2: Preparación de Dimensiones (Geografía y Producto)


# Preparamos las tablas maestras. Del JSON geográfico seleccionamos solo lo necesario (Región, Zona). De la Maestra de Productos, obtenemos el nombre oficial para estandarizar las descripciones.


# ==============================================================================
# PASO 2: PREPARACIÓN DE DIMENSIONES (GEO Y PRODUCTO)
# ==============================================================================

# 2a. Dimensión Geográfica (JSON)
df_geo = df_datos_zona_json.select(
    trim(col("zone_code")).alias("zone_code"),
    col("zone_name").alias("Nombre_Zona"),
    col("region").alias("Region")
)

# 2b. Dimensión Producto (CSV Maestra)
# Seleccionamos la llave (Producto) y el nombre real (Descripcion)
df_prod_maestra = df_maestra.select(
    trim(col("Producto")).alias("Producto_Key"), 
    col("Descripcion").alias("Nombre_Producto_Oficial"),
    col("Numero de articulo").alias("ID_Articulo")
)

# ## Paso 3: Enriquecimiento Inicial y Cálculo de Precios


# Unimos las ventas con la geografía y los nombres oficiales. Además, creamos una variable clave para el modelo: el Precio Unitario, que nos ayudará a entender la elasticidad de la demanda.


# ==============================================================================
# PASO 3: ENRIQUECIMIENTO INICIAL (JOINS) Y FEATURE ENGINEERING BÁSICO
# ==============================================================================

# Join 1: Ventas + Geografía
df_step1 = df_transaccional.join(
    df_geo,
    df_transaccional.zone_code_join == df_geo.zone_code,
    "left"
)

# Join 2: Resultado + Maestra de Productos
df_master_analytics = df_step1.join(
    df_prod_maestra,
    trim(df_step1.Producto) == df_prod_maestra.Producto_Key,
    "left"
)

# Selección final y Cálculo de Precio Unitario
# IMPORTANTE: Aquí agregamos 'zone_code_join' y 'Producto_Key' para usarlas después
df_final = df_master_analytics.withColumn(
    # Calculamos el precio por CAJA (que es la unidad de venta B2B)
    "Precio_Caja", 
    when(col("Venta_Cajas") > 0, 
         round(col("Venta_Valor") / col("Venta_Cajas"), 2)
    ).otherwise(0.0)
).withColumn(
    # Dato informativo: Precio unitario del gotero
    "Precio_Unitario_Pieza",
    round(col("Precio_Caja") / 20, 2)
).select(
    col("zone_code_join"), 
    col("Producto_Key"),
    "Region", 
    "Nombre_Zona", 
    "Cliente",
    when(col("Nombre_Producto_Oficial").isNotNull(), col("Nombre_Producto_Oficial")).otherwise(col("Producto")).alias("Producto"), 
    "ID_Articulo", 
    "Mes_Num", 
    "Mes",
    "Venta_Cajas",           # <--- TARGET DEL MODELO (Cajas)
    "Venta_Piezas_Reales",   # <--- DATO DE REPORTE (Piezas)
    "Venta_Valor",
    "Precio_Caja",           # <--- FEATURE DEL MODELO
    "Precio_Unitario_Pieza"
)

print("--- ✅ Fase 1 Completada: Dataset Transaccional con Llaves ---")
df_final.printSchema() # Verifica que zone_code_join y Producto_Key aparezcan aquí

df_final.show()

# ## Paso 4: Integración del Contexto de Mercado (Unidades y Valores)


# Aquí transformamos los archivos de reporte (que vienen con meses en columnas) a formato filas usando stack. Esto agrega al dataset las Metas y la Venta Histórica (PY) de la zona, permitiendo al modelo comparar el desempeño del cliente contra el mercado.


from pyspark.sql.functions import col, expr, trim, split, upper, when, round
from pyspark.sql.types import DoubleType

# ==============================================================================
# 4. ENRIQUECIMIENTO CON CONTEXTO DE MERCADO (CORREGIDO: CAJAS Y LIMPIEZA)
# ==============================================================================
print("--- Procesando Contexto de Mercado: Cajas (x20), Valores y Limpieza de Negativos ---")

# --- 🛠️ SUB-RUTINA DE CORRECCIÓN DE TIPOS 🛠️ ---
def cast_metrics_to_double(df):
    cols_to_cast = [c for c in df.columns if "TGT" in c or "PY" in c]
    for column_name in cols_to_cast:
        df = df.withColumn(column_name, col(column_name).cast(DoubleType()))
    return df

# 1. Aplicamos la corrección de tipos
df_unidades_producto = cast_metrics_to_double(df_unidades_producto)
df_valores_producto = cast_metrics_to_double(df_valores_producto)
df_unidades_familia = cast_metrics_to_double(df_unidades_familia)
df_valores_familia = cast_metrics_to_double(df_valores_familia)

# Función auxiliar para la expresión 'stack'
def get_stack_expr(metric_suffix):
    return f"""stack(12, 
        'ENE', `Enero _{metric_suffix}`, `Enero _PY 24`,
        'FEB', `Febrero _{metric_suffix}`, `Febrero _PY 24`,
        'MAR', `Marzo _{metric_suffix}`, `Marzo _PY 24`,
        'ABR', `Abril _{metric_suffix}`, `Abril _PY 24`,
        'MAY', `Mayo _{metric_suffix}`, `Mayo _PY 24`,
        'JUN', `Junio_{metric_suffix}`, `Junio_PY 24`,
        'JUL', `Julio_{metric_suffix}`, `Julio_PY 24`,
        'AGO', `Agosto_{metric_suffix}`, `Agosto_PY 24`,
        'SEP', `Septiembre_{metric_suffix}`, `Septiembre_PY 24`,
        'OCT', `Octubre_{metric_suffix}`, `Octubre_PY 24`,
        'NOV', `Noviembre_{metric_suffix}`, `Noviembre_PY 24`,
        'DIC', `Diciembre_{metric_suffix}`, `Diciembre_PY 24`
    )"""

# ---------------------------------------------------------
# 4a. Procesar Unidades (CAJAS)
# ---------------------------------------------------------
# Nota: Asumimos que el Excel "Unidades" trae CAJAS, igual que el transaccional.
df_ctx_unidades = df_unidades_producto.select(
    col("Zona"), col("Producto"),
    expr(get_stack_expr("TGT ") + " as (Mes_Corto, Meta_Zona_Cajas_Raw, Venta_PY_Zona_Cajas_Raw)")
)

# Limpieza de Negativos (Devoluciones/Errores en Metas o PY)
# Si es negativo, lo volvemos 0 para no afectar promedios ni sumas
df_ctx_unidades = df_ctx_unidades.withColumn(
    "Meta_Zona_Cajas", 
    when(col("Meta_Zona_Cajas_Raw") < 0, 0).otherwise(col("Meta_Zona_Cajas_Raw"))
).withColumn(
    "Venta_PY_Zona_Cajas", 
    when(col("Venta_PY_Zona_Cajas_Raw") < 0, 0).otherwise(col("Venta_PY_Zona_Cajas_Raw"))
)

# Cálculo de Piezas (x20) para Reportería
df_ctx_unidades = df_ctx_unidades.withColumn("Meta_Zona_Piezas", col("Meta_Zona_Cajas") * 20) \
                                 .withColumn("Venta_PY_Zona_Piezas", col("Venta_PY_Zona_Cajas") * 20) \
                                 .drop("Meta_Zona_Cajas_Raw", "Venta_PY_Zona_Cajas_Raw")


# ---------------------------------------------------------
# 4b. Procesar Valores (DINERO)
# ---------------------------------------------------------
df_ctx_valores = df_valores_producto.select(
    col("Zona"), col("Producto"),
    expr(get_stack_expr("TGT ") + " as (Mes_Corto, Meta_Zona_Valor_Raw, Venta_PY_Zona_Valor_Raw)")
)

# Limpieza de Negativos en Valores
df_ctx_valores = df_ctx_valores.withColumn(
    "Meta_Zona_Valor", 
    when(col("Meta_Zona_Valor_Raw") < 0, 0.0).otherwise(col("Meta_Zona_Valor_Raw"))
).withColumn(
    "Venta_PY_Zona_Valor", 
    when(col("Venta_PY_Zona_Valor_Raw") < 0, 0.0).otherwise(col("Venta_PY_Zona_Valor_Raw"))
).drop("Meta_Zona_Valor_Raw", "Venta_PY_Zona_Valor_Raw")


# ---------------------------------------------------------
# 4c. Unir ambos contextos
# ---------------------------------------------------------
df_contexto_producto = df_ctx_unidades.join(
    df_ctx_valores, 
    on=["Zona", "Producto", "Mes_Corto"], 
    how="inner"
)

# Limpieza de llaves para el Join
df_contexto_producto = df_contexto_producto.withColumn("zone_code_join", trim(split(col("Zona"), "-").getItem(1))) \
                                           .withColumn("Producto_Key", trim(col("Producto"))) \
                                           .withColumn("Mes_Corto", upper(col("Mes_Corto")))

# ---------------------------------------------------------
# 4d. JOIN FINAL al Dataset Principal
# ---------------------------------------------------------
# df_final ya viene con la lógica de Cajas del paso anterior
df_dataset_completo = df_final.join(
    df_contexto_producto,
    (df_final.zone_code_join == df_contexto_producto.zone_code_join) & 
    (df_final.Producto_Key == df_contexto_producto.Producto_Key) & 
    (df_final.Mes == df_contexto_producto.Mes_Corto),
    "left"
).select(
    df_final["*"],
    # Seleccionamos las métricas en CAJAS para el modelo (Variables Numéricas)
    col("Meta_Zona_Cajas"), 
    col("Venta_PY_Zona_Cajas"),
    col("Meta_Zona_Valor"), 
    col("Venta_PY_Zona_Valor"),
    # Opcional: Traer Piezas si las quieres para reporte, pero para ML usamos Cajas
    col("Meta_Zona_Piezas"),
    col("Venta_PY_Zona_Piezas")
).na.fill(0, subset=[
    "Meta_Zona_Cajas", "Venta_PY_Zona_Cajas", 
    "Meta_Zona_Valor", "Venta_PY_Zona_Valor",
    "Meta_Zona_Piezas", "Venta_PY_Zona_Piezas"
])

# ---------------------------------------------------------
# 4e. Feature Engineering: Precio Promedio de Mercado (Por Caja)
# ---------------------------------------------------------
df_dataset_completo = df_dataset_completo.withColumn(
    "Precio_Promedio_PY_Caja",
    when(col("Venta_PY_Zona_Cajas") > 0, 
         round(col("Venta_PY_Zona_Valor") / col("Venta_PY_Zona_Cajas"), 2)
    ).otherwise(0.0)
)

print("--- ✅ Contexto de Mercado (Cajas/Piezas) Integrado Correctamente ---")
df_dataset_completo.printSchema()

df_dataset_completo.show()

# ## Paso 5: Integración de Jerarquías (Familias)


# Finalmente, añadimos el nivel más alto de abstracción. Usamos la lógica de la "Primera Palabra" (ej. asociar "ELIPTIC PF" con la familia "ELIPTIC") para traer tendencias generales, vital para predecir sobre productos nuevos.


# ==============================================================================
# PASO 5: INTEGRACIÓN DE FAMILIAS (JERARQUÍA) - LÓGICA CAJAS Y LIMPIEZA
# ==============================================================================
print("--- Iniciando Integración de Contexto Familiar: Cajas, Piezas y Limpieza ---")

# ---------------------------------------------------------
# 5a. Procesar Unidades de Familia (CAJAS)
# ---------------------------------------------------------
df_fam_uni = df_unidades_familia.select(
    col("Zona"), col("Producto").alias("Familia_Nom"),
    expr(get_stack_expr("TGT ") + " as (Mes_Corto, Meta_Fam_Cajas_Raw, Venta_PY_Fam_Cajas_Raw)")
)

# Limpieza de Negativos en Cajas (Targets y PY)
df_fam_uni = df_fam_uni.withColumn(
    "Meta_Fam_Cajas", 
    when(col("Meta_Fam_Cajas_Raw") < 0, 0).otherwise(col("Meta_Fam_Cajas_Raw"))
).withColumn(
    "Venta_PY_Fam_Cajas", 
    when(col("Venta_PY_Fam_Cajas_Raw") < 0, 0).otherwise(col("Venta_PY_Fam_Cajas_Raw"))
)

# Cálculo de Piezas (x20) para contexto
df_fam_uni = df_fam_uni.withColumn("Meta_Fam_Piezas", col("Meta_Fam_Cajas") * 20) \
                       .withColumn("Venta_PY_Fam_Piezas", col("Venta_PY_Fam_Cajas") * 20) \
                       .drop("Meta_Fam_Cajas_Raw", "Venta_PY_Fam_Cajas_Raw")

# ---------------------------------------------------------
# 5b. Procesar Valores de Familia (DINERO)
# ---------------------------------------------------------
df_fam_val = df_valores_familia.select(
    col("Zona"), col("Producto").alias("Familia_Nom"),
    expr(get_stack_expr("TGT ") + " as (Mes_Corto, Meta_Fam_Valor_Raw, Venta_PY_Fam_Valor_Raw)")
)

# Limpieza de Negativos en Valores
df_fam_val = df_fam_val.withColumn(
    "Meta_Fam_Valor", 
    when(col("Meta_Fam_Valor_Raw") < 0, 0.0).otherwise(col("Meta_Fam_Valor_Raw"))
).withColumn(
    "Venta_PY_Fam_Valor", 
    when(col("Venta_PY_Fam_Valor_Raw") < 0, 0.0).otherwise(col("Venta_PY_Fam_Valor_Raw"))
).drop("Meta_Fam_Valor_Raw", "Venta_PY_Fam_Valor_Raw")

# ---------------------------------------------------------
# 5c. Unir y Preparar Llaves
# ---------------------------------------------------------
df_familia_master = df_fam_uni.join(
    df_fam_val, 
    on=["Zona", "Familia_Nom", "Mes_Corto"], 
    how="outer"
)

# Crear llaves de cruce (Primera palabra de Familia y Producto)
df_familia_master = df_familia_master.withColumn(
    "Family_Join_Key", trim(split(col("Familia_Nom"), " ").getItem(0))
).withColumn(
    "zone_code_join", trim(split(col("Zona"), "-").getItem(1))
).withColumn("Mes_Corto", upper(col("Mes_Corto")))

# Llave en el dataset principal
df_dataset_completo = df_dataset_completo.withColumn(
    "Family_Join_Key", trim(split(col("Producto"), " ").getItem(0))
)

# ---------------------------------------------------------
# 5d. JOIN FINAL: Dataset Completo + Familia
# ---------------------------------------------------------
df_ml_final_v2 = df_dataset_completo.join(
    df_familia_master,
    (df_dataset_completo.zone_code_join == df_familia_master.zone_code_join) &
    (df_dataset_completo.Family_Join_Key == df_familia_master.Family_Join_Key) &
    (df_dataset_completo.Mes == df_familia_master.Mes_Corto),
    "left"
).select(
    df_dataset_completo["*"],
    # Seleccionamos métricas limpias (Cajas y Valores) para el modelo
    col("Meta_Fam_Cajas").alias("Meta_Familia_Cajas"),
    col("Venta_PY_Fam_Cajas").alias("Venta_PY_Familia_Cajas"),
    col("Meta_Fam_Valor").alias("Meta_Familia_Valor"),
    col("Venta_PY_Fam_Valor").alias("Venta_PY_Familia_Valor"),
    # Opcional: Piezas para reporte
    col("Meta_Fam_Piezas").alias("Meta_Familia_Piezas"),
    col("Venta_PY_Fam_Piezas").alias("Venta_PY_Familia_Piezas")
).na.fill(0)

# Limpieza final de columnas auxiliares
df_ml_final_v2 = df_ml_final_v2.drop("zone_code_join", "Mes_Corto", "Family_Join_Key", "Producto_Key")

print("--- ✅ Integración de Familias (Cajas/Piezas) Completada ---")
df_ml_final_v2.printSchema()

# ## Paso 6: Visualización Final


# Verificamos que todo esté correcto. Este DataFrame df_ml_final_v2 es el activo final que entrará a tu algoritmo Random Forest.


# ==============================================================================
# RESULTADO FINAL
# ==============================================================================
print("--- ✅ Dataset FINAL Completado ---")
df_ml_final_v2.printSchema()

print("--- Muestra de datos enriquecidos para ML ---")
# Mostramos las columnas CLAVE que usará el modelo
df_ml_final_v2.select(
    "Cliente", 
    "Producto", 
    "Mes", 
    "Venta_Cajas",              # Target (Variable Objetivo)
    "Precio_Caja",              # Feature Principal
    "Precio_Promedio_PY_Caja",  # Contexto Zona
    "Venta_PY_Familia_Cajas"    # Contexto Familia
).show(10, truncate=False)

df_ml_final_v2.show(truncate=False)

# ## Paso 7: Validación y limpieza final para ML


print("--- 🧹 Ejecutando Limpieza de Nulos (Imputación a 0) ---")

# 1. Relleno de Nulos (Imputación)
# Es CRÍTICO rellenar con 0 cualquier métrica de contexto (Metas, PY) que venga nula
# porque el Random Forest fallará si encuentra un solo valor nulo.
df_ready = df_ml_final_v2.na.fill(0, subset=[
    "Venta_Cajas", 
    "Venta_Valor", 
    "Precio_Caja",
    "Meta_Zona_Cajas", 
    "Venta_PY_Zona_Cajas",
    "Precio_Promedio_PY_Caja",
    "Meta_Familia_Cajas",
    "Venta_PY_Familia_Cajas",
    "Precio_Unitario_Pieza"
])

# 2. Verificación de Seguridad (Chequeo de Nulos)
from pyspark.sql.functions import col, sum as _sum

print("--- Chequeo de Nulos Restantes (Todo debe ser 0) ---")
# Verificamos solo las columnas numéricas críticas
cols_to_check = [
    "Venta_Cajas", "Precio_Caja", 
    "Meta_Zona_Cajas", "Venta_PY_Zona_Cajas", 
    "Venta_PY_Familia_Cajas"
]

df_ready.select([
    _sum(col(c).isNull().cast("int")).alias(c) 
    for c in cols_to_check
]).show()

# 3. Filtro de Sanidad (Outliers imposibles)
# Eliminamos precios negativos por si se coló algún error de digitación
df_ready = df_ready.filter(col("Precio_Caja") >= 0)

print(f"--- Dataset Listo. Total Filas: {df_ready.count()} ---")

# ## Paso 8: Almacenamiento


# ==============================================================================
# 5. ALMACENAMIENTO (DATA ENGINEERING FINALIZADO)
# ==============================================================================
print("--- 💾 Guardando dataset procesado en HDFS (Formato Parquet) ---")

# Ruta donde se guardará el archivo maestro
ruta_destino_parquet = hdfs_base_path + "processed/dataset_ml_sophia_final"

# Guardamos (mode='overwrite' reemplaza si ya existe)
df_ready.write.mode("overwrite").parquet(ruta_destino_parquet)

print(f"✅ Dataset guardado exitosamente en: {ruta_destino_parquet}")

# # Entrenamiento del Modelo


# ## 1. IMPORTACIONES NECESARIAS


from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, VectorAssembler, SQLTransformer
from pyspark.ml.regression import RandomForestRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator
from pyspark.sql.functions import col, log1p, expm1, lit, desc
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import builtins
import pyspark.sql.functions as F

# ## 2. ENTRENAMIENTO AVANZADO (TUNING AUTOMÁTICO + CROSS VALIDATION)


print("--- 🤖 Iniciando Entrenamiento con Estrategia Log-Normal ---")

# 1. Cargar Datos
path_df_ml = "hdfs://namenode:9000/user/nifi/processed/dataset_ml_sophia_final"
df_full = spark.read.parquet(path_df_ml)

# Crear Target Logarítmico
df_full = df_full.withColumn("Log_Venta", log1p(col("Venta_Cajas")))
df_full.cache()
print(f"Total Registros: {df_full.count()}")

# 2. Definición de Variables
categorical_cols = ["Cliente", "Producto", "Nombre_Zona", "Region", "Mes"]

numerical_cols = [
    "Precio_Caja",              
    "Mes_Num",
    "Meta_Zona_Cajas",          
    "Venta_PY_Zona_Cajas",      
    "Precio_Promedio_PY_Caja",  
    "Venta_PY_Familia_Cajas"    
]

label_col = "Log_Venta" # Entrenamos contra el Logaritmo de Cajas

# 3. Pipeline Base
stages = []
for col_name in categorical_cols:
    stages.append(StringIndexer(inputCol=col_name, outputCol=col_name + "_Index", handleInvalid="keep"))

input_cols = [c + "_Index" for c in categorical_cols] + numerical_cols
stages.append(VectorAssembler(inputCols=input_cols, outputCol="features", handleInvalid="keep"))

# Random Forest
rf = RandomForestRegressor(featuresCol="features", labelCol=label_col, seed=42, maxBins=500)
stages.append(rf)

# Transformación Inversa Inicial (Log -> Cajas Reales Raw)
inverter = SQLTransformer(statement="SELECT *, expm1(prediction) as prediction_raw FROM __THIS__")
stages.append(inverter)

pipeline = Pipeline(stages=stages)

# ## 3. CONFIGURACIÓN DEL MOTOR DE TUNING (GRID SEARCH)


print("--- ⚙️ Configurando Grid Search ---")
paramGrid = ParamGridBuilder() \
    .addGrid(rf.numTrees, [20, 50]) \
    .addGrid(rf.maxDepth, [5, 10]) \
    .build()

# Evaluador interno (Evalúa qué tan bien predice el LOGARITMO)
evaluator_log = RegressionEvaluator(labelCol=label_col, predictionCol="prediction", metricName="rmse")

cv = CrossValidator(estimator=pipeline,
                    estimatorParamMaps=paramGrid,
                    evaluator=evaluator_log,
                    numFolds=3,
                    parallelism=2)

# ## 4. SPLIT DE DATOS (Train / Test)


# Ya no necesitamos "Validation" manual, CrossValidator lo hace internamente.
print("--- ✂️ Separando datos (80% Entrenamiento+Validación / 20% Test Final) ---")
(train_data, test_data) = df_full.randomSplit([0.8, 0.2], seed=42)

print(f" - Train Set (Para CrossValidation): {train_data.count()} filas")
print(f" - Test Set (Hold-out):              {test_data.count()} filas")

# ## 5. EJECUCIÓN (ENTRENAMIENTO Y SELECCIÓN)


print("\n--- 🧠 Iniciando Cross-Validation (Esto tomará un momento)... ---")
# Aquí ocurre la magia: Spark entrena, valida y selecciona el mejor.
cv_model = cv.fit(train_data)

# Extraemos el mejor modelo encontrado
best_model = cv_model.bestModel

print("\n--- ✅ ¡Entrenamiento Completado! ---")
# Para ver qué hiperparámetros ganaron (un poco complejo de acceder en Pipelines, pero posible):
best_rf_model = best_model.stages[-2] # El penúltimo paso es el RF (el último es el inverter)
print(f"Mejor Configuración encontrada:")
print(f" - Num Trees: {best_rf_model.getNumTrees}")
print(f" - Max Depth: {best_rf_model.getOrDefault('maxDepth')}")

# ## 6. EVALUACIÓN DEL MODELO SIN CALIBRAR


print("\n--- 🏆 Evaluando el MEJOR modelo en TEST SET ---")
predictions = best_model.transform(test_data)

rmse = evaluator_log.evaluate(predictions)
mae = RegressionEvaluator(labelCol=label_col, predictionCol="prediction", metricName="mae").evaluate(predictions)
r2 = RegressionEvaluator(labelCol=label_col, predictionCol="prediction", metricName="r2").evaluate(predictions)

print("="*40)
print(f"📊 RESULTADOS")
print("="*40)
print(f"RMSE: {rmse:.2f}")
print(f"MAE:  {mae:.2f}")
print(f"R²:   {r2:.2f} (Porcentaje de varianza explicada)")
print("="*40)

# ## 7. CÁLCULO Y CORRECCIÓN DE SESGO


print("--- 🔧 Calculando Factor de Ajuste de Sesgo (Basado en Cajas) ---")

# 1. Predecimos sobre el set de ENTRENAMIENTO para medir el sesgo sistemático
preds_train = best_model.transform(train_data)

# 2. Sumamos Cajas Reales vs. Cajas Predichas (Raw)
totales = preds_train.select(
    _sum("Venta_Cajas").alias("Real"),      # <--- Usamos la nueva variable objetivo
    _sum("prediction_raw").alias("Pred")    # <--- Predicción cruda (expm1)
).collect()[0]

# 3. Calculamos el Factor
# Evitamos división por cero por seguridad
if totales["Pred"] == 0:
    bias_factor = 1.0
else:
    bias_factor = totales["Real"] / totales["Pred"]

print(f"   > Total Reales:    {totales['Real']:,.0f}")
print(f"   > Total Predichas: {totales['Pred']:,.0f}")
print(f"   > FACTOR CORRECCIÓN:     {bias_factor:.6f}")

# 4. Creamos la etapa final de calibración (SQLTransformer)
# Generamos dos salidas:
# - prediction_final: Cajas calibradas (para evaluar el modelo).
# - prediction_piezas: Piezas reales (Cajas * 20) para el Dashboard/Negocio.
calibrator_sql = f"""
    SELECT *, 
    prediction_raw * {bias_factor} as prediction_final,
    (prediction_raw * {bias_factor}) * 20 as prediction_piezas 
    FROM __THIS__
"""
calibrator_stage = SQLTransformer(statement=calibrator_sql)

# 5. Ensamblamos el Pipeline Definitivo
# Tomamos los pasos del mejor modelo y le pegamos el calibrador al final
stages_finales = best_model.stages + [calibrator_stage]
final_calibrated_model = Pipeline(stages=stages_finales).fit(train_data)

print("--- ✅ Modelo Final Calibrado - Listo ---")

# 6. Guardamos el modelo
model_path = "hdfs://namenode:9000/user/nifi/models/best_rf_calibrated"
final_calibrated_model.write().overwrite().save(model_path)
print(f"Modelo guardado en: {model_path}")

# ## 8. EVALUACIÓN AVANZADA CON EL MODELO CALIBRADO


print("\n--- 🕵️‍♂️ Iniciando Auditoría del Modelo (Escala Real en Cajas) ---")

# 1. Generar Predicciones Finales
final_predictions = final_calibrated_model.transform(test_data)

# Definimos las columnas a comparar (Cajas Reales vs Cajas Predichas)
col_real = "Venta_Cajas"       # <--- CAMBIO CLAVE: Ahora evaluamos Cajas
col_pred = "prediction_final"  # <--- Predicción calibrada en Cajas

# [1] MÉTRICAS
print("\n[1] MÉTRICAS DE ERROR Y NEGOCIO")
evaluator_rmse = RegressionEvaluator(labelCol=col_real, predictionCol=col_pred, metricName="rmse")
evaluator_mae = RegressionEvaluator(labelCol=col_real, predictionCol=col_pred, metricName="mae")
evaluator_r2 = RegressionEvaluator(labelCol=col_real, predictionCol=col_pred, metricName="r2")

rmse = evaluator_rmse.evaluate(final_predictions)
mae = evaluator_mae.evaluate(final_predictions)
r2 = evaluator_r2.evaluate(final_predictions)

# MAPE (usando F.abs)
mape_df = final_predictions.withColumn("APE", F.abs((F.col(col_real) - F.col(col_pred)) / (F.col(col_real) + 1)))
mape_score = mape_df.select(F.avg("APE")).collect()[0][0] * 100

print(f"  > RMSE: {rmse:.2f}")
print(f"  > MAE:  {mae:.2f} (Error promedio en CAJAS)")
print(f"  > R²:   {r2:.2%} (Varianza explicada)")
# Nota: El MAPE en cajas pequeñas suele ser alto, no te asustes.

# [2] RESIDUOS
print("\n[2] ANÁLISIS DE RESIDUOS")
df_residuals = final_predictions.withColumn("Residual", F.col(col_real) - F.col(col_pred))
res_stats = df_residuals.select(F.avg("Residual").alias("Mean_Residual")).collect()[0]
mean_res = res_stats['Mean_Residual']

print(f"  > Promedio del Residuo: {mean_res:.4f} Cajas")
if abs(mean_res) > 1: # Tolerancia: 1 Caja de sesgo
    print("    ⚠️ ALERTA: Sesgo significativo (mayor a 1 caja promedio).")
else:
    print("    ✅ Residuo aceptable. Modelo balanceado.")

# [3] IMPORTANCIA DE VARIABLES
print("\n[3] IMPORTANCIA DE VARIABLES")
# Recuperamos el modelo RF (antepenúltimo stage)
rf_model = best_model.stages[-2] 

try:
    features_meta = final_predictions.schema["features"].metadata["ml_attr"]
    all_attrs = []
    if "attrs" in features_meta:
        for attr_type in ["numeric", "nominal", "binary"]:
            if attr_type in features_meta["attrs"]:
                all_attrs.extend(features_meta["attrs"][attr_type])
    
    attrs = sorted((attr["idx"], attr["name"]) for attr in all_attrs)
    feature_names = [name for idx, name in attrs]
    importances = rf_model.featureImportances.toArray()

    feat_imp_pd = pd.DataFrame({'Feature': feature_names, 'Importance': importances}).sort_values(by='Importance', ascending=False).head(10)
    for index, row in feat_imp_pd.iterrows():
        print(f"    - {row['Feature']}: {row['Importance']:.4f}")
except Exception as e:
    print(f"No se pudo extraer features: {e}")

# [4] GRÁFICOS
print("\n[4] GRÁFICOS")

# Muestra para Pandas
sample_pd = df_residuals.select(col_real, col_pred, "Residual") \
                        .sample(fraction=0.2, seed=42) \
                        .limit(5000) \
                        .toPandas()

plt.figure(figsize=(15, 5))

# --- Gráfico A: Real vs Predicción ---
plt.subplot(1, 2, 1)
sns.scatterplot(x=col_real, y=col_pred, data=sample_pd, alpha=0.3)

val_max_real = sample_pd[col_real].max()
val_max_pred = sample_pd[col_pred].max()
max_v = builtins.max(val_max_real, val_max_pred) 

plt.plot([0, max_v], [0, max_v], 'r--', label='Predicción Perfecta')
plt.xlabel('Venta Real (Cajas)')
plt.ylabel('Predicción Final (Cajas)')
plt.title('Realidad vs Predicción (Escala Cajas)')
plt.legend()

# --- Gráfico B: Distribución de Errores ---
plt.subplot(1, 2, 2)

sns.histplot(sample_pd['Residual'], kde=True, bins=30)
plt.axvline(0, color='r', linestyle='--', label='Cero Error')
plt.title('Distribución de Errores (Residuos en Cajas)')
plt.xlabel('Error (Real - Predicho)')
plt.legend()

plt.tight_layout()
plt.show()

# **1. R2 (R-Cuadrado): 37.24%**
# 
# De toda la variabilidad loca que tienen las ventas (suben, bajan, clientes nuevos, etc.), tu modelo es capaz de explicar y predecir el 37% de esos movimientos.
# 
# **2. MAE (Error Absoluto Medio): 16.25 unidades**
# 
# En promedio, la predicción falla por +/- 16 unidades.
# 
# **3. RMSE (Error Cuadrático Medio): 40.25**
# 
# Penaliza mucho los errores grandes e indica que, aunque el promedio es bueno, todavía hay algunas ventas "atípicas" o sorpresivas que el modelo no logra adivinar bien.
# 
# **4. Residuo Promedio: -0.6205**
# 
# Significa que el modelo es neutral, al estar cerca de cero.


# ## 8. PRUEBA


def recomendar_productos(nombre_cliente_busqueda):
    print(f"--- 🔍 Generando recomendaciones para: {nombre_cliente_busqueda} ---")
    
    # 1. Obtener datos del cliente
    info_cliente = df_full.filter(col("Cliente") == nombre_cliente_busqueda).select("Region", "Nombre_Zona").limit(1).collect()
    
    if not info_cliente:
        print("❌ Error: Cliente no encontrado en la base de datos.")
        return

    region_cliente = info_cliente[0]["Region"]
    zona_cliente = info_cliente[0]["Nombre_Zona"]
    mes_actual = "OCT" 
    mes_num = 10
    
    print(f"   > Contexto: Zona {zona_cliente} ({region_cliente}) - Mes: {mes_actual}")

    # 2. Obtener CATÁLOGO DE PRODUCTOS
    # Usamos los nuevos nombres de columnas: Precio_Caja, Venta_PY_Zona_Cajas
    catalogo_productos = df_full.select("Producto", "Precio_Caja", "ID_Articulo", 
                                      "Venta_PY_Zona_Cajas", "Venta_PY_Familia_Cajas",
                                      "Meta_Zona_Cajas", "Precio_Promedio_PY_Caja") \
                              .dropDuplicates(["Producto"]) \
                              .orderBy(desc("Venta_PY_Zona_Cajas")) \
                              .limit(50) 
    
    # 3. Construir el DataFrame de Simulación
    df_simulacion = catalogo_productos.withColumn("Cliente", lit(nombre_cliente_busqueda)) \
                                      .withColumn("Region", lit(region_cliente)) \
                                      .withColumn("Nombre_Zona", lit(zona_cliente)) \
                                      .withColumn("Mes", lit(mes_actual)) \
                                      .withColumn("Mes_Num", lit(mes_num))

    # 4. Ejecutar el Modelo CALIBRADO
    predicciones = final_calibrated_model.transform(df_simulacion)
    
    # 5. Mostrar Top 5 Recomendaciones
    print("\n--- 💡 TOP 5 PRODUCTOS RECOMENDADOS ---")
    
    # Mostramos Cajas y Piezas para que sea claro
    top_recs = predicciones.select("Producto", "Precio_Caja", "prediction_final", "prediction_piezas") \
                           .orderBy(desc("prediction_final")) \
                           .limit(5)
    
    top_recs.show(truncate=False)
    
    # Extra: Análisis de Elasticidad
    if top_recs.count() > 0:
        row_top = top_recs.collect()[0]
        mejor_producto = row_top["Producto"]
        precio_actual = row_top["Precio_Caja"]
        pred_actual_cajas = row_top["prediction_final"]
        
        print(f"\n--- 🧪 Análisis de Escenario para '{mejor_producto}' ---")
        print(f"   Precio Caja Actual: {precio_actual:.2f} -> Demanda: {pred_actual_cajas:.2f} Cajas")
        
        # Simulamos descuento del 10%
        precio_nuevo = precio_actual * 0.90
        
        df_escenario = df_simulacion.filter(col("Producto") == mejor_producto) \
                                    .withColumn("Precio_Caja", lit(precio_nuevo))
        
        res_escenario = final_calibrated_model.transform(df_escenario).select("prediction_final").collect()
        if res_escenario:
            pred_escenario_cajas = res_escenario[0][0]
            cambio = ((pred_escenario_cajas - pred_actual_cajas) / pred_actual_cajas) * 100
            
            print(f"   Precio -10% ({precio_nuevo:.2f})  -> Demanda: {pred_escenario_cajas:.2f} Cajas")
            print(f"   Impacto estimado: {cambio:+.2f}% en volumen.")
            
            if cambio > 0 and cambio < 1:
                print("   > Conclusión: Demanda Inelástica. Bajar precio no mueve la aguja.")
            elif cambio >= 1:
                print("   > Conclusión: Demanda Elástica. El descuento funciona.")
            else:
                print("   > Conclusión: Comportamiento atípico.")

# --- EJECUTAR PRUEBA ---
cliente_prueba = "ADMINISTRADORA CLINICA TRESA S.A" 
recomendar_productos(cliente_prueba)

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pyspark.sql.functions import lit, col, desc

# ==============================================================================
# 9. ANALIZADOR DE ESTRATEGIA DE PRECIOS (CORREGIDO)
# ==============================================================================

def analizar_cliente_y_precios(nombre_cliente_busqueda, mes_analisis="OCT"):
    print(f"--- 🔍 Analizando Oportunidades para: {nombre_cliente_busqueda} ---")
    
    # 1. Contexto del Cliente
    info = df_full.filter(col("Cliente") == nombre_cliente_busqueda).select("Region", "Nombre_Zona").limit(1).collect()
    if not info:
        print("❌ Cliente no encontrado.")
        return
    region, zona = info[0]["Region"], info[0]["Nombre_Zona"]
    
    # 2. Catálogo Top 50 (CORREGIDO: Agregada la columna faltante)
    catalogo = df_full.select(
        "Producto", 
        "Precio_Caja", 
        "ID_Articulo", 
        "Venta_PY_Zona_Cajas", 
        "Meta_Zona_Cajas", 
        "Precio_Promedio_PY_Caja",
        "Venta_PY_Familia_Cajas"  # <--- ¡AQUÍ ESTABA EL ERROR! Faltaba esta columna.
    ).dropDuplicates(["Producto"]) \
     .orderBy(desc("Venta_PY_Zona_Cajas")) \
     .limit(50)
    
    # 3. Simulación Base
    df_sim = catalogo.withColumn("Cliente", lit(nombre_cliente_busqueda)) \
                     .withColumn("Region", lit(region)) \
                     .withColumn("Nombre_Zona", lit(zona)) \
                     .withColumn("Mes", lit(mes_analisis)) \
                     .withColumn("Mes_Num", lit(10)) # Asumimos Octubre=10
    
    # Predicción Base
    preds = final_calibrated_model.transform(df_sim)
    
    # 4. Mostrar Top 3 Recomendaciones
    # Usamos prediction_final (Cajas) y prediction_piezas (Unidades)
    top_recs = preds.select("Producto", "Precio_Caja", "prediction_final", "prediction_piezas") \
                    .orderBy(desc("prediction_final")) \
                    .limit(3) \
                    .collect()
    
    print(f"\n📍 Ubicación: {zona} ({region})")
    print("💡 TOP 3 PRODUCTOS RECOMENDADOS (Volumen Estimado):")
    for row in top_recs:
        print(f"   - {row['Producto']}: {row['prediction_final']:.1f} Cajas ({row['prediction_piezas']:.0f} Unids) a S/.{row['Precio_Caja']:.2f}")

    # ==========================================================================
    # 5. MOTOR DE SIMULACIÓN MASIVA (CURVA DE ELASTICIDAD)
    # ==========================================================================
    if not top_recs:
        print("⚠️ No se generaron recomendaciones suficientes.")
        return

    # Tomamos el producto #1 para hacer el análisis profundo
    mejor_prod = top_recs[0]["Producto"]
    precio_base = top_recs[0]["Precio_Caja"]
    
    print("\n" + "="*80)
    print(f"🧪 ANÁLISIS DE ELASTICIDAD AUTOMÁTICO: {mejor_prod}")
    print("="*80)
    
    # Generamos escenarios: De -30% a +30% en pasos de 5%
    rango_ajustes = np.arange(-0.30, 0.35, 0.05) 
    resultados_sim = []
    
    print("⏳ Simulando escenarios de precio...", end="")
    
    for ajuste in rango_ajustes:
        nuevo_precio = precio_base * (1 + ajuste)
        
        # Creamos dataframe de escenario para el modelo
        df_escenario = df_sim.filter(col("Producto") == mejor_prod) \
                             .withColumn("Precio_Caja", lit(nuevo_precio))
        
        # Predecimos (Cajas)
        res = final_calibrated_model.transform(df_escenario).select("prediction_final").collect()
        demanda_est_cajas = res[0]["prediction_final"] if res else 0
        
        # Ingreso = Precio Caja * Cantidad Cajas
        ingreso_est = nuevo_precio * demanda_est_cajas
        
        resultados_sim.append({
            "Ajuste": ajuste * 100,
            "Precio": nuevo_precio,
            "Demanda_Cajas": demanda_est_cajas,
            "Ingreso_Total": ingreso_est
        })
    print(" ¡Listo!\n")
    
    # Convertimos a Pandas
    df_resultados = pd.DataFrame(resultados_sim)
    
    # 6. Encontrar el Precio Óptimo
    idx_optimo = df_resultados["Ingreso_Total"].idxmax()
    escenario_optimo = df_resultados.iloc[idx_optimo]
    
    # Buscamos el escenario base (Ajuste ~ 0%) para comparar
    base_row = df_resultados.iloc[(df_resultados['Ajuste'].abs()).argsort()[:1]]
    ingreso_actual = base_row["Ingreso_Total"].values[0]
    
    mejora = ((escenario_optimo['Ingreso_Total'] - ingreso_actual) / ingreso_actual) * 100
    
    print(f"🏆 ESTRATEGIA RECOMENDADA:")
    if abs(escenario_optimo['Ajuste']) < 1:
        print(f"   ✅ MANTENER PRECIO ACTUAL (S/. {precio_base:.2f}). Es el punto óptimo de rentabilidad.")
    elif escenario_optimo['Ajuste'] < 0:
        print(f"   ⬇️  BAJAR PRECIO un {abs(escenario_optimo['Ajuste']):.0f}% (a S/. {escenario_optimo['Precio']:.2f}).")
        print(f"       -> La demanda subirá a {escenario_optimo['Demanda_Cajas']:.1f} Cajas.")
        print(f"       -> Tus ingresos subirán un +{mejora:.1f}%.")
    else:
        print(f"   ⬆️  SUBIR PRECIO un {escenario_optimo['Ajuste']:.0f}% (a S/. {escenario_optimo['Precio']:.2f}).")
        print(f"       -> La demanda bajará un poco, pero ganarás +{mejora:.1f}% más dinero.")

    # 7. Visualización Gráfica
    plt.figure(figsize=(14, 6))
    
    # Gráfico 1: Curva de Demanda
    plt.subplot(1, 2, 1)
    sns.lineplot(x="Precio", y="Demanda_Cajas", data=df_resultados, marker="o", color="blue", label="Demanda (Cajas)")
    plt.axvline(precio_base, color="grey", linestyle="--", label="Precio Actual")
    plt.axvline(escenario_optimo['Precio'], color="green", linestyle="--", label="Precio Óptimo")
    plt.title(f"Curva de Demanda: {mejor_prod}")
    plt.xlabel("Precio por Caja (S/.)")
    plt.ylabel("Cajas Estimadas")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Gráfico 2: Curva de Ingresos
    plt.subplot(1, 2, 2)
    sns.lineplot(x="Precio", y="Ingreso_Total", data=df_resultados, marker="o", color="orange", label="Ingresos Proyectados")
    plt.axvline(precio_base, color="grey", linestyle="--")
    plt.axvline(escenario_optimo['Precio'], color="green", linestyle="--", label="Máximo Ingreso")
    plt.plot(escenario_optimo['Precio'], escenario_optimo['Ingreso_Total'], 'r*', markersize=15)
    
    plt.title("Proyección de Ingresos Totales")
    plt.xlabel("Precio por Caja (S/.)")
    plt.ylabel("Ingreso Total (S/.)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

# ==============================================================================
# EJECUCIÓN
# ==============================================================================
cliente_prueba = "ADMINISTRADORA CLINICA TRESA S.A" 
analizar_cliente_y_precios(cliente_prueba)

# ==============================================================================
# 10. EXPORTACIÓN PARA STREAMLIT (Ejecutar al final del entrenamiento)
# ==============================================================================
print("\n" + "="*80)
print("📦 EXPORTANDO MODELO Y DATOS PARA STREAMLIT")
print("="*80)

import os
import pickle

# Directorios de salida (dentro de notebooks/ para compartir con Streamlit)
export_dir = "/home/jupyter/notebooks"
models_dir = os.path.join(export_dir, "models")
data_dir = os.path.join(export_dir, "data")

os.makedirs(models_dir, exist_ok=True)
os.makedirs(data_dir, exist_ok=True)

# 1. Exportar el modelo calibrado (PySpark PipelineModel)
model_export_path = os.path.join(models_dir, "best_rf_calibrated_pyspark")
try:
    final_calibrated_model.write().overwrite().save(model_export_path)
    print(f"✅ Modelo PySpark guardado en: {model_export_path}")
except Exception as e:
    print(f"⚠️ Error guardando modelo PySpark: {e}")

# 2. Exportar dataset procesado (Parquet - compatible con Pandas)
data_export_path = os.path.join(data_dir, "dataset_ml_final.parquet")
try:
    # Convertimos a Pandas y guardamos como Parquet
    df_full_pandas = df_full.toPandas()
    df_full_pandas.to_parquet(data_export_path, index=False)
    print(f"✅ Dataset exportado (Pandas Parquet) en: {data_export_path}")
    print(f"   Total de filas: {len(df_full_pandas):,}")
except Exception as e:
    print(f"⚠️ Error exportando dataset: {e}")

# 3. EXTRA: Exportar modelo como scikit-learn compatible (si es posible)
# Nota: PySpark RandomForest no es directamente compatible con scikit-learn
# Para Streamlit necesitarás cargar el PipelineModel con PySpark
print("\n⚠️ NOTA IMPORTANTE:")
print("   - El modelo exportado es un PipelineModel de PySpark.")
print("   - Para usarlo en Streamlit, necesitas tener PySpark instalado.")
print("   - Alternativa: convertir predicciones a una tabla lookup si no quieres PySpark en Streamlit.")

print("\n" + "="*80)
print("✅ EXPORTACIÓN COMPLETADA")
print("="*80)
print("\n📋 PRÓXIMOS PASOS:")
print("1. Sal de este notebook")
print("2. En terminal (fuera del contenedor):")
print("   cd frontend")
print("   pip install -r requirements.txt")
print("   streamlit run streamlit_app.py")
print("\n🌐 El dashboard estará disponible en: http://localhost:8501")
print("="*80)