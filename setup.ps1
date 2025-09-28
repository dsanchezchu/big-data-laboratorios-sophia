# Setup Automático - Big Data Laboratorios Sophia (Windows PowerShell)
# ================================================================

Write-Host "🚀 Setup Automático - Big Data Laboratorios Sophia" -ForegroundColor Blue
Write-Host "=================================================" -ForegroundColor Blue
Write-Host ""

function Write-Info($message) {
    Write-Host "ℹ️  $message" -ForegroundColor Cyan
}

function Write-Success($message) {
    Write-Host "✅ $message" -ForegroundColor Green
}

function Write-Warning($message) {
    Write-Host "⚠️  $message" -ForegroundColor Yellow
}

function Write-Error($message) {
    Write-Host "❌ $message" -ForegroundColor Red
}

# Verificar Docker
Write-Info "Verificando Docker..."
try {
    $dockerVersion = docker --version
    Write-Success "Docker está instalado: $dockerVersion"
} catch {
    Write-Error "Docker no está instalado. Por favor instala Docker Desktop."
    Write-Host "Descarga desde: https://www.docker.com/products/docker-desktop/"
    exit 1
}

# Verificar Docker Compose
Write-Info "Verificando Docker Compose..."
try {
    $composeVersion = docker-compose --version
    Write-Success "Docker Compose está instalado: $composeVersion"
} catch {
    Write-Error "Docker Compose no está instalado."
    exit 1
}

# Verificar que Docker esté ejecutándose
Write-Info "Verificando que Docker esté ejecutándose..."
try {
    docker ps | Out-Null
    Write-Success "Docker está ejecutándose correctamente"
} catch {
    Write-Error "Docker no está ejecutándose. Por favor inicia Docker Desktop."
    exit 1
}

# Limpiar instalaciones previas
Write-Info "Limpiando instalaciones previas..."
try {
    docker-compose down --volumes 2>$null
} catch {
    # Ignorar errores si no hay nada que limpiar
}
Write-Success "Limpieza completada"

# Construir imágenes
Write-Info "Construyendo imágenes Docker (esto puede tardar 5-10 minutos la primera vez)..."
if ((docker-compose build --no-cache) -and ($LASTEXITCODE -eq 0)) {
    Write-Success "Imágenes construidas exitosamente"
} else {
    Write-Error "Error al construir las imágenes"
    exit 1
}

# Iniciar servicios
Write-Info "Iniciando servicios del cluster..."
if ((docker-compose up -d) -and ($LASTEXITCODE -eq 0)) {
    Write-Success "Cluster iniciado exitosamente"
} else {
    Write-Error "Error al iniciar el cluster"
    exit 1
}

# Esperar a que los servicios estén listos
Write-Info "Esperando a que los servicios estén listos (60 segundos)..."
Start-Sleep -Seconds 60

# Verificar servicios
Write-Info "Verificando estado de los servicios..."
docker-compose ps

Write-Host ""
Write-Success "🎉 ¡Cluster Big Data listo!"
Write-Host ""
Write-Host "📍 URLs disponibles:" -ForegroundColor Yellow
Write-Host "   🌐 Hadoop HDFS UI: http://localhost:9870"
Write-Host "   ⚡ Spark Master UI: http://localhost:8080"
Write-Host "   🔧 Spark Worker UI: http://localhost:8081"  
Write-Host "   📓 Jupyter Lab: http://localhost:8888"
Write-Host ""
Write-Info "Para obtener el token de Jupyter, ejecuta:"
Write-Host '   docker-compose logs jupyter | Select-String -Pattern "token|http://"'
Write-Host ""
Write-Success "¡Ahora puedes empezar a trabajar con Big Data!"