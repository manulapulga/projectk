import subprocess
from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI()

# Serve assetlinks.json correctly for TWA
@app.get("/.well-known/assetlinks.json")
def assetlinks():
    return FileResponse(
        ".well-known/assetlinks.json",
        media_type="application/json"
    )

# Start Streamlit in background
@app.on_event("startup")
def start_streamlit():
    subprocess.Popen([
        "streamlit",
        "run",
        "streamlit_projectk_app.py",
        "--server.port=8501",
        "--server.address=0.0.0.0"
    ])
