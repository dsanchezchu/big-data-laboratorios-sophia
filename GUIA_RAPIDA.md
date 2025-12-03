# 🚀 Guía Rápida de Ejecución

## Sistema de Recomendación Inteligente - Laboratorios Sophia

---

## ⚡ Inicio Rápido (Opción Más Fácil)

### 1. Ejecutar todo el sistema con UN SOLO comando:

```powershell
.\ejecutar-sistema-completo.ps1
```

Este script automáticamente:
- ✅ Verifica que Docker esté corriendo
- ✅ Entrena el modelo base (si no existe)
- ✅ Genera análisis de recomendaciones
- ✅ Inicia el dashboard de Streamlit

**Dashboard disponible en:** http://localhost:8501

---

## 🔧 Ejecución Manual (Paso a Paso)

### Paso 1: Entrenar el Modelo Base

```powershell
docker exec jupyter spark-submit /home/jupyter/notebooks/proyecto.py
```

**Tiempo estimado:** 10-15 minutos

**Resultado esperado:**
```
✅ Dataset limpio guardado en HDFS
✅ Modelo entrenado y guardado
📊 RMSE: 40.25 | MAE: 16.25 | R²: 37.24%
```

---

### Paso 2: Generar Análisis de Recomendaciones (NUEVO)

```powershell
docker exec jupyter spark-submit /home/jupyter/notebooks/modelo_mejorado_v2.py
```

**Tiempo estimado:** 5-10 minutos

**Resultado esperado:**
```
✅ clientes_similares.parquet
✅ portafolio_clientes.parquet  
✅ catalogo_metricas.parquet
```

---

### Paso 3: Iniciar Dashboard

**Opción A: Dashboard Mejorado (RECOMENDADO)**

```powershell
.\start-streamlit.ps1
```

O manualmente:

```powershell
docker exec -it jupyter bash -c "cd /home/jupyter/frontend && streamlit run streamlit_app_v2.py --server.address 0.0.0.0 --server.port 8501"
```

**Opción B: Dashboard Original (Básico)**

```powershell
docker exec -it jupyter bash -c "cd /home/jupyter/frontend && streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501"
```

---

## 🎯 Funcionalidades del Dashboard V2

### Tab 1: 🎯 Recomendaciones
- Predicción de demanda personalizada
- Filtro "Solo productos NO comprados"
- Cálculo de ingresos estimados
- Potencial de crecimiento

### Tab 2: 👥 Clientes Similares (NUEVO)
- Identificación de clientes con perfil similar
- Índice de similitud (Jaccard)
- Oportunidades basadas en similares

### Tab 3: 📊 Análisis de Portafolio (NUEVO)
- Productos actuales del cliente
- Métricas de gasto y frecuencia
- Comparación con catálogo

### Tab 4: 💰 Optimización de Precios
- Simulación de escenarios de precio
- Curvas de elasticidad
- Precio óptimo automático

### Tab 5: 📈 Proyección Multi-Periodo (NUEVO)
- Proyección 12 meses
- Tendencias estacionales
- Tabla pivote mensual

---

## 🛑 Detener el Sistema

```powershell
# Detener Streamlit (Ctrl+C en la terminal)

# O matar el proceso:
docker exec jupyter pkill -f streamlit
```

---

## 🔍 Verificar Estado

### Ver logs de Spark:
```powershell
docker logs spark-master
```

### Ver logs de Jupyter:
```powershell
docker logs jupyter
```

### Verificar modelo en HDFS:
```powershell
docker exec jupyter hdfs dfs -ls /user/nifi/models/
```

### Verificar datos procesados:
```powershell
docker exec jupyter hdfs dfs -ls /user/nifi/processed/
```

---

## ⚠️ Solución de Problemas

### Problema: "Puerto 8501 ya en uso"

**Solución:**
```powershell
docker exec jupyter pkill -f streamlit
# Luego vuelve a ejecutar start-streamlit.ps1
```

---

### Problema: "Modelo no encontrado"

**Solución:**
```powershell
# Re-entrenar el modelo
docker exec jupyter spark-submit /home/jupyter/notebooks/proyecto.py
```

---

### Problema: "No se puede conectar a Spark"

**Solución:**
```powershell
# Reiniciar contenedores
docker-compose restart spark-master
docker-compose restart jupyter
```

---

### Problema: "Dataset no cargado"

**Solución:**
```powershell
# Verificar que los archivos estén en HDFS
docker exec jupyter hdfs dfs -ls /user/nifi/

# Si no están, ejecuta NiFi para cargar los datos
```

---

## 📊 Casos de Uso Rápidos

### Caso 1: ¿Qué productos nuevos recomendar?

1. Abre http://localhost:8501
2. Selecciona el cliente
3. Tab 1: Activa "Solo productos NO comprados"
4. Click "Generar Recomendaciones"
5. Revisa Top 10 productos

---

### Caso 2: ¿A qué precio vender?

1. Tab 4: Optimización de Precios
2. Selecciona el producto
3. Click "Analizar Elasticidad"
4. Revisa el precio óptimo sugerido

---

### Caso 3: ¿Cuánta demanda tendré?

1. Tab 5: Proyección Multi-Periodo
2. Click "Generar Proyección Anual"
3. Revisa gráfico de tendencias
4. Exporta tabla pivote

---

## 📦 Archivos Generados

```
notebooks/data/
├── dataset_ml_final.parquet       # Dataset completo procesado
├── clientes_similares.parquet     # Matriz de similitud
├── portafolio_clientes.parquet    # Historial de compras
└── catalogo_metricas.parquet      # Métricas agregadas

hdfs://namenode:9000/user/nifi/
├── models/
│   └── best_rf_calibrated/        # Modelo Random Forest
└── processed/
    └── dataset_ml_sophia_final/   # Dataset en HDFS
```

---

## 🎓 Documentación Completa

Para detalles técnicos completos, ver:
- **CUMPLIMIENTO_OBJETIVOS.md** - Validación de objetivos del proyecto
- **notebooks/proyecto.py** - Código del modelo base
- **notebooks/modelo_mejorado_v2.py** - Sistema de recomendación
- **frontend/streamlit_app_v2.py** - Dashboard mejorado

---

## ✅ Checklist de Ejecución

Antes de presentar el proyecto:

- [ ] Contenedores Docker corriendo
- [ ] Datos cargados en HDFS (vía NiFi)
- [ ] Modelo base entrenado (`proyecto.py`)
- [ ] Análisis de recomendaciones generado (`modelo_mejorado_v2.py`)
- [ ] Dashboard funcionando en http://localhost:8501
- [ ] Probar los 5 tabs del dashboard
- [ ] Exportar screenshots/demos

---

## 🚀 Comando Único para Demo

```powershell
# Ejecuta todo y abre el dashboard
.\ejecutar-sistema-completo.ps1
```

**Tiempo total:** ~20-25 minutos (primera vez)

**Luego:** http://localhost:8501 (Dashboard listo para demostrar)

---

## 📞 Soporte

Si tienes problemas, verifica:
1. ¿Docker está corriendo? → `docker ps`
2. ¿Contenedor jupyter activo? → Debe aparecer en `docker ps`
3. ¿Datos en HDFS? → `docker exec jupyter hdfs dfs -ls /user/nifi/`
4. Ver logs → `docker logs jupyter`

---

**Última actualización:** 3 de Diciembre, 2025
**Versión:** 2.0 - Sistema Completo
