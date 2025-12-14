import subprocess
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse

app = FastAPI()

# Serve assetlinks.json correctly
@app.api_route("/.well-known/assetlinks.json", methods=["GET", "HEAD"])
def assetlinks():
    return FileResponse(
        ".well-known/assetlinks.json",
        media_type="application/json"
    )

# Redirect everything else to Streamlit
@app.api_route("/{path:path}", methods=["GET"])
def streamlit_proxy(request: Request, path: str):
    return RedirectResponse(
        url=f"http://127.0.0.1:8501/{path}"
    )

# Start Streamlit
@app.on_event("startup")
def start_streamlit():
    subprocess.Popen([
        "streamlit",
        "run",
        "streamlit_projectk_app.py",
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false"
    ])
