import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.models import AlertEvent
from app.notifiers.base import BaseNotifier
from app.config import cfg

logger = logging.getLogger("NetLogIQ.Email")

class EmailNotifier(BaseNotifier):
    channel_name: str = "email"

    def send(self, alert: AlertEvent) -> bool:
        e_cfg = cfg.get("notifications", "email", default={})
        if not e_cfg.get("enabled"):
            return False

        smtp_server = e_cfg.get("smtp_server")
        smtp_port = e_cfg.get("smtp_port", 587)
        use_tls = e_cfg.get("use_tls", True)
        username = e_cfg.get("username")
        password = e_cfg.get("password")
        from_email = e_cfg.get("from_email")
        to_emails = e_cfg.get("to_emails", [])

        if not smtp_server or not to_emails:
            logger.warning("[Email] Missing smtp_server or to_emails")
            return False

        subject = f"[CRITICAL ALERT] {alert.rule_name} on {alert.hostname} ({alert.source_ip})"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f7fafc; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background: white; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <div style="background-color: #e53e3e; color: white; padding: 16px 20px;">
                    <h2 style="margin: 0; font-size: 18px;">🚨 NetLogIQ Alert Notification</h2>
                </div>
                <div style="padding: 20px;">
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr><td style="padding: 8px 0; color: #718096; width: 35%;"><strong>Rule:</strong></td><td style="color: #2d3748; font-weight: bold;">{alert.rule_name}</td></tr>
                        <tr><td style="padding: 8px 0; color: #718096;"><strong>Category:</strong></td><td><span style="background: #fed7d7; color: #9b2c2c; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">{alert.category}</span></td></tr>
                        <tr><td style="padding: 8px 0; color: #718096;"><strong>Device Hostname:</strong></td><td style="color: #2d3748;">{alert.hostname}</td></tr>
                        <tr><td style="padding: 8px 0; color: #718096;"><strong>Device IP:</strong></td><td style="color: #2d3748;">{alert.source_ip}</td></tr>
                        <tr><td style="padding: 8px 0; color: #718096;"><strong>Vendor:</strong></td><td style="color: #2d3748;">{alert.vendor}</td></tr>
                        <tr><td style="padding: 8px 0; color: #718096;"><strong>Severity:</strong></td><td>{alert.severity_name} (Level {alert.severity})</td></tr>
                        <tr><td style="padding: 8px 0; color: #718096;"><strong>Timestamp:</strong></td><td>{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</td></tr>
                    </table>
                    <div style="background: #edf2f7; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 13px; color: #1a202c; word-break: break-all;">
                        {alert.message}
                    </div>
                </div>
                <div style="background: #edf2f7; padding: 12px 20px; font-size: 12px; color: #a0aec0; text-align: center;">
                    Generated automatically by NetLogIQ Syslog Analyzer
                </div>
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = ", ".join(to_emails)
        msg.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                if use_tls:
                    server.starttls()
                if username and password:
                    server.login(username, password)
                server.sendmail(from_email, to_emails, msg.as_string())
            logger.info(f"[Email] Alert successfully sent to {to_emails}")
            return True
        except Exception as e:
            logger.error(f"[Email] Failed to send alert: {e}")
            return False
