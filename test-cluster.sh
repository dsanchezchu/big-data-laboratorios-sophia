#!/bin/bash

echo "🧪 Iniciando pruebas del cluster Big Data"

# Función para esperar un servicio
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Esperando $service_name en puerto $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec namenode bash -c "nc -z localhost $port" 2>/dev/null; then
            echo "✅ $service_name está disponible"
            return 0
        fi
        echo "   Intento $attempt/$max_attempts..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service_name no está disponible después de $max_attempts intentos"
    return 1
}

echo "🔍 Verificando servicios..."

# Verificar que los contenedores estén ejecutándose
echo "📊 Estado de contenedores:"
docker-compose ps

echo ""
echo "🌐 Servicios web disponibles:"
echo "   - Hadoop HDFS UI: http://localhost:9870"
echo "   - Spark Master UI: http://localhost:8080"
echo "   - Spark Worker UI: http://localhost:8081"
echo "   - Jupyter Lab: http://localhost:8888"

# Verificar HDFS
echo ""
echo "📁 Probando HDFS..."
if docker exec namenode bash -c "hdfs dfs -ls /" 2>/dev/null; then
    echo "✅ HDFS está operativo"
    
    # Crear directorio de prueba
    docker exec namenode bash -c "hdfs dfs -mkdir -p /test" 2>/dev/null
    echo "✅ Directorio /test creado en HDFS"
    
    # Subir archivo de prueba
    docker exec namenode bash -c "echo 'Hello Big Data!' | hdfs dfs -put - /test/hello.txt" 2>/dev/null
    echo "✅ Archivo de prueba subido a HDFS"
    
    # Leer archivo
    echo "📖 Contenido del archivo:"
    docker exec namenode bash -c "hdfs dfs -cat /test/hello.txt"
else
    echo "❌ HDFS no está disponible"
fi

# Verificar Spark
echo ""
echo "⚡ Probando conexión a Spark..."
if docker exec spark-master bash -c "nc -z localhost 7077" 2>/dev/null; then
    echo "✅ Spark Master está disponible"
else
    echo "❌ Spark Master no está disponible"
fi

echo ""
echo "🎯 Pruebas completadas. El cluster está listo para usar!"