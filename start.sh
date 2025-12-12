#!/bin/bash

# Railway sets $PORT — pass it to Streamlit the correct way
export STREAMLIT_SERVER_PORT=$PORT
export STREAMLIT_SERVER_ADDRESS=0.0.0.0

echo "Starting Streamlit on port $STREAMLIT_SERVER_PORT ..."

streamlit run streamlit_projectk_app.py
