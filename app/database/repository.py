import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from app.core.models import NormalizedLog, AlertEvent
from app.database.db import get_db_connection

class LogRepository:
    def __init__(self):
        pass

    def save_log(self, log: NormalizedLog) -> int:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            ts_str = log.timestamp.isoformat()
            rcv_str = log.received_at.isoformat()

            cursor.execute("""
            INSERT INTO logs (
                timestamp, received_at, source_ip, hostname, vendor,
                facility, facility_name, severity, severity_name,
                mnemonic, event_category, raw_message, clean_message,
                is_alert, alert_rule
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ts_str, rcv_str, log.source_ip, log.hostname, log.vendor,
                log.facility, log.facility_name, log.severity, log.severity_name,
                log.mnemonic, log.event_category, log.raw_message, log.clean_message,
                1 if log.is_alert else 0, log.alert_rule
            ))
            log_id = cursor.lastrowid

            # Upsert into devices table
            cursor.execute("""
            INSERT INTO devices (ip, hostname, vendor, first_seen, last_seen, total_logs, total_alerts, last_severity)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(ip) DO UPDATE SET
                hostname = excluded.hostname,
                vendor = excluded.vendor,
                last_seen = excluded.last_seen,
                total_logs = devices.total_logs + 1,
                total_alerts = devices.total_alerts + excluded.total_alerts,
                last_severity = excluded.last_severity
            """, (
                log.source_ip, log.hostname, log.vendor, ts_str, ts_str,
                1 if log.is_alert else 0, log.severity
            ))

            conn.commit()
            return log_id
        finally:
            conn.close()

    def save_alert(self, alert: AlertEvent, log_id: Optional[int] = None) -> int:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            ts_str = alert.timestamp.isoformat()
            channels_str = ",".join(alert.notified_channels)

            cursor.execute("""
            INSERT INTO alerts (
                log_id, timestamp, source_ip, hostname, vendor,
                rule_name, category, severity, severity_name,
                message, status, notified_channels
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, ts_str, alert.source_ip, alert.hostname, alert.vendor,
                alert.rule_name, alert.category, alert.severity, alert.severity_name,
                alert.message, alert.status, channels_str
            ))
            alert_id = cursor.lastrowid
            conn.commit()
            return alert_id
        finally:
            conn.close()

    def get_summary_metrics(self) -> Dict[str, Any]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM logs;")
            total_logs = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM alerts;")
            total_alerts = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = 'ACTIVE';")
            active_alerts = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM devices;")
            total_devices = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM logs WHERE severity <= 2;")
            critical_errors = cursor.fetchone()[0]

            return {
                "total_logs": total_logs,
                "total_alerts": total_alerts,
                "active_alerts": active_alerts,
                "total_devices": total_devices,
                "critical_errors": critical_errors,
            }
        finally:
            conn.close()

    def get_severity_analytics(self) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT severity, severity_name, COUNT(*) as count
            FROM logs
            GROUP BY severity, severity_name
            ORDER BY severity ASC;
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_device_analytics(self, limit: int = 15) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT 
                hostname, 
                source_ip, 
                vendor, 
                COUNT(*) as total_logs,
                SUM(CASE WHEN severity <= 3 THEN 1 ELSE 0 END) as error_count,
                SUM(CASE WHEN is_alert = 1 THEN 1 ELSE 0 END) as alert_count,
                MAX(timestamp) as last_seen
            FROM logs
            GROUP BY hostname, source_ip, vendor
            ORDER BY error_count DESC, total_logs DESC
            LIMIT ?;
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_ip_analytics(self, limit: int = 15) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT 
                source_ip,
                MAX(hostname) as hostname,
                MAX(vendor) as vendor,
                COUNT(*) as total_logs,
                SUM(CASE WHEN severity <= 3 THEN 1 ELSE 0 END) as error_count,
                SUM(CASE WHEN is_alert = 1 THEN 1 ELSE 0 END) as alert_count,
                MAX(timestamp) as last_seen
            FROM logs
            GROUP BY source_ip
            ORDER BY total_logs DESC
            LIMIT ?;
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_error_category_analytics(self) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT event_category, COUNT(*) as count
            FROM logs
            WHERE event_category != 'GENERAL' OR severity <= 4
            GROUP BY event_category
            ORDER BY count DESC;
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_vendor_analytics(self) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT vendor, COUNT(*) as count,
                   SUM(CASE WHEN severity <= 3 THEN 1 ELSE 0 END) as error_count
            FROM logs
            GROUP BY vendor
            ORDER BY count DESC;
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_timeline_analytics(self) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # SQLite substr for hour aggregation YYYY-MM-DDTHH
            cursor.execute("""
            SELECT 
                substr(timestamp, 1, 13) || ':00' as time_bucket,
                COUNT(*) as total,
                SUM(CASE WHEN severity <= 3 THEN 1 ELSE 0 END) as errors,
                SUM(CASE WHEN is_alert = 1 THEN 1 ELSE 0 END) as alerts
            FROM logs
            GROUP BY time_bucket
            ORDER BY time_bucket DESC
            LIMIT 24;
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in reversed(rows)]
        finally:
            conn.close()

    def get_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        vendor: Optional[str] = None,
        severity: Optional[int] = None,
        source_ip: Optional[str] = None,
        hostname: Optional[str] = None,
        category: Optional[str] = None,
        is_alert_only: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            conditions = []
            params = []

            if search:
                conditions.append("(raw_message LIKE ? OR clean_message LIKE ? OR mnemonic LIKE ?)")
                p = f"%{search}%"
                params.extend([p, p, p])
            if vendor and vendor != "ALL":
                conditions.append("vendor = ?")
                params.append(vendor)
            if severity is not None and severity != -1:
                conditions.append("severity = ?")
                params.append(severity)
            if source_ip:
                conditions.append("source_ip LIKE ?")
                params.append(f"%{source_ip}%")
            if hostname:
                conditions.append("hostname LIKE ?")
                params.append(f"%{hostname}%")
            if category and category != "ALL":
                conditions.append("event_category = ?")
                params.append(category)
            if is_alert_only:
                conditions.append("is_alert = 1")

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # Count total matching
            cursor.execute(f"SELECT COUNT(*) FROM logs {where_clause}", params)
            total = cursor.fetchone()[0]

            # Fetch rows
            query = f"""
            SELECT * FROM logs 
            {where_clause}
            ORDER BY id DESC
            LIMIT ? OFFSET ?;
            """
            cursor.execute(query, params + [limit, offset])
            rows = cursor.fetchall()
            return [dict(row) for row in rows], total
        finally:
            conn.close()

    def get_alerts(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if status and status != "ALL":
                cursor.execute("""
                SELECT * FROM alerts WHERE status = ? ORDER BY id DESC LIMIT ?
                """, (status, limit))
            else:
                cursor.execute("""
                SELECT * FROM alerts ORDER BY id DESC LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def acknowledge_alert(self, alert_id: int, user: str = "Admin") -> bool:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE alerts SET status = 'ACKNOWLEDGED', acknowledged_by = ? WHERE id = ?
            """, (user, alert_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def purge_old_logs(self, days: int) -> int:
        if days <= 0:
            return 0
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            DELETE FROM logs WHERE timestamp < datetime('now', '-' || ? || ' days')
            """, (days,))
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        finally:
            conn.close()

repository = LogRepository()
