#!/bin/bash

# Start FastAPI static server on port 9000
uvicorn serve_static:app --host 0.0.0.0 --port 9000 &

# Start Streamlit (foreground)
streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0