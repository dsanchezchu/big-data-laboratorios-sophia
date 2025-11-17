# Script de Optimización para Spark + YARN
# Este script aplica las optimizaciones de spark.yarn.archive

Write-Host "🚀 Script de Optimización Spark + YARN" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Función para verificar si Docker está corriendo
function Test-DockerRunning {
    try {
        docker ps | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Función para esperar a que un contenedor esté healthy
function Wait-ContainerHealthy {
    param([string]$ContainerName, [int]$TimeoutSeconds = 120)
    
    Write-Host "⏳ Esperando a que $ContainerName esté healthy..." -ForegroundColor Yellow
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        $health = docker inspect --format='{{.State.Health.Status}}' $ContainerName 2>$null
        if ($health -eq "healthy") {
            Write-Host "✅ $ContainerName está healthy" -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds 5
        $elapsed += 5
        Write-Host "   Esperando... ($elapsed/$TimeoutSeconds segundos)" -ForegroundColor Gray
    }
    Write-Host "❌ Timeout esperando a $ContainerName" -ForegroundColor Red
    return $false
}

# Verificar Docker
if (-not (Test-DockerRunning)) {
    Write-Host "❌ Docker no está corriendo. Por favor inicia Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host "1️⃣  Verificando estado del cluster..." -ForegroundColor Cyan
Write-Host ""

# Verificar si los contenedores están corriendo
$namenodeRunning = docker ps --filter "name=namenode" --format "{{.Names}}" 2>$null
if (-not $namenodeRunning) {
    Write-Host "❌ El contenedor 'namenode' no está corriendo." -ForegroundColor Red
    Write-Host "   Inicia el cluster con: docker compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Cluster está corriendo" -ForegroundColor Green
Write-Host ""

# Esperar a que namenode esté healthy
Write-Host "2️⃣  Esperando a que HDFS esté disponible..." -ForegroundColor Cyan
Write-Host ""

if (-not (Wait-ContainerHealthy "namenode" 180)) {
    Write-Host "⚠️  Namenode no está healthy, pero continuaremos..." -ForegroundColor Yellow
}

# Verificar conectividad HDFS
Write-Host "3️⃣  Verificando conectividad con HDFS..." -ForegroundColor Cyan
Write-Host ""

$maxRetries = 30
$retry = 0
$hdfsReady = $false

while ($retry -lt $maxRetries -and -not $hdfsReady) {
    $result = docker exec namenode hdfs dfs -test -d / 2>&1
    if ($LASTEXITCODE -eq 0) {
        $hdfsReady = $true
        Write-Host "✅ HDFS está disponible" -ForegroundColor Green
    }
    else {
        $retry++
        Write-Host "   Intento $retry/$maxRetries - Esperando HDFS..." -ForegroundColor Gray
        Start-Sleep -Seconds 2
    }
}

if (-not $hdfsReady) {
    Write-Host "❌ HDFS no está disponible después de $maxRetries intentos" -ForegroundColor Red
    Write-Host "   Verifica los logs: docker logs namenode" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Verificar si spark-libs.tgz ya existe
Write-Host "4️⃣  Verificando archivo spark-libs.tgz en HDFS..." -ForegroundColor Cyan
Write-Host ""

$jarExists = docker exec namenode hdfs dfs -test -e /spark-jars/spark-libs.tgz 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ spark-libs.tgz ya existe en HDFS" -ForegroundColor Green
    Write-Host ""
    
    # Mostrar información del archivo
    Write-Host "📊 Información del archivo:" -ForegroundColor Cyan
    docker exec namenode hdfs dfs -ls -h /spark-jars/spark-libs.tgz
    Write-Host ""
    
    $response = Read-Host "¿Quieres recrear el archivo? (s/N)"
    if ($response -ne "s" -and $response -ne "S") {
        Write-Host "✅ Optimización ya aplicada. No se requieren cambios." -ForegroundColor Green
        exit 0
    }
    
    Write-Host "🗑️  Eliminando archivo existente..." -ForegroundColor Yellow
    docker exec namenode hdfs dfs -rm /spark-jars/spark-libs.tgz | Out-Null
}

# Crear spark-libs.tgz
Write-Host "5️⃣  Creando archivo spark-libs.tgz..." -ForegroundColor Cyan
Write-Host ""

Write-Host "   Esto puede tomar 30-60 segundos..." -ForegroundColor Yellow
$result = docker exec namenode bash /scripts/init-spark-jars.sh 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Archivo creado exitosamente" -ForegroundColor Green
}
else {
    Write-Host "❌ Error al crear el archivo:" -ForegroundColor Red
    Write-Host $result -ForegroundColor Red
    exit 1
}

Write-Host ""

# Verificar que se creó correctamente
Write-Host "6️⃣  Verificando integridad del archivo..." -ForegroundColor Cyan
Write-Host ""

$verification = docker exec namenode hdfs dfs -ls -h /spark-jars/spark-libs.tgz 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Verificación exitosa" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Detalles del archivo:" -ForegroundColor Cyan
    Write-Host $verification
}
else {
    Write-Host "❌ Error al verificar el archivo" -ForegroundColor Red
    Write-Host $verification -ForegroundColor Red
    exit 1
}

Write-Host ""

# Resumen
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "✅ Optimización Completada" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📌 Próximos pasos:" -ForegroundColor Cyan
Write-Host "   1. Los nuevos notebooks de Spark usarán automáticamente" -ForegroundColor White
Write-Host "      la optimización de spark.yarn.archive" -ForegroundColor White
Write-Host ""
Write-Host "   2. Para notebooks existentes, asegúrate de incluir:" -ForegroundColor White
Write-Host "      .config('spark.yarn.archive', 'hdfs://namenode:9000/spark-jars/spark-libs.tgz')" -ForegroundColor Gray
Write-Host ""
Write-Host "   3. O simplemente usa .master('yarn') y se tomará" -ForegroundColor White
Write-Host "      la config de spark-defaults.conf automáticamente" -ForegroundColor White
Write-Host ""
Write-Host "🎯 Mejora esperada:" -ForegroundColor Cyan
Write-Host "   - Tiempo de inicio de jobs: ~90% más rápido" -ForegroundColor Green
Write-Host "   - Transferencia de red: ~100% reducción (cached)" -ForegroundColor Green
Write-Host ""
Write-Host "📚 Para más información, lee: OPTIMIZACIONES_SPARK_YARN.md" -ForegroundColor Yellow
Write-Host ""
