#!/bin/bash
cd /home/jupyter/frontend

# Verificar si hay cambios en requirements.txt
REQUIREMENTS_HASH=$(md5sum requirements.txt | awk '{print $1}')
HASH_FILE="venv/.requirements_hash"

if [ ! -d "venv" ] || [ ! -f "$HASH_FILE" ] || [ "$(cat $HASH_FILE)" != "$REQUIREMENTS_HASH" ]; then
    echo "Cambios detectados en requirements.txt. Recreando entorno virtual..."
    rm -rf venv
    python3 -m venv venv
    source venv/bin/activate
    pip3 install --no-cache-dir --upgrade pip
    pip3 install --no-cache-dir -r requirements.txt
    echo "$REQUIREMENTS_HASH" > "$HASH_FILE"
    echo "Dependencias instaladas."
else
    echo "Sin cambios en requirements.txt. Usando entorno existente..."
    source venv/bin/activate
fi

echo "Iniciando Streamlit..."
streamlit run /home/jupyter/frontend/streamlit_app_v2.py --server.address 0.0.0.0 --server.port 8501
