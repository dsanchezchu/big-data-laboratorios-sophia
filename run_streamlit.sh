#!/bin/bash
cd /home/jupyter/frontend
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
/opt/python-env/bin/streamlit run /home/jupyter/frontend/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
