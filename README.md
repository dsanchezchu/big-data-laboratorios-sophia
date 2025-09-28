# 🚀 Big Data Laboratorios Sophia - Cluster Hadoop & Spark con Apache NiFi

Este proyecto implementa un cluster completo de Big Data usando **Apache NiFi**, **Hadoop HDFS** y **Apache Spark** ejecutándose en contenedores para el curso de Big Data de Sophia.

## 👥 Equipo de Desarrollo
- **Desarrollador Principal**: Diego Sanchez
- **Curso**: Big Data - 8vo Ciclo
- **Institución**: Sophia

## 🏗️ Arquitectura del Cluster

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           🌐 Interfaces Web                                 │
│  NiFi UI (8082) │ Hadoop UI (9870) │ Spark UI (8080) │ Jupyter Lab (8888) │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ⚡ Capa de Procesamiento                           │
│              Spark Master ──────────── Spark Worker                        │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│                          💾 Capa de Almacenamiento                          │
│               NameNode ──────────────── DataNode                           │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│                          🌊 Capa de Ingesta de Datos                        │
│                              Apache NiFi                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## � Requisitos Previos

### 🖥️ Hardware Mínimo
- **RAM**: 8GB (recomendado 16GB)
- **CPU**: 4 cores (recomendado 8 cores)  
- **Disco**: 50GB libres (para datos y contenedores)

### 💻 Software Requerido
1. **Docker Desktop**: [Descargar aquí](https://www.docker.com/products/docker-desktop/)
2. **Docker Compose**: (incluido con Docker Desktop)
3. **Git**: Para clonar el repositorio

### 🔧 Verificar Instalación
```bash
# Verificar Docker
docker --version
docker-compose --version

# Verificar que Docker esté ejecutándose
docker ps
```

## 🚀 Guía de Instalación Paso a Paso

### 🌐 **Opción 1: GitHub Codespaces** (Recomendado - Sin instalación)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/dsanchezchu/big-data-laboratorios-sophia)

1. **Click en el botón de arriba**
2. **Esperar 2-3 minutos** a que se configure
3. **Ejecutar**: `./setup.sh`
4. **¡Listo!** - Ver [Guía de Codespaces](CODESPACES.md)

### 💻 **Opción 2: Instalación Local**

### 1️⃣ **Clonar el Repositorio**
```bash
git clone https://github.com/dsanchezchu/big-data-laboratorios-sophia.git
cd big-data-laboratorios-sophia
```

### 2️⃣ **Construir las Imágenes** (Primera vez o después de cambios)
```bash
# Limpiar contenedores anteriores (opcional)
docker-compose down --volumes

# Construir imágenes (puede tardar 5-10 minutos la primera vez)
docker-compose build --no-cache
```

### 3️⃣ **Iniciar el Cluster**
```bash
docker-compose up -d
```

### 4️⃣ **Verificar que Todo Funcione**
```bash
# En Windows PowerShell
docker-compose ps

# En Linux/Mac
chmod +x test-cluster.sh
./test-cluster.sh
```

### 5️⃣ **Acceder a las Interfaces**

| 🌐 Servicio | 📍 URL | 📝 Descripción |
|-------------|--------|----------------|
| **🌊 Apache NiFi UI** | http://localhost:8082 | Ingesta y procesamiento de flujos de datos |
| **💾 Hadoop HDFS UI** | http://localhost:9870 | Administración del sistema de archivos distribuido |
| **⚡ Spark Master UI** | http://localhost:8080 | Monitor del cluster Spark |
| **🔧 Spark Worker UI** | http://localhost:8081 | Estado del worker Spark |
| **📊 Jupyter Lab** | http://localhost:8888 | Notebooks interactivos |

## 🔑 Credenciales de Acceso

### 🌊 Apache NiFi
- **Usuario**: `admin`
- **Contraseña**: `ctsBtRBKHRAx69EqUghvvgEvjnaLjFEB`
- **URL**: http://localhost:8082

### 📊 Token de Jupyter

Para obtener el token de acceso a Jupyter:

### Windows PowerShell:
```powershell
docker-compose logs jupyter | Select-String -Pattern "token|http://"
```

### Linux/Mac:
```bash
docker-compose logs jupyter | grep -E "(token|http://)"
```

## 🛠️ Componentes del Sistema

### 📦 Contenedores Incluidos
- **🌊 Apache NiFi**: Ingesta y procesamiento de flujos de datos (Puerto 8082)
- **💾 NameNode**: Gestiona metadatos HDFS (Puerto 9870)
- **💾 DataNode**: Almacena datos distribuidos  
- **⚡ Spark Master**: Coordinador de trabajos Spark (Puerto 8080)
- **⚡ Spark Worker**: Ejecutor de tareas Spark (Puerto 8081)
- **📊 Jupyter Lab**: Entorno de desarrollo interactivo (Token requerido)

### 🔧 Tecnologías Utilizadas
- **Sistema Base**: Debian 12 (Bookworm) para servicios Hadoop/Spark
- **Ingesta de Datos**: Apache NiFi 1.23.2
- **Java**: OpenJDK 17
- **Almacenamiento Distribuido**: Hadoop HDFS 3.3.6
- **Procesamiento Distribuido**: Apache Spark 3.4.1
- **Análisis Interactivo**: Python 3.11 con Jupyter Lab
- **Contenedorización**: Docker & Docker Compose

## 📊 Ejemplos y Flujos de Datos

### 🌊 **Flujo Completo: NiFi → HDFS → Spark → Jupyter**

#### **1. Preparar Datos de Entrada**
```bash
# Crear archivos de ejemplo en el directorio de datos
echo "id,name,age,city
1,Juan,25,Madrid
2,Maria,30,Barcelona
3,Carlos,28,Valencia" > ./data/sample_users.csv
```

#### **2. Configurar Flujo en NiFi**
1. **Acceder a NiFi**: http://localhost:8082
2. **Iniciar sesión** con las credenciales proporcionadas
3. **Crear procesadores**:
   - `GetFile`: Leer archivos de `./data/input/`
   - `ConvertRecord`: Convertir CSV a JSON
   - `PutHDFS`: Escribir a HDFS en `/data/processed/`

#### **3. Configuración de Procesadores NiFi**

**GetFile Processor:**
```
Input Directory: /opt/nifi/nifi-current/data
File Filter: .*\.csv
Keep Source File: false
```

**PutHDFS Processor:**
```
Hadoop Configuration Resources: (dejar vacío)
Directory: /data/nifi_processed
Additional Classpath Resources: (dejar vacío)
```

### 🧪 **Prueba Rápida de HDFS**
```bash
# Crear directorio en HDFS
docker exec namenode hdfs dfs -mkdir /test

# Subir archivo de prueba
echo "Hola Big Data Sophia!" | docker exec -i namenode hdfs dfs -put - /test/saludo.txt

# Leer archivo
docker exec namenode hdfs dfs -cat /test/saludo.txt

# Ver estructura de directorios
docker exec namenode hdfs dfs -ls /
```

### ⚡ **Ejemplo con Spark + Jupyter**
1. Abrir http://localhost:8888 e ingresar el token
2. Crear nuevo notebook de Python
3. Ejecutar código para leer datos procesados por NiFi:
```python
from pyspark.sql import SparkSession

# Crear sesión Spark
spark = SparkSession.builder \
    .appName("NiFi-HDFS-Analysis") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

# Leer datos desde HDFS
df = spark.read.json("hdfs://namenode:9000/data/nifi_processed/*.json")
df.show()

# Análisis básico
df.groupBy("city").count().show()
```

### 📈 **Verificar Estado Completo del Cluster**
```bash
# Verificar estado de todos los servicios
docker-compose ps

# Estado de HDFS (debería mostrar 2 DataNodes)
docker exec namenode hdfs dfsadmin -report

# Ver archivos procesados por NiFi en HDFS
docker exec namenode hdfs dfs -ls /data/

# Verificar logs de NiFi
docker logs nifi --tail 20

# Estado de Spark Master
curl http://localhost:8080
```

## 🔄 Escalabilidad del Cluster

### Para Agregar Más DataNodes:
1. Editar `docker-compose.yml`:
```yaml
  datanode2:
    build: .
    container_name: datanode2
    hostname: datanode2
    # ... misma configuración que datanode1
```

2. Agregar volumen correspondiente:
```yaml
volumes:
  namenode_data:
  datanode1_data:
  datanode2_data:  # Nuevo
```

3. Reiniciar cluster:
```bash
docker-compose down
docker-compose up -d
```

## 🛠️ Comandos Útiles de Administración

### 🐳 Docker
```bash
# Ver logs de servicios específicos
docker-compose logs -f namenode
docker-compose logs -f nifi
docker-compose logs -f spark-master

# Reiniciar un servicio
docker-compose restart nifi
docker-compose restart namenode

# Acceder a un contenedor
docker exec -it namenode bash
docker exec -it nifi bash
docker exec -it jupyter bash

# Ver recursos utilizados
docker stats
```

### 🌊 NiFi
```bash
# Ver logs de NiFi
docker logs nifi

# Reiniciar solo NiFi
docker-compose restart nifi

# Acceder al directorio de datos de NiFi
docker exec -it nifi ls -la /opt/nifi/nifi-current/data

# Ver procesadores activos (desde dentro del contenedor)
docker exec -it nifi curl http://localhost:8080/nifi-api/flow/process-groups/root
```

### 🗄️ HDFS
```bash
# Reportes del sistema
docker exec namenode hdfs dfsadmin -report
docker exec namenode hdfs dfsadmin -safemode get

# Operaciones con archivos
docker exec namenode hdfs dfs -ls /
docker exec namenode hdfs dfs -du -h /
docker exec namenode hdfs dfs -df -h
```

### ⚡ Spark
```bash
# Enviar trabajo Spark (ejemplo)
docker exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --class org.apache.spark.examples.SparkPi \
  $SPARK_HOME/examples/jars/spark-examples_2.12-3.4.1.jar 10
```

## 🆘 Resolución de Problemas

### ❌ **Error: "NiFi UI no carga"**
✅ **Solución**: 
```bash
# Verificar estado de NiFi
docker logs nifi --tail 50

# Reiniciar NiFi si es necesario
docker-compose restart nifi

# Esperar 2-3 minutos para inicialización completa
```

### ❌ **Error: "pip externally-managed-environment"**
✅ **Solución**: El proyecto usa entorno virtual automáticamente. No requiere acción.

### ❌ **Error: "Port already in use"**
✅ **Solución**: 
```bash
docker-compose down
docker system prune -f
docker-compose up -d
```

### ❌ **Error: "Cannot connect to Spark Master"**
✅ **Solución**: Esperar 2-3 minutos para que todos los servicios se inicien completamente.

### ❌ **Jupyter no muestra token**
✅ **Solución**:
```bash
docker-compose restart jupyter
docker-compose logs jupyter | Select-String "token"
```

### ❌ **NiFi no puede conectar con HDFS**
✅ **Solución**:
```bash
# Verificar que HDFS esté funcionando
docker exec namenode hdfs dfsadmin -safemode get

# En NiFi UI, configurar PutHDFS processor:
# - Hadoop Configuration Resources: (dejar vacío)
# - Directory: /data/nifi_processed
# - No configurar Kerberos ni autenticación adicional
```

### ❌ **DataNode no se conecta al NameNode**
✅ **Solución**:
```bash
# Formatear NameNode si es necesario
docker exec namenode hdfs namenode -format -force
docker-compose restart
```

## 🧪 Estructura de Archivos del Proyecto

```
big-data-laboratorios-sophia/
├── 📄 README.md                    # Esta guía
├── 📄 .gitignore                   # Archivos ignorados por Git
├── 📄 docker-compose.yml           # Orquestación de servicios con NiFi
├── 📄 Dockerfile                   # Imagen personalizada Debian + Hadoop + Spark
├── 📄 NIFI-GUIDE.md                # Guía específica de Apache NiFi
├── 📁 config/                      # Configuraciones
│   ├── 📄 core-site.xml           # Configuración core de Hadoop
│   ├── 📄 hdfs-site.xml           # Configuración HDFS
│   ├── 📄 spark-defaults.conf     # Configuración por defecto de Spark
│   └── 📄 jupyter_notebook_config.py # Configuración de Jupyter
├── 📁 scripts/                     # Scripts de automatización
│   ├── 📄 start-services-fixed.sh # Inicio de servicios mejorado
│   ├── 📄 start-nifi.sh           # Script específico para NiFi
│   └── 📄 verify-stack-nifi.ps1   # Verificación del stack completo
├── 📁 data/                        # Datos de entrada para NiFi
│   ├── 📁 input/                   # Archivos de entrada
│   │   ├── 📄 sample_users.csv    # Datos de ejemplo CSV
│   │   └── 📄 sample_logs.json    # Logs de ejemplo JSON
│   └── 📁 processed/               # Archivos procesados
└── 📁 notebooks/                   # Jupyter notebooks
    └── 📄 ejemplo_elt.ipynb       # Ejemplo de procesamiento ELT
```

## 🎯 Casos de Uso Académicos

### 📚 **Para Estudiantes**
- Aprender conceptos de Big Data hands-on
- Experimentar con ingesta de datos usando NiFi
- Comprender flujos ETL/ELT completos
- Desarrollar aplicaciones Spark en Python
- Practicar con sistemas distribuidos reales

### 👨‍🏫 **Para Profesores**
- Demostrar pipelines de datos completos en tiempo real
- Enseñar arquitecturas modernas de Big Data
- Mostrar integración entre diferentes tecnologías
- Asignar proyectos de análisis de datos a gran escala
- Evaluar competencias en ecosistemas Big Data

### 🔬 **Para Proyectos**
- Prototipado de soluciones de ingesta masiva de datos
- Desarrollo de pipelines ETL/ELT robustos
- Análisis de datasets medianos a grandes (GB a TB)
- Testing de arquitecturas distribuidas
- Implementación de data lakes modernos

## 🤝 Contribuir al Proyecto

1. Fork del repositorio
2. Crear branch para nueva funcionalidad: `git checkout -b feature/nueva-funcionalidad`
3. Commit de cambios: `git commit -am 'Add: Nueva funcionalidad de [descripción]'`
4. Push al branch: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

### 🏷️ **Convenciones de Commits**
- `Add:` Nueva funcionalidad
- `Fix:` Corrección de errores
- `Update:` Actualización de documentación o configuración
- `Refactor:` Refactorización de código
- `Remove:` Eliminación de código o archivos

## 📞 Soporte y Contacto

- **Desarrollador**: Diego Sanchez
- **Email Institucional**: [Tu email aquí]
- **Issues**: Reportar problemas en GitHub Issues
- **Discussiones**: Usar GitHub Discussions para preguntas

## 📄 Licencia

Este proyecto es para uso académico en el contexto del curso de Big Data de Sophia.

---

## 🎉 ¡Felicidades!

Si llegaste hasta aquí y todo funciona correctamente, ya tienes un **cluster completo de Big Data con Apache NiFi** totalmente operativo. 

### 🌊 **Tu Stack Incluye:**
- **Ingesta de Datos**: Apache NiFi para capturar y transformar datos
- **Almacenamiento Distribuido**: Hadoop HDFS para big data
- **Procesamiento Distribuido**: Apache Spark para análisis a gran escala  
- **Análisis Interactivo**: Jupyter Lab para data science

**¡Ahora puedes construir pipelines de datos modernos y explorar el fascinante mundo del Big Data!** 🚀

---

*Última actualización: Septiembre 2025 - Diego Sanchez*  
*Versión 2.0 - Con integración Apache NiFi*