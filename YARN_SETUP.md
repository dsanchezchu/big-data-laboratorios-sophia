# Guía de Configuración YARN

## 📋 Resumen de Cambios

Se ha configurado **Apache YARN** (Yet Another Resource Negotiator) en tu cluster Hadoop para permitir la ejecución de trabajos Spark en modo distribuido.

## 🎯 Componentes Instalados

### 1. **YARN ResourceManager** (en `namenode`)
- Puerto Web UI: `8088`
- Puerto RPC: `8032`
- Gestiona recursos del cluster
- Programa tareas en NodeManagers

### 2. **YARN NodeManager** (en `datanode1` y `datanode2`)
- Puerto Web UI: `8042` (datanode1), `8043` (datanode2)
- Ejecuta contenedores de aplicaciones
- Reporta recursos al ResourceManager

### 3. **MapReduce JobHistory Server** (en `namenode`)
- Puerto Web UI: `19888`
- Historial de trabajos MapReduce

## 📁 Archivos Creados/Modificados

### Nuevos Archivos de Configuración:
- `config/yarn-site.xml` - Configuración YARN
- `config/mapred-site.xml` - Configuración MapReduce

### Archivos Actualizados:
- `docker-compose.yml` - Agregadas configuraciones YARN y puertos
- `scripts/start-services-fixed.sh` - Scripts para iniciar servicios YARN
- `notebooks/Proyecto_V1 copy.ipynb` - Configuración Spark con YARN

## 🚀 Cómo Usar

### 1. Reconstruir y Levantar el Cluster

```powershell
# Detener servicios actuales
docker-compose down

# Reconstruir imágenes (solo si cambiaste el Dockerfile)
docker-compose build

# Levantar todos los servicios
docker-compose up -d

# Ver logs para verificar que todo inició correctamente
docker-compose logs -f namenode
```

### 2. Verificar que YARN está Funcionando

#### Verificar ResourceManager:
```powershell
# Ver logs del ResourceManager
docker-compose logs namenode | Select-String -Pattern "resourcemanager"

# Acceder a la UI web
# Abrir navegador: http://localhost:8088
```

#### Verificar NodeManagers:
```powershell
# Ver NodeManagers registrados
docker exec -it namenode bash -c "sudo -u hadoop /opt/hadoop/bin/yarn node -list"

# UI de NodeManager 1: http://localhost:8042
# UI de NodeManager 2: http://localhost:8043
```

### 3. Usar YARN desde Jupyter Notebook

Tu notebook ya está configurado. Solo ejecuta las celdas:

```python
# Celda 2: Imports (incluye os)
from pyspark.sql import SparkSession
from pyspark.sql.functions import expr, col, lit
from pyspark.sql.functions import col, count, avg, sum, max, min, when, datediff, current_date
import re
import os

# Celda 3: Inicializar Spark con YARN
os.environ['HADOOP_CONF_DIR'] = '/opt/hadoop/etc/hadoop'
os.environ['YARN_CONF_DIR'] = '/opt/hadoop/etc/hadoop'

spark = SparkSession.builder \
    .appName("HDFS_NiFi_Data_Cleaning") \
    .master("yarn") \
    .config("spark.submit.deployMode", "client") \
    .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
    .config("spark.yarn.am.memory", "1g") \
    .config("spark.executor.memory", "1g") \
    .config("spark.executor.cores", "1") \
    .config("spark.executor.instances", "2") \
    .getOrCreate()

print(f"✅ Spark Session creada exitosamente")
print(f"📊 Spark Master: {spark.sparkContext.master}")
```

### 4. Monitorear Aplicaciones Spark

- **YARN ResourceManager UI**: http://localhost:8088
  - Ver aplicaciones en ejecución
  - Ver aplicaciones completadas
  - Ver recursos del cluster

- **Spark UI** (cuando ejecutes código): http://localhost:4040
  - Detalles de jobs
  - Stages y tasks
  - Ejecutores activos

## 🔧 Configuración de Recursos

### Configuración Actual (ajustable en `yarn-site.xml`):

- **Memoria por NodeManager**: 4096 MB
- **CPU cores por NodeManager**: 2 vcores
- **Memoria mínima por contenedor**: 512 MB
- **Memoria máxima por contenedor**: 4096 MB

### Ajustar Recursos de Spark:

En tu notebook, puedes modificar:

```python
spark = SparkSession.builder \
    .master("yarn") \
    .config("spark.yarn.am.memory", "1g")      # Memoria del Application Master
    .config("spark.executor.memory", "1g")     # Memoria por executor
    .config("spark.executor.cores", "1")       # Cores por executor
    .config("spark.executor.instances", "2")   # Número de executors
    .getOrCreate()
```

## 🐛 Troubleshooting

### Problema: "HADOOP_CONF_DIR or YARN_CONF_DIR must be set"

**Solución**: Las variables ya están configuradas en `docker-compose.yml` para el contenedor `jupyter`. Si el error persiste:

```python
import os
os.environ['HADOOP_CONF_DIR'] = '/opt/hadoop/etc/hadoop'
os.environ['YARN_CONF_DIR'] = '/opt/hadoop/etc/hadoop'
```

### Problema: NodeManagers no se registran

**Verificar logs**:
```powershell
docker-compose logs datanode1 | Select-String -Pattern "nodemanager"
docker-compose logs datanode2 | Select-String -Pattern "nodemanager"
```

**Reiniciar NodeManagers**:
```powershell
docker-compose restart datanode1 datanode2
```

### Problema: Aplicación Spark falla por falta de memoria

**Reducir recursos**:
```python
.config("spark.executor.memory", "512m") \
.config("spark.executor.instances", "1") \
```

## 📊 Comparación: Local vs Standalone vs YARN

| Modo | Configuración | Uso |
|------|--------------|-----|
| **Local** | `.master("local[*]")` | Desarrollo rápido, testing |
| **Standalone** | `.master("spark://spark-master:7077")` | Cluster Spark dedicado |
| **YARN** | `.master("yarn")` | Integración Hadoop, compartir recursos |

## ✅ Verificación Final

```powershell
# 1. Verificar servicios corriendo
docker-compose ps

# 2. Verificar YARN ResourceManager
curl http://localhost:8088

# 3. Verificar NodeManagers registrados
docker exec -it namenode bash -c "sudo -u hadoop /opt/hadoop/bin/yarn node -list"

# 4. Ejecutar celda de Spark en Jupyter
# Debe mostrar: "Spark Master: yarn"
```

## 🎉 Resultado Esperado

Cuando ejecutes tu notebook con YARN:
- ✅ Spark se conecta a YARN
- ✅ YARN crea contenedores en los NodeManagers
- ✅ Los datos se procesan de forma distribuida
- ✅ Puedes monitorear en http://localhost:8088

## 📚 Recursos Adicionales

- YARN UI: http://localhost:8088
- HDFS UI: http://localhost:9870
- Spark Master UI: http://localhost:8080
- Jupyter: http://localhost:8888
- MapReduce JobHistory: http://localhost:19888
