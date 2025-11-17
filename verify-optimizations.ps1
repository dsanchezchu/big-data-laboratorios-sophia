# Script de Verificación del Cluster Hadoop + Spark + YARN

Write-Host "🔍 Verificación del Cluster Big Data" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$global:passedTests = 0
$global:failedTests = 0

# Función para verificar un test
function Test-Component {
    param(
        [string]$Name,
        [scriptblock]$TestScript
    )
    
    Write-Host "🔹 $Name... " -NoNewline -ForegroundColor Yellow
    try {
        $result = & $TestScript
        if ($result) {
            Write-Host "✅" -ForegroundColor Green
            $global:passedTests++
            return $true
        }
        else {
            Write-Host "❌" -ForegroundColor Red
            $global:failedTests++
            return $false
        }
    }
    catch {
        Write-Host "❌ (Error: $_)" -ForegroundColor Red
        $global:failedTests++
        return $false
    }
}

# 1. Verificar Docker
Write-Host "1️⃣  Verificando Docker" -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Gray

Test-Component "Docker está corriendo" {
    try {
        docker ps | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

Write-Host ""

# 2. Verificar contenedores
Write-Host "2️⃣  Verificando Contenedores" -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Gray

$containers = @(
    "namenode",
    "datanode1", 
    "datanode2",
    "spark-master",
    "spark-worker",
    "jupyter",
    "nifi"
)

foreach ($container in $containers) {
    Test-Component "Contenedor '$container' corriendo" {
        $running = docker ps --filter "name=^$container$" --format "{{.Names}}" 2>$null
        return ($running -eq $container)
    }
}

Write-Host ""

# 3. Verificar servicios HDFS
Write-Host "3️⃣  Verificando HDFS" -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Gray

Test-Component "HDFS NameNode accesible" {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9870" -TimeoutSec 5 -UseBasicParsing
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

Test-Component "HDFS filesystem operativo" {
    $result = docker exec namenode hdfs dfs -test -d / 2>&1
    return $LASTEXITCODE -eq 0
}

Test-Component "HDFS fuera de safe mode" {
    $result = docker exec namenode hdfs dfsadmin -safemode get 2>&1
    return $result -match "OFF"
}

Test-Component "DataNodes reportando" {
    $result = docker exec namenode hdfs dfsadmin -report 2>&1
    $liveNodes = ($result | Select-String "Live datanodes").ToString()
    return $liveNodes -match "\(2\)"  # Esperamos 2 DataNodes
}

Write-Host ""

# 4. Verificar YARN
Write-Host "4️⃣  Verificando YARN" -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Gray

Test-Component "YARN ResourceManager accesible" {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8088" -TimeoutSec 5 -UseBasicParsing
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

Test-Component "YARN NodeManagers activos" {
    $result = docker exec namenode yarn node -list 2>&1
    # Debe haber al menos un NodeManager activo
    return ($result -match "RUNNING" -or $result -match "datanode")
}

Write-Host ""

# 5. Verificar Spark
Write-Host "5️⃣  Verificando Spark" -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Gray

Test-Component "Spark Master accesible" {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080" -TimeoutSec 5 -UseBasicParsing
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

Test-Component "Spark Worker conectado" {
    # Verificar que el worker esté conectado al master
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8081" -TimeoutSec 5 -UseBasicParsing
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

Write-Host ""

# 6. Verificar optimización de JARs
Write-Host "6️⃣  Verificando Optimización Spark" -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Gray

Test-Component "Directorio /spark-jars existe en HDFS" {
    $result = docker exec namenode hdfs dfs -test -d /spark-jars 2>&1
    return $LASTEXITCODE -eq 0
}

$jarFileExists = Test-Component "Archivo spark-libs.tgz existe" {
    $result = docker exec namenode hdfs dfs -test -e /spark-jars/spark-libs.tgz 2>&1
    return $LASTEXITCODE -eq 0
}

if ($jarFileExists) {
    Write-Host "   📊 Tamaño: " -NoNewline -ForegroundColor Cyan
    $size = docker exec namenode hdfs dfs -ls -h /spark-jars/spark-libs.tgz 2>$null | Select-String -Pattern "\d+\.?\d*[KMG]"
    if ($size) {
        Write-Host $size.Matches[0].Value -ForegroundColor White
    }
}

Test-Component "spark-defaults.conf configurado" {
    $config = docker exec jupyter cat /opt/spark/conf/spark-defaults.conf 2>&1
    return $config -match "spark.yarn.archive"
}

Write-Host ""

# 7. Verificar Jupyter
Write-Host "7️⃣  Verificando Jupyter" -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Gray

Test-Component "JupyterLab accesible" {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8888" -TimeoutSec 5 -UseBasicParsing
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

Test-Component "PySpark instalado" {
    $result = docker exec jupyter python -c "import pyspark; print(pyspark.__version__)" 2>&1
    return $LASTEXITCODE -eq 0
}

Write-Host ""

# 8. Verificar NiFi
Write-Host "8️⃣  Verificando NiFi" -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Gray

Test-Component "NiFi UI accesible" {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8082/nifi" -TimeoutSec 5 -UseBasicParsing
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

Write-Host ""

# 9. Verificar directorios HDFS
Write-Host "9️⃣  Verificando Estructura HDFS" -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Gray

$hdfsDirectories = @(
    "/user/hadoop",
    "/user/nifi",
    "/tmp",
    "/spark-logs"
)

foreach ($dir in $hdfsDirectories) {
    Test-Component "Directorio $dir existe" {
        $result = docker exec namenode hdfs dfs -test -d $dir 2>&1
        return $LASTEXITCODE -eq 0
    }
}

Write-Host ""

# 10. Test de escritura/lectura en HDFS
Write-Host "🔟 Test de Lectura/Escritura HDFS" -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Gray

Test-Component "Escribir archivo de prueba" {
    $result = docker exec namenode bash -c "echo 'test' | hdfs dfs -put -f - /tmp/test-verify.txt" 2>&1
    return $LASTEXITCODE -eq 0
}

Test-Component "Leer archivo de prueba" {
    $result = docker exec namenode hdfs dfs -cat /tmp/test-verify.txt 2>&1
    return $result -eq "test"
}

Test-Component "Eliminar archivo de prueba" {
    $result = docker exec namenode hdfs dfs -rm /tmp/test-verify.txt 2>&1
    return $LASTEXITCODE -eq 0
}

Write-Host ""

# Resumen
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "📊 Resumen de Verificación" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Tests pasados:  $global:passedTests" -ForegroundColor Green
Write-Host "❌ Tests fallidos: $global:failedTests" -ForegroundColor Red
Write-Host ""

$totalTests = $global:passedTests + $global:failedTests
$successRate = [math]::Round(($global:passedTests / $totalTests) * 100, 1)

Write-Host "Tasa de éxito: $successRate%" -ForegroundColor $(if ($successRate -ge 90) { "Green" } elseif ($successRate -ge 70) { "Yellow" } else { "Red" })
Write-Host ""

if ($global:failedTests -eq 0) {
    Write-Host "🎉 ¡Todos los tests pasaron! El cluster está completamente operativo." -ForegroundColor Green
}
elseif ($successRate -ge 80) {
    Write-Host "⚠️  La mayoría de los componentes funcionan, pero hay algunos problemas." -ForegroundColor Yellow
    Write-Host "   Revisa los tests fallidos arriba." -ForegroundColor Yellow
}
else {
    Write-Host "❌ Hay problemas significativos con el cluster." -ForegroundColor Red
    Write-Host "   Revisa los logs: docker compose logs" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🔗 URLs de acceso:" -ForegroundColor Cyan
Write-Host "   HDFS NameNode:    http://localhost:9870" -ForegroundColor White
Write-Host "   YARN ResourceMgr: http://localhost:8088" -ForegroundColor White
Write-Host "   Spark Master:     http://localhost:8080" -ForegroundColor White
Write-Host "   JupyterLab:       http://localhost:8888" -ForegroundColor White
Write-Host "   NiFi:             http://localhost:8082/nifi" -ForegroundColor White
Write-Host ""

# Código de salida
if ($global:failedTests -eq 0) {
    exit 0
}
else {
    exit 1
}
