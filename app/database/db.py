import sqlite3
import os
from pathlib import Path
from app.config import cfg, BASE_DIR

DB_PATH = BASE_DIR / cfg.get("database", "path", default="data/syslog_analyzer.db")

def get_db_connection() -> sqlite3.Connection:
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # High-performance SQLite pragmas
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-64000;")  # 64MB cache
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table: logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        received_at TEXT NOT NULL,
        source_ip TEXT NOT NULL,
        hostname TEXT NOT NULL,
        vendor TEXT NOT NULL,
        facility INTEGER NOT NULL,
        facility_name TEXT NOT NULL,
        severity INTEGER NOT NULL,
        severity_name TEXT NOT NULL,
        mnemonic TEXT NOT NULL,
        event_category TEXT NOT NULL,
        raw_message TEXT NOT NULL,
        clean_message TEXT NOT NULL,
        is_alert INTEGER NOT NULL DEFAULT 0,
        alert_rule TEXT
    );
    """)

    # Table: alerts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_id INTEGER,
        timestamp TEXT NOT NULL,
        source_ip TEXT NOT NULL,
        hostname TEXT NOT NULL,
        vendor TEXT NOT NULL,
        rule_name TEXT NOT NULL,
        category TEXT NOT NULL,
        severity INTEGER NOT NULL,
        severity_name TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        acknowledged_by TEXT,
        notified_channels TEXT,
        FOREIGN KEY (log_id) REFERENCES logs(id) ON DELETE SET NULL
    );
    """)

    # Table: device_inventory (auto-discovered devices)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        ip TEXT PRIMARY KEY,
        hostname TEXT NOT NULL,
        vendor TEXT NOT NULL,
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL,
        total_logs INTEGER DEFAULT 0,
        total_alerts INTEGER DEFAULT 0,
        last_severity INTEGER DEFAULT 6,
        status TEXT DEFAULT 'UP'
    );
    """)

    # Indexes for optimal query performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_source_ip ON logs(source_ip);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_hostname ON logs(hostname);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_vendor ON logs(vendor);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_severity ON logs(severity);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_category ON logs(event_category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_is_alert ON logs(is_alert);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);")

    conn.commit()
    conn.close()
    print("[Database] Initialized tables and indexes successfully.")
