import subprocess
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response

app = FastAPI()

STREAMLIT_URL = "http://127.0.0.1:8501"

# Serve assetlinks.json correctly
@app.api_route("/.well-known/assetlinks.json", methods=["GET", "HEAD"])
def assetlinks():
    return FileResponse(
        ".well-known/assetlinks.json",
        media_type="application/json"
    )

# Proxy all other requests to Streamlit
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_to_streamlit(request: Request, path: str):
    url = f"{STREAMLIT_URL}/{path}"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.request(
            request.method,
            url,
            headers=request.headers.raw,
            content=await request.body()
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
        media_type=resp.headers.get("content-type")
    )

# Start Streamlit in background
@app.on_event("startup")
def start_streamlit():
    subprocess.Popen([
        "streamlit",
        "run",
        "streamlit_projectk_app.py",
        "--server.port=8501",
        "--server.address=127.0.0.1",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false"
    ])
