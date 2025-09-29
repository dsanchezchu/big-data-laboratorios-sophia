#!/usr/bin/env bash
set -e

SERVICE_TYPE=$1

echo "🚀 Iniciando servicio: $SERVICE_TYPE"
echo "📅 $(date)"
echo "🖥️  Hostname: $(hostname)"
echo "👤 Usuario: $(whoami)"

# Configurar variables de entorno comunes
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export SPARK_HOME=/opt/spark
export PATH="$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$SPARK_HOME/bin:/opt/python-env/bin"

# Función para esperar un puerto
wait_for_port() {
    local host=$1
    local port=$2
    local timeout=${3:-60}
    
    echo "⏳ Esperando $host:$port (timeout: ${timeout}s)..."
    for i in $(seq 1 $timeout); do
        if nc -z $host $port 2>/dev/null; then
            echo "✅ $host:$port está disponible"
            return 0
        fi
        sleep 1
    done
    echo "❌ Timeout esperando $host:$port"
    return 1
}

case $SERVICE_TYPE in
  "namenode")
    echo "📊 Configurando NameNode..."
    
    mkdir -p /data/hdfs/namenode
    chown -R hadoop:hadoop /data/hdfs/namenode
    
    sudo -u hadoop bash -c "
        export JAVA_HOME=$JAVA_HOME
        export HADOOP_HOME=$HADOOP_HOME
        export PATH=$PATH

        # Formatear NameNode si no está formateado
        if [ ! -d '/data/hdfs/namenode/current' ]; then
            echo '🔧 Formateando NameNode...'
            \$HADOOP_HOME/bin/hdfs namenode -format -force -nonInteractive
        fi

        # Iniciar NameNode en background
        echo '🚀 Iniciando NameNode...'
        \$HADOOP_HOME/sbin/hadoop-daemon.sh start namenode

        # Esperar a que HDFS esté listo
        echo '⏳ Esperando a que HDFS esté disponible...'
        until \$HADOOP_HOME/bin/hdfs dfs -ls / >/dev/null 2>&1; do
            sleep 2
        done

        # Crear la carpeta de NiFi
        echo '📂 Creando /user/nifi en HDFS...'
        \$HADOOP_HOME/bin/hdfs dfs -mkdir -p /user/nifi
        \$HADOOP_HOME/bin/hdfs dfs -chown nifi:nifi /user/nifi

        # Mantener contenedor vivo
        tail -f /dev/null
    "
    ;;

    
  "datanode")
    echo "💾 Configurando DataNode..."
    
    # Esperar al NameNode
    wait_for_port namenode 9000 120
    
    # Crear directorios necesarios
    mkdir -p /data/hdfs/datanode
    chown -R hadoop:hadoop /data/hdfs/datanode
    
    exec sudo -u hadoop bash -c "
        export JAVA_HOME=$JAVA_HOME
        export HADOOP_HOME=$HADOOP_HOME
        export PATH=$PATH
        
        echo '🚀 Iniciando DataNode...'
        \$HADOOP_HOME/bin/hdfs datanode
    "
    ;;
    
  "spark-master")
    echo "⚡ Configurando Spark Master..."
    
    # Esperar HDFS
    wait_for_port namenode 9870 120
    
    exec sudo -u hadoop bash -c "
        export JAVA_HOME=$JAVA_HOME
        export SPARK_HOME=$SPARK_HOME
        export PATH=$PATH
        
        echo '🚀 Iniciando Spark Master...'
        \$SPARK_HOME/bin/spark-class org.apache.spark.deploy.master.Master \
            --host 0.0.0.0 \
            --port 7077 \
            --webui-port 8080
    "
    ;;
    
  "spark-worker")
    echo "🔧 Configurando Spark Worker..."
    
    # Esperar Spark Master
    wait_for_port spark-master 7077 120
    
    exec sudo -u hadoop bash -c "
        export JAVA_HOME=$JAVA_HOME
        export SPARK_HOME=$SPARK_HOME
        export PATH=$PATH
        
        echo '🚀 Iniciando Spark Worker...'
        \$SPARK_HOME/bin/spark-class org.apache.spark.deploy.worker.Worker \
            spark://spark-master:7077 \
            --webui-port 8081
    "
    ;;
    
  "jupyter")
    echo "📓 Configurando Jupyter..."
    
    # Esperar servicios principales
    wait_for_port namenode 9870 120
    wait_for_port spark-master 7077 120
    
    # Crear directorios necesarios
    mkdir -p /home/hadoop/.jupyter
    mkdir -p /home/jupyter/notebooks
    chown -R hadoop:hadoop /home/hadoop/.jupyter /home/jupyter
    
    exec sudo -u hadoop bash -c "
        export PATH=/opt/python-env/bin:\$PATH
        export JAVA_HOME=$JAVA_HOME
        export SPARK_HOME=$SPARK_HOME
        export HADOOP_HOME=$HADOOP_HOME
        export PYTHONPATH=/opt/python-env/lib/python3.11/site-packages
        
        # Configurar findspark
        python3 -c '
import sys
sys.path.insert(0, \"/opt/python-env/lib/python3.11/site-packages\")
import findspark
findspark.init(\"/opt/spark\")
import pyspark
print(f\"✅ PySpark {pyspark.__version__} configurado correctamente\")
        '
        
        cd /home/jupyter/notebooks
        echo '🚀 Iniciando Jupyter Lab...'
        jupyter lab \
            --ip=0.0.0.0 \
            --port=8888 \
            --no-browser \
            --allow-root \
            --NotebookApp.token='' \
            --NotebookApp.password='' \
            --NotebookApp.allow_origin='*' \
            --NotebookApp.disable_check_xsrf=True
    "
    ;;
    
  *)
    echo "❌ Tipo de servicio desconocido: $SERVICE_TYPE"
    echo "📋 Servicios disponibles: namenode, datanode, spark-master, spark-worker, jupyter"
    exit 1
    ;;
esac