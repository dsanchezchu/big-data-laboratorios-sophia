# Streamlit Dashboard - Recomendador Random Forest

## Flujo de trabajo completo

```
Jupyter Container → Entrena modelo → Exporta archivos → Streamlit lee archivos → Dashboard interactivo
```

## Requisitos
- Python 3.10+ instalado localmente
- Docker Compose corriendo (para entrenar en Jupyter)
- PySpark instalado (el modelo es un PipelineModel de PySpark)

---

## Paso 1: Entrenar y exportar desde Jupyter

### 1.1 Levantar el contenedor Jupyter

```powershell
docker-compose up -d jupyter
```

### 1.2 Acceder a Jupyter

Abre http://localhost:8888 y ejecuta el notebook `proyecto.py` (o el notebook equivalente).

### 1.3 Exportación automática

Al final del script `proyecto.py`, se ejecuta automáticamente:

```python
# Exporta modelo PySpark a: notebooks/models/best_rf_calibrated_pyspark
# Exporta dataset a: notebooks/data/dataset_ml_final.parquet
```

**Archivos generados:**
- `notebooks/models/best_rf_calibrated_pyspark/` (PipelineModel)
- `notebooks/data/dataset_ml_final.parquet` (Dataset procesado)

---

## Paso 2: Reconstruir la imagen (si es primera vez)

```powershell
docker-compose build jupyter
docker-compose up -d jupyter
```

---

## Paso 3: Ejecutar Streamlit dentro del contenedor

```powershell
# Opción A: Desde terminal local
docker exec -it jupyter /opt/python-env/bin/streamlit run /home/jupyter/frontend/streamlit_app.py --server.address 0.0.0.0 --server.port 8501

# Opción B: Abrir terminal en Jupyter y ejecutar
docker exec -it jupyter bash
cd /home/jupyter/frontend
/opt/python-env/bin/streamlit run streamlit_app.py --server.address 0.0.0.0
```

Abrir en navegador: **http://localhost:8501**

---

## Configurar rutas personalizadas (opcional)

Si moviste los archivos a otra ubicación:

```powershell
$env:MODEL_PATH = "C:\ruta\completa\models\best_rf_calibrated_pyspark"
$env:DATA_PATH = "C:\ruta\completa\data\dataset_ml_final.parquet"
streamlit run streamlit_app.py
```

---

## Solución de problemas

### Error: "No such file or directory: ../notebooks/models/..."

**Causa:** Los archivos no se exportaron desde Jupyter o las rutas no coinciden.

**Solución:**
1. Verifica que ejecutaste `proyecto.py` hasta el final (sección "EXPORTACIÓN PARA STREAMLIT")
2. Confirma que existen:
   - `notebooks/models/best_rf_calibrated_pyspark/`
   - `notebooks/data/dataset_ml_final.parquet`

### Error: "ModuleNotFoundError: No module named 'pyspark'"

**Causa:** PySpark no está instalado en el entorno virtual.

**Solución:**
```powershell
pip install pyspark==3.4.1
```

### Streamlit se queda en "Generando recomendaciones..."

**Causa:** El modelo tarda en cargar o hay un error silencioso.

**Solución:**
1. Revisa los logs en la terminal donde corriste `streamlit run`
2. Verifica que el modelo tiene todas las columnas necesarias
3. Reduce el catálogo de productos (cambia `200` a `50` en la línea de `.nlargest()`)

---

## Arquitectura del flujo

```
┌─────────────────────┐
│  Jupyter Container  │
│  (Spark + Python)   │
│                     │
│  1. Carga datos     │
│     desde HDFS      │
│  2. Entrena modelo  │
│  3. Exporta a       │
│     /notebooks/     │ ← Volumen compartido
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Local Machine      │
│  (Streamlit)        │
│                     │
│  1. Lee archivos    │
│     desde           │
│     notebooks/      │
│  2. Carga modelo    │
│     (PySpark local) │
│  3. Sirve dashboard │
└─────────────────────┘
```

---

## Notas técnicas

- **Modelo:** PySpark PipelineModel (no es scikit-learn)
- **Spark local:** Streamlit inicia una SparkSession en modo `local[2]` para cargar el modelo
- **Dataset:** Parquet exportado con Pandas (más liviano que HDFS)
- **Volumen compartido:** `./notebooks` está montado en el contenedor Jupyter y accesible localmente
