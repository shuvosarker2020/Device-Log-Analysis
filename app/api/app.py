import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.config import BASE_DIR, cfg
from app.database.db import init_db
from app.core.syslog_server import syslog_server
from app.core.queue_worker import queue_worker, register_ws_broadcaster
from app.api.routes import router as api_router
from app.api.websocket import ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("NetLogIQ.App")

# Background worker task reference
worker_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task
    logger.info("Initializing NetLogIQ Syslog Analyzer System...")

    # 1. Initialize DB tables
    init_db()

    # 2. Hook WebSocket broadcaster to queue worker
    register_ws_broadcaster(ws_manager.broadcast)

    # 3. Start Queue Worker
    worker_task = asyncio.create_task(queue_worker())

    # 4. Start Syslog UDP/TCP Server
    await syslog_server.start()

    logger.info("NetLogIQ is ready and accepting syslogs.")
    yield

    # Teardown
    logger.info("Shutting down NetLogIQ...")
    await syslog_server.stop()
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    logger.info("Shutdown complete.")

app = FastAPI(
    title="NetLogIQ - Multi-Vendor Device Syslog Analyzer",
    description="Next-Gen Syslog Ingestion, Multi-Vendor Parser, Optimization Analytics, and Real-Time Alerting",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API routes
app.include_router(api_router)

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "title": "NetLogIQ - Network Device Syslog Analyzer",
        "udp_port": cfg.get("server", "syslog_udp_port", default=1514),
        "tcp_port": cfg.get("server", "syslog_tcp_port", default=1514)
    })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open and receive any ping/command from client
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WS exception: {e}")
        ws_manager.disconnect(websocket)
