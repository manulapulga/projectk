#!/bin/bash
set -e

# Start Streamlit on local port 8501 (background)
streamlit run streamlit_app.py --server.port 8501 --server.address 127.0.0.1 &
STREAMLIT_PID=$!

# Wait until Streamlit is up (tries up to 60 seconds)
echo "Waiting for Streamlit to start on http://127.0.0.1:8501 ..."
for i in $(seq 1 60); do
  if curl --silent --fail http://127.0.0.1:8501 >/dev/null 2>&1; then
    echo "Streamlit is up."
    break
  fi
  sleep 1
done

# If Streamlit never started, print message and exit
if ! curl --silent --fail http://127.0.0.1:8501 >/dev/null 2>&1; then
  echo "Streamlit failed to start. Check logs."
  kill $STREAMLIT_PID || true
  exit 1
fi

# Start FastAPI (uvicorn) on the port Railway provides ($PORT)
# This will serve assetlinks.json and proxy all other requests to streamlit
exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
