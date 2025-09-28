#!/bin/bash

SERVICE_TYPE=$1

echo "🚀 Iniciando servicio: $SERVICE_TYPE"

case $SERVICE_TYPE in
  "namenode")
    echo "📊 Configurando NameNode..."
    
    # Configurar SSH
    sudo service ssh start
    
    # Formatear NameNode si es necesario
    if [ ! -d "/data/hdfs/namenode/current" ]; then
        echo "Formateando NameNode..."
        $HADOOP_HOME/bin/hdfs namenode -format -force -nonInteractive
    fi
    
    # Iniciar NameNode
    $HADOOP_HOME/bin/hdfs namenode
    ;;
    
  "datanode")
    echo "💾 Configurando DataNode..."
    sleep 10  # Esperar al NameNode
    $HADOOP_HOME/bin/hdfs datanode
    ;;
    
  "spark-master")
    echo "⚡ Configurando Spark Master..."
    sleep 15  # Esperar HDFS
    $SPARK_HOME/bin/spark-class org.apache.spark.deploy.master.Master
    ;;
    
  "spark-worker")
    echo "🔧 Configurando Spark Worker..."
    sleep 20  # Esperar Master
    $SPARK_HOME/bin/spark-class org.apache.spark.deploy.worker.Worker spark://spark-master:7077
    ;;
    
  "jupyter")
    echo "📓 Configurando Jupyter..."
    sleep 25  # Esperar servicios
    
    # Configurar variables de entorno para Python
    export PATH="/opt/python-env/bin:$PATH"
    export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
    export SPARK_HOME=/opt/spark
    export HADOOP_HOME=/opt/hadoop
    
    # Crear directorio de configuración
    mkdir -p /home/hadoop/.jupyter
    
    # Inicializar findspark con el entorno virtual
    /opt/python-env/bin/python3 -c "
import findspark
findspark.init('/opt/spark')
import pyspark
print(f'✅ PySpark {pyspark.__version__} configurado correctamente')
"
    
    # Iniciar Jupyter con el entorno virtual
    cd /home/jupyter/notebooks
    /opt/python-env/bin/jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
    ;;
    
  *)
    echo "❌ Tipo de servicio desconocido: $SERVICE_TYPE"
    exit 1
    ;;
esac