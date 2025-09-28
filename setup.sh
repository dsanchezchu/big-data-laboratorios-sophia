#!/bin/bash

echo "🚀 Setup Automático - Big Data Laboratorios Sophia"
echo "================================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir con colores
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar Docker
print_info "Verificando Docker..."
if command -v docker &> /dev/null; then
    print_success "Docker está instalado: $(docker --version)"
else
    print_error "Docker no está instalado. Por favor instala Docker Desktop."
    echo "Descarga desde: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# Verificar Docker Compose
print_info "Verificando Docker Compose..."
if command -v docker-compose &> /dev/null; then
    print_success "Docker Compose está instalado: $(docker-compose --version)"
else
    print_error "Docker Compose no está instalado."
    exit 1
fi

# Verificar que Docker esté ejecutándose
print_info "Verificando que Docker esté ejecutándose..."
if docker ps &> /dev/null; then
    print_success "Docker está ejecutándose correctamente"
else
    print_error "Docker no está ejecutándose. Por favor inicia Docker Desktop."
    exit 1
fi

# Limpiar instalaciones previas
print_info "Limpiando instalaciones previas..."
docker-compose down --volumes 2>/dev/null || true
print_success "Limpieza completada"

# Construir imágenes
print_info "Construyendo imágenes Docker (esto puede tardar 5-10 minutos la primera vez)..."
if docker-compose build --no-cache; then
    print_success "Imágenes construidas exitosamente"
else
    print_error "Error al construir las imágenes"
    exit 1
fi

# Iniciar servicios
print_info "Iniciando servicios del cluster..."
if docker-compose up -d; then
    print_success "Cluster iniciado exitosamente"
else
    print_error "Error al iniciar el cluster"
    exit 1
fi

# Esperar a que los servicios estén listos
print_info "Esperando a que los servicios estén listos (60 segundos)..."
sleep 60

# Verificar servicios
print_info "Verificando estado de los servicios..."
docker-compose ps

echo ""
print_success "🎉 ¡Cluster Big Data listo!"
echo ""
echo "📍 URLs disponibles:"
echo "   🌐 Hadoop HDFS UI: http://localhost:9870"
echo "   ⚡ Spark Master UI: http://localhost:8080"  
echo "   🔧 Spark Worker UI: http://localhost:8081"
echo "   📓 Jupyter Lab: http://localhost:8888"
echo ""
print_info "Para obtener el token de Jupyter, ejecuta:"
echo "   docker-compose logs jupyter | grep -E '(token|http://)'"
echo ""
print_success "¡Ahora puedes empezar a trabajar con Big Data!"