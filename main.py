# main.py
import os
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
import httpx
import asyncio

app = FastAPI()

# Path to your assetlinks.json inside the repo
ASSETLINKS_PATH = "public/.well-known/assetlinks.json"

# Streamlit runs locally on this internal port (we start it in start.sh)
STREAMLIT_HOST = "127.0.0.1"
STREAMLIT_PORT = 8501
STREAMLIT_BASE = f"http://{STREAMLIT_HOST}:{STREAMLIT_PORT}"


@app.get("/.well-known/assetlinks.json")
async def assetlinks():
    if os.path.exists(ASSETLINKS_PATH):
        return FileResponse(ASSETLINKS_PATH, media_type="application/json")
    return Response(status_code=404, content='{"error":"assetlinks.json not found"}', media_type="application/json")


# Generic proxy for everything else -> forward to streamlit
@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy(full_path: str, request: Request):
    # Build target URL
    query = request.url.query
    target_url = f"{STREAMLIT_BASE}/{full_path}"
    if query:
        target_url = target_url + "?" + query

    # Prepare headers without host (let upstream set host)
    headers = dict(request.headers)
    headers.pop("host", None)
    # Also remove hop-by-hop headers if present
    for h in ["connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"]:
        headers.pop(h, None)

    # Body
    body = await request.body()

    # Async forward using httpx
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            upstream = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                stream=True,
            )
        except httpx.RequestError as e:
            return Response(status_code=502, content=f"Upstream connection error: {e}")

        # Filter response headers (remove hop-by-hop)
        response_headers = [(k, v) for k, v in upstream.headers.items()
                            if k.lower() not in ("content-encoding", "transfer-encoding", "connection")]

        # Stream response body back
        return StreamingResponse(upstream.aiter_raw(), status_code=upstream.status_code, headers=dict(response_headers))
