#!/bin/bash
cd /home/jupyter/frontend

# Instalar dependencias si no están instaladas
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Instalando dependencias..."
    pip3 install --no-cache-dir -q -r requirements.txt
else
    source venv/bin/activate
fi

echo "Iniciando Streamlit..."
streamlit run /home/jupyter/frontend/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
