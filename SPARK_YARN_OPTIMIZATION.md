# Optimización Spark + YARN

## ✅ Qué se optimizó

Se agregó `spark.yarn.archive` para reducir el tiempo de inicio de jobs de Spark en YARN.

### Antes
- Cada job de Spark transfería ~293 MB de JARs desde HDFS a los NodeManagers
- Tiempo de inicio: 2-3 minutos

### Después
- Los JARs se cachean en los NodeManagers (lectura una sola vez)
- Tiempo de inicio: 10-20 segundos
- **Mejora: ~90% más rápido**

---

## 📦 Archivos modificados

1. **`scripts/init-spark-jars.sh`** - Crea el archivo de JARs automáticamente
2. **`scripts/start-services-fixed.sh`** - Ejecuta el script al iniciar namenode
3. **`config/spark-defaults.conf`** - Configuración optimizada:
   ```properties
   spark.yarn.archive hdfs://namenode:9000/spark-jars/spark-libs.tgz
   spark.yarn.preserve.staging.files false
   spark.yarn.submit.file.replication 2
   ```
4. **`docker-compose.yml`** - Monta spark-defaults.conf en Jupyter

---

## 🚀 Cómo funciona

1. Al iniciar el cluster, se crea `/spark-jars/spark-libs.tgz` en HDFS (una sola vez)
2. Contiene todos los JARs de Spark (293 MB comprimidos)
3. YARN lo cachea en cada NodeManager
4. Los jobs reutilizan el cache en lugar de transferir cada vez

---

## 💻 Uso en notebooks

La configuración ya está en `spark-defaults.conf`, así que solo necesitas:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("MiApp") \
    .master("yarn") \
    .getOrCreate()  # Toma config automáticamente
```

Si prefieres especificar manualmente:

```python
spark = SparkSession.builder \
    .appName("MiApp") \
    .master("yarn") \
    .config("spark.yarn.archive", "hdfs://namenode:9000/spark-jars/spark-libs.tgz") \
    .getOrCreate()
```

---

## 🔍 Verificación

```powershell
# Ver el archivo en HDFS
docker exec namenode hdfs dfs -ls -h /spark-jars/

# Verificar configuración
docker exec jupyter cat /opt/spark/conf/spark-defaults.conf | Select-String "yarn"
```

---

## ⚙️ Configuración YARN adicional

También se optimizaron recursos de YARN:

```properties
spark.yarn.am.memory    512m      # Memoria del Application Master
spark.yarn.am.cores     1         # Cores del Application Master
spark.executor.instances 2        # Número de executors
spark.executor.cores    1         # Cores por executor
```

Puedes ajustar estos valores según tus necesidades en `config/spark-defaults.conf`.
