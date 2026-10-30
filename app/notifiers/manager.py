import logging
from typing import List
from app.core.models import AlertEvent
from app.notifiers.base import BaseNotifier
from app.notifiers.telegram import TelegramNotifier
from app.notifiers.webhook import WebhookNotifier
from app.notifiers.email_notifier import EmailNotifier

logger = logging.getLogger("NetLogIQ.NotificationManager")

class NotificationManager:
    def __init__(self):
        self.notifiers: List[BaseNotifier] = [
            TelegramNotifier(),
            WebhookNotifier(),
            EmailNotifier(),
        ]

    def dispatch(self, alert: AlertEvent) -> List[str]:
        """
        Dispatch the alert to all enabled notification channels.
        Returns the list of channels that successfully delivered the alert.
        """
        successful_channels = []
        for notifier in self.notifiers:
            try:
                if notifier.send(alert):
                    successful_channels.append(notifier.channel_name)
            except Exception as e:
                logger.error(f"Notifier {notifier.channel_name} failed: {e}")

        alert.notified_channels = successful_channels
        return successful_channels

    def send_test_alert(self, channel: str) -> bool:
        """Send a test alert to verify notification credentials."""
        test_event = AlertEvent(
            source_ip="127.0.0.1",
            hostname="TEST-DEVICE-01",
            vendor="Cisco",
            rule_name="Test Notification",
            category="TEST",
            severity=1,
            severity_name="Alert",
            message="This is a test notification from NetLogIQ Syslog Analyzer. If you received this, notifications are working correctly!",
            status="ACTIVE"
        )
        for n in self.notifiers:
            if n.channel_name == channel:
                return n.send(test_event)
        # If generic webhook / slack / discord test
        if channel in ["slack", "discord", "ms_teams", "generic_webhook"]:
            wh = WebhookNotifier()
            if channel == "slack": return wh._send_slack(test_event)
            if channel == "discord": return wh._send_discord(test_event)
            if channel == "ms_teams": return wh._send_teams(test_event)
            if channel == "generic_webhook": return wh._send_generic(test_event)
        return False

notification_manager = NotificationManager()
