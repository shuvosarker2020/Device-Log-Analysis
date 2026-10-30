from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

SEVERITY_NAMES = {
    0: "Emergency",
    1: "Alert",
    2: "Critical",
    3: "Error",
    4: "Warning",
    5: "Notice",
    6: "Informational",
    7: "Debug",
}

FACILITY_NAMES = {
    0: "kern",
    1: "user",
    2: "mail",
    3: "daemon",
    4: "auth",
    5: "syslog",
    6: "lpr",
    7: "news",
    8: "uucp",
    9: "cron",
    10: "authpriv",
    11: "ftp",
    12: "ntp",
    13: "security",
    14: "console",
    15: "solariscron",
    16: "local0",
    17: "local1",
    18: "local2",
    19: "local3",
    20: "local4",
    21: "local5",
    22: "local6",
    23: "local7",
}

class NormalizedLog(BaseModel):
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_ip: str
    hostname: str
    vendor: str = "Generic"
    facility: int = 16
    facility_name: str = "local0"
    severity: int = 6
    severity_name: str = "Informational"
    mnemonic: str = "UNKNOWN"
    event_category: str = "GENERAL"
    raw_message: str
    clean_message: str
    is_alert: bool = False
    alert_rule: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AlertEvent(BaseModel):
    id: Optional[int] = None
    log_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_ip: str
    hostname: str
    vendor: str
    rule_name: str
    category: str
    severity: int
    severity_name: str
    message: str
    status: str = "ACTIVE"  # ACTIVE, ACKNOWLEDGED, RESOLVED
    acknowledged_by: Optional[str] = None
    notified_channels: List[str] = Field(default_factory=list)
