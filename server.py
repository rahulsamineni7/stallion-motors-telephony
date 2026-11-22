"""
Stallion Motors Telephony Server.
FastAPI Application integrating Kros AI Telephony CPaaS,
Sarvam AI Speech Infrastructure, and the Dealership Voice Concierge.
"""

import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(kros_router)
app.include_router(sim_router)

# Mount Static Files for Demo Dashboard
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root_index():
    """Serves the interactive web-based telephony dashboard."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "dealership": dealership_config.dealership_name,
        "status": "online",
        "telephony_provider": telephony_config.provider,
        "kros_virtual_number": telephony_config.kros_virtual_number
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "dealership": dealership_config.dealership_name,
        "virtual_number": telephony_config.kros_virtual_number
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8028, reload=True)
