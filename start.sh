#!/bin/bash

# Start FastAPI static server in background
python serve_static.py &

# Start Streamlit app (foreground)
streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0
