#!/bin/bash

echo "🔧 Solucionador de Problemas - Big Data Cluster"
echo "==============================================="

# Función para corregir endings de línea
fix_line_endings() {
    echo "🔄 Corrigiendo endings de línea en scripts..."
    
    if command -v dos2unix >/dev/null 2>&1; then
        find scripts/ -name "*.sh" -exec dos2unix {} \;
        echo "✅ Usamos dos2unix"
    else
        find scripts/ -name "*.sh" -exec sed -i 's/\r$//' {} \;
        echo "✅ Usamos sed"
    fi
}

# Función para dar permisos
fix_permissions() {
    echo "🔐 Corrigiendo permisos de scripts..."
    chmod +x scripts/*.sh
    chmod +x setup.sh
    chmod +x test-cluster.sh
    echo "✅ Permisos corregidos"
}

# Función para limpiar y reconstruir
rebuild_clean() {
    echo "🧹 Limpiando y reconstruyendo..."
    docker-compose down --volumes --remove-orphans 2>/dev/null || true
    docker system prune -f
    docker-compose build --no-cache
    echo "✅ Reconstrucción completada"
}

echo ""
echo "🔍 Detectando problema..."

# Verificar si hay archivos con CRLF
if grep -l $'\r' scripts/*.sh >/dev/null 2>&1; then
    echo "❌ Encontrados endings de línea Windows (CRLF)"
    fix_line_endings
    fix_permissions
    echo "✅ Problema de endings corregido"
else
    echo "✅ Endings de línea OK"
fi

# Verificar permisos
if [ ! -x "scripts/start-services.sh" ]; then
    echo "❌ Permisos de ejecución faltantes"
    fix_permissions
    echo "✅ Permisos corregidos"
else
    echo "✅ Permisos OK"
fi

echo ""
echo "🚀 ¿Quieres reconstruir todo limpio? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    rebuild_clean
fi

echo ""
echo "✅ ¡Problemas solucionados!"
echo "🎯 Ahora ejecuta: docker-compose up -d"