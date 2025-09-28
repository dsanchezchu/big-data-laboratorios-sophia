#!/bin/bash

echo "🔍 Verificando Cluster HDFS con 2 DataNodes"
echo "==========================================="

echo ""
echo "📊 Estado de contenedores:"
docker-compose ps

echo ""
echo "⏳ Esperando que los servicios estén listos..."
sleep 30

echo ""
echo "📈 Reporte detallado de HDFS:"
docker exec namenode hdfs dfsadmin -report

echo ""
echo "📋 Resumen de DataNodes:"
docker exec namenode hdfs dfsadmin -report | grep -A 10 "Live datanodes"

echo ""
echo "🌐 Interfaces web disponibles:"
echo "   - Hadoop UI: http://localhost:9870"
echo "   - Spark Master: http://localhost:8080"
echo "   - Jupyter Lab: http://localhost:8888"

echo ""
echo "🧪 Prueba rápida de HDFS:"
echo "   Creando archivo de prueba..."
echo "Hola desde cluster con 2 DataNodes!" | docker exec -i namenode hdfs dfs -put - /test-2-nodes.txt 2>/dev/null

if docker exec namenode hdfs dfs -cat /test-2-nodes.txt >/dev/null 2>&1; then
    echo "   ✅ Archivo creado y leído correctamente"
    echo "   📄 Contenido: $(docker exec namenode hdfs dfs -cat /test-2-nodes.txt)"
else
    echo "   ⏳ HDFS aún no está completamente listo"
fi

echo ""
echo "✅ Verificación completada!"