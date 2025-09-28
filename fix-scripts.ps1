# Solucionador de Problemas - Big Data Cluster (Windows)
# ====================================================

Write-Host "🔧 Solucionador de Problemas - Big Data Cluster" -ForegroundColor Blue
Write-Host "===============================================" -ForegroundColor Blue

function Fix-LineEndings {
    Write-Host "🔄 Corrigiendo endings de línea en scripts..." -ForegroundColor Yellow
    
    Get-ChildItem -Path "scripts\" -Filter "*.sh" | ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        $content = $content -replace "`r`n", "`n"
        $content = $content -replace "`r", "`n"
        [System.IO.File]::WriteAllText($_.FullName, $content, [System.Text.Encoding]::UTF8)
        Write-Host "   ✅ Corregido: $($_.Name)" -ForegroundColor Green
    }
    
    # También corregir otros scripts
    @("setup.sh", "test-cluster.sh", "fix-scripts.sh") | ForEach-Object {
        if (Test-Path $_) {
            $content = Get-Content $_ -Raw
            $content = $content -replace "`r`n", "`n"
            $content = $content -replace "`r", "`n"
            [System.IO.File]::WriteAllText($_, $content, [System.Text.Encoding]::UTF8)
            Write-Host "   ✅ Corregido: $_" -ForegroundColor Green
        }
    }
}

function Rebuild-Clean {
    Write-Host "🧹 Limpiando y reconstruyendo..." -ForegroundColor Yellow
    
    try {
        docker-compose down --volumes --remove-orphans 2>$null
    } catch {
        # Ignorar errores si no hay contenedores
    }
    
    docker system prune -f
    docker-compose build --no-cache
    Write-Host "✅ Reconstrucción completada" -ForegroundColor Green
}

Write-Host ""
Write-Host "🔍 Detectando y solucionando problemas..." -ForegroundColor Cyan

# Siempre corregir endings y permisos
Fix-LineEndings

Write-Host ""
Write-Host "🚀 ¿Quieres reconstruir todo limpio? (y/n): " -ForegroundColor Yellow -NoNewline
$response = Read-Host

if ($response -match "^[Yy]$") {
    Rebuild-Clean
}

Write-Host ""
Write-Host "✅ ¡Problemas solucionados!" -ForegroundColor Green
Write-Host "🎯 Ahora ejecuta: docker-compose up -d" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 Si persiste el problema, ejecuta:" -ForegroundColor Yellow
Write-Host "   docker-compose build --no-cache" -ForegroundColor White
Write-Host "   docker-compose up -d" -ForegroundColor White