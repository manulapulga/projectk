#!/bin/bash

# Force Streamlit to use Railway PORT
export STREAMLIT_SERVER_PORT=$PORT
export STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Start FastAPI in background
uvicorn fastapi_server:app --host 0.0.0.0 --port 9000 &

# Start Streamlit frontend
streamlit run streamlit_projectk_app.py
