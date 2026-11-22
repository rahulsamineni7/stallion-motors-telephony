"""
Stallion Motors Telephony Server.
FastAPI Application integrating Kros AI Telephony CPaaS,
Sarvam AI Speech Infrastructure, and the Dealership Voice Concierge.
Supports local execution and Vercel Serverless deployment.
"""

import os
import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from routes.kros_webhooks import kros_router
from routes.simulation_api import sim_router
from config import dealership_config, telephony_config

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("server")

app = FastAPI(
    title="Stallion Motors Dealership - Kros AI Voice Telephony",
    description="Automated Inbound Routing, Multi-Line Hunt Retries, and Telephony Handover",
    version="1.0.0"
)

# Vercel Path Normalization Middleware
@app.middleware("http")
async def vercel_path_rewrite_middleware(request: Request, call_next):
    matched_path = request.headers.get("x-matched-path")
    if matched_path and matched_path != "/api/index.py":
        request.scope["path"] = matched_path
    else:
        path = request.scope.get("path", "")
        # If Vercel rewrites to /api/index.py/something or /api/index.py
        if path.startswith("/api/index.py"):
            new_path = path[len("/api/index.py"):]
            request.scope["path"] = new_path if new_path else "/"
    return await call_next(request)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers (mounted both at root and with /api and /kros prefixes)
app.include_router(kros_router)
app.include_router(kros_router, prefix="/kros")
app.include_router(sim_router)
app.include_router(sim_router, prefix="/api")

# Mount Static Files for Demo Dashboard
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
if os.path.exists(PUBLIC_DIR):
    app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")

PUBLIC_AUDIO_DIR = os.path.join(PUBLIC_DIR, "audio")
if os.path.exists(PUBLIC_AUDIO_DIR):
    app.mount("/audio", StaticFiles(directory=PUBLIC_AUDIO_DIR), name="audio")

@app.get("/audio_assets.js")
@app.get("/static/audio_assets.js")
@app.get("/public/audio_assets.js")
@app.get("/api/audio_assets.js")
async def serve_audio_assets():
    """Serves preloaded Nigerian Fish Audio base64 assets as JS for zero-network playback."""
    for folder in [
        PUBLIC_DIR,
        STATIC_DIR,
        os.path.dirname(__file__)
    ]:
        js_path = os.path.join(folder, "audio_assets.js")
        if os.path.exists(js_path):
            return FileResponse(js_path, media_type="application/javascript")
    return HTMLResponse(content="// audio_assets not found", media_type="application/javascript")

@app.get("/audio/{filename}")
@app.get("/public/audio/{filename}")
@app.get("/static/audio/{filename}")
async def serve_audio_file(filename: str):
    """Direct audio file server ensuring MP3s are always delivered with 200/206 status."""
    for folder in [
        os.path.join(PUBLIC_DIR, "audio"),
        os.path.join(STATIC_DIR, "audio"),
    ]:
        fpath = os.path.join(folder, filename)
        if os.path.exists(fpath):
            return FileResponse(fpath, media_type="audio/mpeg")
    return FileResponse(os.path.join(PUBLIC_DIR, "audio", "greeting.mp3"), media_type="audio/mpeg")

@app.get("/")
@app.get("/api")
@app.get("/api/index.py")
async def root_index():
    """Serves the interactive web-based telephony dashboard."""
    for folder in [PUBLIC_DIR, STATIC_DIR]:
        index_path = os.path.join(folder, "index.html")
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
            except Exception:
                return FileResponse(index_path)
    return {
        "dealership": dealership_config.dealership_name,
        "status": "online",
        "telephony_provider": telephony_config.provider,
        "kros_virtual_number": telephony_config.kros_virtual_number
    }

@app.get("/health")
@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "dealership": dealership_config.dealership_name,
        "virtual_number": telephony_config.kros_virtual_number
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8028, reload=True)
