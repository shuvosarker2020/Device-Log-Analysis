import logging
import requests
from typing import Dict, Any
from app.core.models import AlertEvent
from app.notifiers.base import BaseNotifier
from app.config import cfg

logger = logging.getLogger("NetLogIQ.Webhook")

class WebhookNotifier(BaseNotifier):
    channel_name: str = "webhook"

    def send(self, alert: AlertEvent) -> bool:
        success = False
        if self._send_slack(alert):
            success = True
        if self._send_discord(alert):
            success = True
        if self._send_teams(alert):
            success = True
        if self._send_generic(alert):
            success = True
        return success

    def _send_slack(self, alert: AlertEvent) -> bool:
        s_cfg = cfg.get("notifications", "slack", default={})
        if not s_cfg.get("enabled") or not s_cfg.get("webhook_url"):
            return False

        color = "#e53e3e" if alert.severity <= 1 else "#dd6b20"
        payload = {
            "channel": s_cfg.get("channel", "#network-alerts"),
            "attachments": [
                {
                    "color": color,
                    "title": f"🚨 [CRITICAL ALERT] {alert.rule_name} on {alert.hostname}",
                    "fields": [
                        {"title": "Device", "value": alert.hostname, "short": True},
                        {"title": "IP", "value": alert.source_ip, "short": True},
                        {"title": "Vendor", "value": alert.vendor, "short": True},
                        {"title": "Category", "value": alert.category, "short": True},
                        {"title": "Severity", "value": f"{alert.severity_name} ({alert.severity})", "short": True},
                        {"title": "Message", "value": alert.message[:300], "short": False},
                    ],
                    "footer": "NetLogIQ Syslog Analyzer",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }
        try:
            r = requests.post(s_cfg["webhook_url"], json=payload, timeout=8)
            return r.status_code == 200
        except Exception as e:
            logger.error(f"[Slack] Error: {e}")
            return False

    def _send_discord(self, alert: AlertEvent) -> bool:
        d_cfg = cfg.get("notifications", "discord", default={})
        if not d_cfg.get("enabled") or not d_cfg.get("webhook_url"):
            return False

        color = 15158332 if alert.severity <= 1 else 15105570
        payload = {
            "embeds": [
                {
                    "title": f"🚨 {alert.rule_name} - {alert.hostname}",
                    "description": f"```{alert.message[:400]}```",
                    "color": color,
                    "fields": [
                        {"name": "Device", "value": alert.hostname, "inline": True},
                        {"name": "IP", "value": alert.source_ip, "inline": True},
                        {"name": "Vendor", "value": alert.vendor, "inline": True},
                        {"name": "Category", "value": alert.category, "inline": True},
                        {"name": "Severity", "value": alert.severity_name, "inline": True},
                    ],
                    "footer": {"text": "NetLogIQ Syslog Analyzer"}
                }
            ]
        }
        try:
            r = requests.post(d_cfg["webhook_url"], json=payload, timeout=8)
            return r.status_code in [200, 204]
        except Exception as e:
            logger.error(f"[Discord] Error: {e}")
            return False

    def _send_teams(self, alert: AlertEvent) -> bool:
        t_cfg = cfg.get("notifications", "ms_teams", default={})
        if not t_cfg.get("enabled") or not t_cfg.get("webhook_url"):
            return False

        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "FF0000" if alert.severity <= 1 else "FFA500",
            "summary": f"Alert on {alert.hostname}",
            "title": f"🚨 Critical Alert: {alert.rule_name}",
            "sections": [
                {
                    "activityTitle": f"Device: {alert.hostname} ({alert.source_ip})",
                    "activitySubtitle": f"Vendor: {alert.vendor} | Severity: {alert.severity_name}",
                    "facts": [
                        {"name": "Category", "value": alert.category},
                        {"name": "Rule", "value": alert.rule_name},
                        {"name": "Log Message", "value": alert.message[:300]},
                    ],
                    "markdown": True
                }
            ]
        }
        try:
            r = requests.post(t_cfg["webhook_url"], json=payload, timeout=8)
            return r.status_code == 200
        except Exception as e:
            logger.error(f"[Teams] Error: {e}")
            return False

    def _send_generic(self, alert: AlertEvent) -> bool:
        g_cfg = cfg.get("notifications", "generic_webhook", default={})
        if not g_cfg.get("enabled") or not g_cfg.get("webhook_url"):
            return False

        payload = {
            "event": "CRITICAL_LOG_ALERT",
            "rule": alert.rule_name,
            "category": alert.category,
            "severity": alert.severity,
            "severity_name": alert.severity_name,
            "device": alert.hostname,
            "ip": alert.source_ip,
            "vendor": alert.vendor,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat()
        }
        headers = g_cfg.get("headers", {})
        try:
            r = requests.post(g_cfg["webhook_url"], json=payload, headers=headers, timeout=8)
            return r.status_code in [200, 201, 202, 204]
        except Exception as e:
            logger.error(f"[GenericWebhook] Error: {e}")
            return False
