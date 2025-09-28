#!/bin/bash

# Inicializar HDFS
echo "Inicializando HDFS..."
$HADOOP_HOME/bin/hdfs namenode -format -force

# Iniciar servicios de HDFS
echo "Iniciando servicios HDFS..."
$HADOOP_HOME/sbin/start-dfs.sh

# Esperar a que HDFS esté listo
sleep 10

# Crear directorios en HDFS
echo "Creando directorios en HDFS..."
$HADOOP_HOME/bin/hdfs dfs -mkdir -p /user/hadoop
$HADOOP_HOME/bin/hdfs dfs -mkdir -p /spark-logs
$HADOOP_HOME/bin/hdfs dfs -mkdir -p /data/input
$HADOOP_HOME/bin/hdfs dfs -mkdir -p /data/output

$HADOOP_HOME/bin/hdfs dfs -chmod -R 755 /
$HADOOP_HOME/bin/hdfs dfs -chown -R hadoop:hadoop /user/hadoop

echo "HDFS inicializado correctamente"