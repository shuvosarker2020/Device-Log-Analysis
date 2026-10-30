from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Body
from pydantic import BaseModel
from app.database.repository import repository
from app.core.queue_worker import process_log_pipeline
from app.simulator.log_generator import simulate_batch, send_udp_syslog
from app.config import cfg
from app.notifiers.manager import notification_manager

router = APIRouter(prefix="/api")

class IngestRequest(BaseModel):
    message: str
    source_ip: Optional[str] = "127.0.0.1"

class SimulateRequest(BaseModel):
    count: int = 10
    vendor: Optional[str] = None
    scenario: Optional[str] = None

class NotificationConfigRequest(BaseModel):
    telegram: Optional[Dict[str, Any]] = None
    slack: Optional[Dict[str, Any]] = None
    discord: Optional[Dict[str, Any]] = None
    ms_teams: Optional[Dict[str, Any]] = None
    generic_webhook: Optional[Dict[str, Any]] = None
    email: Optional[Dict[str, Any]] = None

# --- Analytics Endpoints ---

@router.get("/stats/summary")
def get_summary():
    return repository.get_summary_metrics()

@router.get("/stats/severity")
def get_severity_stats():
    return repository.get_severity_analytics()

@router.get("/stats/devices")
def get_device_stats(limit: int = 20):
    return repository.get_device_analytics(limit=limit)

@router.get("/stats/ips")
def get_ip_stats(limit: int = 20):
    return repository.get_ip_analytics(limit=limit)

@router.get("/stats/categories")
def get_category_stats():
    return repository.get_error_category_analytics()

@router.get("/stats/vendors")
def get_vendor_stats():
    return repository.get_vendor_analytics()

@router.get("/stats/timeline")
def get_timeline_stats():
    return repository.get_timeline_analytics()

# --- Logs Endpoints ---

@router.get("/logs")
def get_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    vendor: Optional[str] = None,
    severity: Optional[int] = None,
    source_ip: Optional[str] = None,
    hostname: Optional[str] = None,
    category: Optional[str] = None,
    is_alert_only: bool = False
):
    rows, total = repository.get_logs(
        limit=limit,
        offset=offset,
        search=search,
        vendor=vendor,
        severity=severity,
        source_ip=source_ip,
        hostname=hostname,
        category=category,
        is_alert_only=is_alert_only
    )
    return {"logs": rows, "total": total, "limit": limit, "offset": offset}

@router.post("/logs/ingest")
async def ingest_log(req: IngestRequest):
    log, alert = await process_log_pipeline(req.message, req.source_ip)
    return {
        "status": "success",
        "log": log.model_dump(mode="json"),
        "alert": alert.model_dump(mode="json") if alert else None
    }

# --- Alerts Endpoints ---

@router.get("/alerts")
def get_alerts(status: Optional[str] = None, limit: int = 50):
    return repository.get_alerts(status=status, limit=limit)

@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, user: str = "Operator"):
    success = repository.acknowledge_alert(alert_id, user=user)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "success", "alert_id": alert_id}

# --- Simulation & Testing Endpoints ---

@router.post("/simulate")
async def trigger_simulation(req: SimulateRequest):
    results = await simulate_batch(count=req.count, vendor=req.vendor, scenario=req.scenario)
    return {
        "status": "success",
        "generated_count": len(results),
        "results": results[:5]  # Sample first 5
    }

@router.post("/simulate/udp")
def trigger_udp_simulation(count: int = 5, vendor: Optional[str] = None):
    udp_port = cfg.get("server", "syslog_udp_port", default=1514)
    send_udp_syslog(target_host="127.0.0.1", port=udp_port, count=count, vendor=vendor)
    return {"status": "success", "sent_udp_count": count, "target_port": udp_port}

# --- Config & Notification Endpoints ---

@router.get("/config")
def get_configuration():
    # Return config with sensitive password masked
    c = dict(cfg.config)
    email_cfg = c.get("notifications", {}).get("email", {})
    if email_cfg and "password" in email_cfg and email_cfg["password"]:
        email_cfg = dict(email_cfg)
        email_cfg["password"] = "******"
        c["notifications"]["email"] = email_cfg
    return c

@router.post("/config/notifications")
def update_notifications(req: NotificationConfigRequest):
    update_data = {}
    if req.telegram is not None: update_data["telegram"] = req.telegram
    if req.slack is not None: update_data["slack"] = req.slack
    if req.discord is not None: update_data["discord"] = req.discord
    if req.ms_teams is not None: update_data["ms_teams"] = req.ms_teams
    if req.generic_webhook is not None: update_data["generic_webhook"] = req.generic_webhook
    if req.email is not None:
        # Don't overwrite password with mask
        if req.email.get("password") == "******":
            req.email["password"] = cfg.get("notifications", "email", "password", default="")
        update_data["email"] = req.email

    cfg.update_notifications(update_data)
    return {"status": "success", "message": "Notification configurations updated successfully"}

@router.post("/config/test-notification")
def test_notification(channel: str = Body(..., embed=True)):
    success = notification_manager.send_test_alert(channel)
    if success:
        return {"status": "success", "message": f"Test alert sent successfully via {channel}"}
    else:
        return {"status": "error", "message": f"Failed to send test alert via {channel}. Check logs and configuration."}
