#!/usr/bin/env bash
set -e

echo "📦 Creando archivo de JARs de Spark para YARN..."

SPARK_HOME=/opt/spark
HADOOP_HOME=/opt/hadoop
HDFS_JAR_PATH=/spark-jars
LOCAL_TAR=/tmp/spark-libs.tgz

# Esperar a que HDFS esté disponible
echo "⏳ Esperando a que HDFS esté disponible..."
until $HADOOP_HOME/bin/hdfs dfs -test -d / >/dev/null 2>&1; do
    sleep 2
done

# Verificar si el archivo ya existe en HDFS
if $HADOOP_HOME/bin/hdfs dfs -test -e $HDFS_JAR_PATH/spark-libs.tgz; then
    echo "✅ spark-libs.tgz ya existe en HDFS, omitiendo creación"
    exit 0
fi

echo "🔨 Empaquetando JARs de Spark..."
cd $SPARK_HOME/jars
tar -czf $LOCAL_TAR *.jar

echo "📊 Tamaño del archivo: $(du -h $LOCAL_TAR | cut -f1)"

echo "📤 Subiendo a HDFS..."
$HADOOP_HOME/bin/hdfs dfs -mkdir -p $HDFS_JAR_PATH
$HADOOP_HOME/bin/hdfs dfs -put -f $LOCAL_TAR $HDFS_JAR_PATH/

echo "🔧 Configurando permisos..."
$HADOOP_HOME/bin/hdfs dfs -chmod 644 $HDFS_JAR_PATH/spark-libs.tgz

echo "✅ spark-libs.tgz creado exitosamente en HDFS"

# Limpiar archivo temporal
rm -f $LOCAL_TAR

# Verificar
echo "📋 Verificación:"
$HADOOP_HOME/bin/hdfs dfs -ls -h $HDFS_JAR_PATH/
