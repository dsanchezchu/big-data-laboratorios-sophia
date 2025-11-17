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
    echo "📊 Configurando NameNode con YARN ResourceManager..."
    
    mkdir -p /data/hdfs/namenode
    chown -R hadoop:hadoop /data/hdfs/namenode
    
    sudo -u hadoop bash -c "
        export JAVA_HOME=$JAVA_HOME
        export HADOOP_HOME=$HADOOP_HOME
        export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
        export YARN_CONF_DIR=$HADOOP_HOME/etc/hadoop
        export PATH=$PATH

        # Formatear NameNode si no está formateado
        if [ ! -d '/data/hdfs/namenode/current' ]; then
            echo '🔧 Formateando NameNode...'
            \$HADOOP_HOME/bin/hdfs namenode -format -force -nonInteractive
        fi

        # Iniciar NameNode en background
        echo '🚀 Iniciando NameNode...'
        \$HADOOP_HOME/bin/hdfs --daemon start namenode

        # Esperar a que HDFS esté listo
        echo '⏳ Esperando a que HDFS esté disponible...'
        until \$HADOOP_HOME/bin/hdfs dfs -ls / >/dev/null 2>&1; do
            sleep 2
        done

        # Esperar a que HDFS salga de safe mode (optimizado: 5 intentos = 15s max)
        echo '🔓 Esperando a que HDFS salga de safe mode...'
        WAIT_COUNT=0
        MAX_WAIT=5
        until \$HADOOP_HOME/bin/hdfs dfsadmin -safemode get | grep -q 'OFF'; do
            echo '⏳ HDFS aún en safe mode, esperando...'
            sleep 3
            WAIT_COUNT=\$((WAIT_COUNT + 1))
            
            # Después de 15 segundos (5 intentos), forzar salida de safe mode
            if [ \$WAIT_COUNT -ge \$MAX_WAIT ]; then
                echo '⚠️  Forzando salida de safe mode...'
                \$HADOOP_HOME/bin/hdfs dfsadmin -safemode leave
                sleep 1
                break
            fi
        done
        echo '✅ HDFS fuera de safe mode'

        # Crear carpetas necesarias en HDFS solo si no existen
        echo '📂 Verificando directorios en HDFS...'
        \$HADOOP_HOME/bin/hdfs dfs -test -d /user/nifi || \$HADOOP_HOME/bin/hdfs dfs -mkdir -p /user/nifi
        \$HADOOP_HOME/bin/hdfs dfs -chown nifi:nifi /user/nifi 2>/dev/null || true
        \$HADOOP_HOME/bin/hdfs dfs -test -d /user/hadoop || \$HADOOP_HOME/bin/hdfs dfs -mkdir -p /user/hadoop
        \$HADOOP_HOME/bin/hdfs dfs -test -d /tmp || (\$HADOOP_HOME/bin/hdfs dfs -mkdir -p /tmp && \$HADOOP_HOME/bin/hdfs dfs -chmod 1777 /tmp)
        \$HADOOP_HOME/bin/hdfs dfs -test -d /spark-logs || (\$HADOOP_HOME/bin/hdfs dfs -mkdir -p /spark-logs && \$HADOOP_HOME/bin/hdfs dfs -chmod 1777 /spark-logs)
        echo '✅ Directorios HDFS verificados'

        # Crear archivo de JARs de Spark en HDFS (solo si no existe)
        if ! \$HADOOP_HOME/bin/hdfs dfs -test -e /spark-jars/spark-libs.tgz; then
            echo '📦 Creando archivo de JARs de Spark para YARN...'
            bash /scripts/init-spark-jars.sh
        else
            echo '✅ spark-libs.tgz ya existe en HDFS'
        fi

        # Iniciar YARN ResourceManager
        echo '🎯 Iniciando YARN ResourceManager...'
        \$HADOOP_HOME/bin/yarn --daemon start resourcemanager
        
        # Esperar a que ResourceManager esté listo
        echo '⏳ Esperando a que YARN ResourceManager esté disponible...'
        for i in {1..15}; do
            if nc -z localhost 8032 2>/dev/null; then
                echo '✅ YARN ResourceManager está disponible'
                break
            fi
            sleep 2
        done

        # Iniciar MapReduce JobHistory Server
        echo '📜 Iniciando MapReduce JobHistory Server...'
        \$HADOOP_HOME/bin/mapred --daemon start historyserver

        echo '✅ NameNode, YARN ResourceManager y JobHistory Server iniciados'

        # Mantener contenedor vivo
        tail -f /dev/null
    "
    ;;

    
  "datanode")
    echo "💾 Configurando DataNode con YARN NodeManager..."
    
    # Esperar al NameNode
    wait_for_port namenode 9000 120
    
    # Esperar a que YARN ResourceManager esté disponible (con timeout razonable)
    echo "⏳ Esperando YARN ResourceManager..."
    YARN_WAIT=0
    until nc -z namenode 8032 2>/dev/null || [ $YARN_WAIT -ge 45 ]; do
        echo "⏳ Esperando ResourceManager en namenode:8032 ($YARN_WAIT/45s)..."
        sleep 3
        YARN_WAIT=$((YARN_WAIT + 3))
    done
    
    if nc -z namenode 8032 2>/dev/null; then
        echo "✅ YARN ResourceManager disponible"
    else
        echo "⚠️  ResourceManager no disponible después de 45s, continuando de todas formas..."
    fi
    
    # Crear directorios necesarios
    mkdir -p /data/hdfs/datanode
    mkdir -p /data/yarn/local
    mkdir -p /data/yarn/logs
    chown -R hadoop:hadoop /data/hdfs/datanode
    chown -R hadoop:hadoop /data/yarn
    
    sudo -u hadoop bash -c "
        export JAVA_HOME=$JAVA_HOME
        export HADOOP_HOME=$HADOOP_HOME
        export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
        export YARN_CONF_DIR=$HADOOP_HOME/etc/hadoop
        export PATH=$PATH
        
        echo '🚀 Iniciando DataNode...'
        \$HADOOP_HOME/bin/hdfs --daemon start datanode
        
        echo '⏳ Esperando a que DataNode esté listo...'
        sleep 5
        
        echo '🎯 Iniciando YARN NodeManager...'
        \$HADOOP_HOME/bin/yarn --daemon start nodemanager
        
        echo '✅ DataNode y NodeManager iniciados'
        
        # Mantener contenedor vivo
        tail -f /dev/null
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