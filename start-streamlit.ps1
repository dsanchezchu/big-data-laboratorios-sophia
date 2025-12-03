# Script para ejecutar Streamlit en el contenedor de Jupyter
# Copia el script al contenedor y lo ejecuta

Write-Host "Deteniendo procesos anteriores de Streamlit..." -ForegroundColor Yellow
docker exec jupyter pkill -f streamlit 2>$null
Start-Sleep -Seconds 2

Write-Host "Copiando script al contenedor..." -ForegroundColor Green
docker cp run_streamlit.sh jupyter:/home/jupyter/run_streamlit.sh

Write-Host "Configurando permisos..." -ForegroundColor Green
docker exec jupyter chmod +x /home/jupyter/run_streamlit.sh

Write-Host "Ejecutando Streamlit..." -ForegroundColor Green
docker exec -it jupyter bash /home/jupyter/run_streamlit.sh
