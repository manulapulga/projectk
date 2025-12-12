from fastapi import FastAPI
from fastapi.responses import FileResponse
import os

app = FastAPI()

FILE_PATH = "public/.well-known/assetlinks.json"

@app.get("/.well-known/assetlinks.json")
def serve_assetlinks():
    if os.path.exists(FILE_PATH):
        return FileResponse(FILE_PATH, media_type="application/json")
    return {"error": "assetlinks.json not found"}
