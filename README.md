# 🚀 Big Data Laboratorios Sophia - Cluster Hadoop & Spark

Este proyecto implementa un cluster completo de Big Data usando **Hadoop HDFS** y **Apache Spark** ejecutándose en contenedores **Debian 12** para el curso de Big Data de Sophia.

## 👥 Equipo de Desarrollo
- **Desarrollador Principal**: Diego Sanchez
- **Curso**: Big Data - 8vo Ciclo
- **Institución**: Sophia

## 🏗️ Arquitectura del Cluster

```
┌─────────────────────────────────────────────────────────────┐
│                    🌐 Interfaces Web                        │
│  Hadoop UI (9870) │ Spark UI (8080) │ Jupyter Lab (8888)   │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    ⚡ Capa de Procesamiento                  │
│          Spark Master ──────── Spark Worker                │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    💾 Capa de Almacenamiento                │
│          NameNode ──────────── DataNode                    │
└─────────────────────────────────────────────────────────────┘
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
| **Hadoop HDFS UI** | http://localhost:9870 | Administración del sistema de archivos distribuido |
| **Spark Master UI** | http://localhost:8080 | Monitor del cluster Spark |
| **Spark Worker UI** | http://localhost:8081 | Estado del worker Spark |
| **Jupyter Lab** | http://localhost:8888 | Notebooks interactivos |

## � Token de Jupyter

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
- **NameNode**: Gestiona metadatos HDFS (Puerto 9870)
- **DataNode**: Almacena datos distribuidos  
- **Spark Master**: Coordinador de trabajos Spark (Puerto 8080)
- **Spark Worker**: Ejecutor de tareas Spark (Puerto 8081)
- **Jupyter Lab**: Entorno de desarrollo interactivo (Token requerido)

### 🔧 Tecnologías Utilizadas
- **Sistema Base**: Debian 12 (Bookworm)
- **Java**: OpenJDK 17
- **Hadoop**: 3.3.6
- **Spark**: 3.4.1
- **Python**: 3.11 con entorno virtual
- **Jupyter Lab**: Última versión

## 📊 Ejemplos y Pruebas

### 🧪 Prueba Rápida de HDFS
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

### ⚡ Ejemplo con Spark + Jupyter
1. Abrir http://localhost:8888 e ingresar el token
2. Abrir el notebook `notebooks/ejemplo_elt.ipynb`
3. Ejecutar las celdas paso a paso
4. Ver resultados en tiempo real

### 📈 Verificar Estado del Cluster
```bash
# Estado de HDFS
docker exec namenode hdfs dfsadmin -report

# Estado de Spark
docker exec namenode hdfs dfs -ls /
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
# Ver logs de un servicio específico
docker-compose logs -f namenode
docker-compose logs -f spark-master

# Reiniciar un servicio
docker-compose restart namenode

# Acceder a un contenedor
docker exec -it namenode bash
docker exec -it jupyter bash

# Ver recursos utilizados
docker stats
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
├── 📄 docker-compose.yml           # Orquestación de servicios
├── 📄 Dockerfile                   # Imagen personalizada Debian + Hadoop + Spark
├── 📄 test-cluster.sh              # Script de pruebas automatizadas
├── 📁 config/                      # Configuraciones
│   ├── 📄 core-site.xml           # Configuración core de Hadoop
│   ├── 📄 hdfs-site.xml           # Configuración HDFS
│   ├── 📄 spark-defaults.conf     # Configuración por defecto de Spark
│   └── 📄 jupyter_notebook_config.py # Configuración de Jupyter
├── 📁 scripts/                     # Scripts de automatización
│   ├── 📄 start-services.sh       # Inicio de servicios
│   ├── 📄 dynamic-datanodes.sh    # Gestión dinámica de DataNodes
│   └── 📄 scale-cluster.sh        # Escalamiento del cluster
└── 📁 notebooks/                   # Jupyter notebooks
    └── 📄 ejemplo_elt.ipynb       # Ejemplo de procesamiento ELT
```

## 🎯 Casos de Uso Académicos

### 📚 **Para Estudiantes**
- Aprender conceptos de Big Data hands-on
- Experimentar con HDFS y operaciones distribuidas
- Desarrollar aplicaciones Spark en Python
- Comprender arquitecturas de cluster

### 👨‍🏫 **Para Profesores**
- Demostrar conceptos en tiempo real
- Asignar proyectos prácticos
- Evaluar conocimientos con ejercicios reales
- Mostrar diferencias entre procesamiento local vs distribuido

### 🔬 **Para Proyectos**
- Prototipado de soluciones Big Data
- Testing de algoritmos distribuidos
- Análisis de datasets medianos (< 10GB)
- Desarrollo de pipelines ETL/ELT

## 🤝 Contribuir al Proyecto

1. Fork del repositorio
2. Crear branch para nueva funcionalidad: `git checkout -b feature/nueva-funcionalidad`
3. Commit de cambios: `git commit -am 'Agregar nueva funcionalidad'`
4. Push al branch: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

## 📞 Soporte y Contacto

- **Desarrollador**: Diego Sanchez
- **Email Institucional**: [Tu email aquí]
- **Issues**: Reportar problemas en GitHub Issues
- **Discussiones**: Usar GitHub Discussions para preguntas

## 📄 Licencia

Este proyecto es para uso académico en el contexto del curso de Big Data de Sophia.

---

## 🎉 ¡Felicidades!

Si llegaste hasta aquí y todo funciona correctamente, ya tienes un cluster de Big Data completamente funcional. 

**¡Ahora puedes explorar el fascinante mundo del procesamiento distribuido!** 🚀

---

*Última actualización: Septiembre 2025 - Diego Sanchez*