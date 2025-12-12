from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn
import os

app = FastAPI()

STATIC_FILE = "public/.well-known/assetlinks.json"

@app.get("/.well-known/assetlinks.json")
def serve_assetlinks():
    if os.path.exists(STATIC_FILE):
        return FileResponse(STATIC_FILE, media_type="application/json")
    return {"error": "assetlinks.json not found"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
