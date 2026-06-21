"""
VoxSense — main.py
FastAPI application entry point.
Runs on http://localhost:8000
"""

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from routes.websocket_route import router as ws_router
from modules.memory import MemoryManager

# ─── Logging ──────────────────────────────────────────────────
log_dir = Path.home() / ".voxsense" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logger.add(
    log_dir / "app.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)

# ─── Lifespan ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VoxSense starting...")
    mem = MemoryManager()
    await mem.init_db()
    app.state.memory = mem
    logger.info("VoxSense ready.")
    yield
    logger.info("VoxSense shutting down.")

# ─── App ───────────────────────────────────────────────────────
app = FastAPI(
    title="VoxSense API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ────────────────────────────────────────────────────
app.include_router(ws_router)

# ─── Status ────────────────────────────────────────────────────
@app.get("/status")
async def get_status():
    nvda_connected = False
    try:
        import nvda_controller_client as nvda  # type: ignore
        nvda_connected = True
    except Exception:
        pass
    return {
        "backend_ready": True,
        "nvda_connected": nvda_connected,
        "version": "1.0.0",
    }

# ─── Frontend ──────────────────────────────────────────────────
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"

@app.get("/")
async def serve_index():
    index = FRONTEND / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"error": "Frontend not found."}

if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")