import asyncio
import logging
from typing import Tuple, Optional
from app.core.models import NormalizedLog, AlertEvent
from app.parsers.engine import parser_engine
from app.analyzer.engine import analyzer_engine
from app.database.repository import repository
from app.notifiers.manager import notification_manager

logger = logging.getLogger("NetLogIQ.QueueWorker")

# In-memory queue for decoupling network receiver from DB and notifications
log_queue: asyncio.Queue = asyncio.Queue(maxsize=100000)

# Callback hook for WebSocket broadcasting
_ws_broadcaster = None

def register_ws_broadcaster(broadcaster_func):
    global _ws_broadcaster
    _ws_broadcaster = broadcaster_func

async def broadcast_ws(event_type: str, data: dict):
    if _ws_broadcaster:
        try:
            await _ws_broadcaster(event_type, data)
        except Exception as e:
            logger.debug(f"WS broadcast error: {e}")

async def process_log_pipeline(raw_message: str, source_ip: str) -> Tuple[NormalizedLog, Optional[AlertEvent]]:
    """
    Core pipeline: Parse -> Analyze -> Save to DB -> Notify -> Stream to UI
    """
    # 1. Parse into NormalizedLog
    normalized = parser_engine.parse(raw_message, source_ip)

    # 2. Analyze for alerts & categories
    normalized, alert = analyzer_engine.analyze(normalized)

    # 3. Save to database in thread pool to prevent blocking asyncio loop
    loop = asyncio.get_running_loop()
    log_id = await loop.run_in_executor(None, repository.save_log, normalized)
    normalized.id = log_id

    # 4. Handle Alert if triggered
    if alert:
        alert.log_id = log_id
        # Save alert
        alert_id = await loop.run_in_executor(None, repository.save_alert, alert, log_id)
        alert.id = alert_id

        # Dispatch external notifications asynchronously
        await loop.run_in_executor(None, notification_manager.dispatch, alert)

        # Broadcast alert to WebSocket clients (triggers UI modal / sound)
        await broadcast_ws("alert", alert.model_dump(mode="json"))

    # 5. Broadcast log to WebSocket live stream
    await broadcast_ws("log", normalized.model_dump(mode="json"))

    return normalized, alert

async def queue_worker():
    """Background worker continuously pulling from log_queue"""
    logger.info("[QueueWorker] Background processing worker started.")
    while True:
        try:
            raw_msg, source_ip = await log_queue.get()
            try:
                await process_log_pipeline(raw_msg, source_ip)
            except Exception as e:
                logger.error(f"[QueueWorker] Error processing log from {source_ip}: {e}")
            finally:
                log_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[QueueWorker] Worker loop error: {e}")
            await asyncio.sleep(0.1)
