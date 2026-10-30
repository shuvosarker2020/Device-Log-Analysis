import logging
import requests
from app.core.models import AlertEvent
from app.notifiers.base import BaseNotifier
from app.config import cfg

logger = logging.getLogger("NetLogIQ.Telegram")

class TelegramNotifier(BaseNotifier):
    channel_name: str = "telegram"

    def send(self, alert: AlertEvent) -> bool:
        t_cfg = cfg.get("notifications", "telegram", default={})
        if not t_cfg.get("enabled"):
            return False

        bot_token = t_cfg.get("bot_token")
        chat_id = t_cfg.get("chat_id")

        if not bot_token or not chat_id:
            logger.warning("[Telegram] Missing bot_token or chat_id")
            return False

        emoji = "🚨" if alert.severity <= 1 else "⚠️"
        text = (
            f"{emoji} *NETLOG CRITICAL ALERT*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"*Rule:* `{alert.rule_name}`\n"
            f"*Category:* `{alert.category}`\n"
            f"*Severity:* {alert.severity_name} (Level {alert.severity})\n"
            f"*Device:* `{alert.hostname}`\n"
            f"*IP Address:* `{alert.source_ip}`\n"
            f"*Vendor:* {alert.vendor}\n"
            f"*Time:* `{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"*Message:*\n`{alert.message[:400]}`"
        )

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        try:
            resp = requests.post(url, json=payload, timeout=8)
            if resp.status_code == 200:
                logger.info(f"[Telegram] Alert sent for device {alert.hostname}")
                return True
            else:
                logger.error(f"[Telegram] Failed: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"[Telegram] Exception sending alert: {e}")
            return False
