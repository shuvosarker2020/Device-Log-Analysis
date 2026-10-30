import re
from datetime import datetime, timezone
from typing import Optional
from app.core.models import NormalizedLog
from app.parsers.base import BaseParser

# Nokia SR OS (TiMOS) syslog pattern
# Example: Nokia-7750SR SYSTEM-CRITICAL-1002: Base Chassis Power Supply 1 Failed or Removed
# Example: PORT-MAJOR-2001: Port 1/1/c1/1 is operational down
NOKIA_PATTERN = re.compile(
    r'(?P<subsys>[A-Z0-9_\-]+)-(?P<sev>CRITICAL|MAJOR|MINOR|WARNING|INFO|CLEARED|DEBUG)-(?P<id>\d+):\s*(?P<body>.*)',
    re.IGNORECASE
)

NOKIA_SEV_MAP = {
    "CRITICAL": 2,
    "MAJOR": 3,
    "MINOR": 4,
    "WARNING": 4,
    "INFO": 6,
    "CLEARED": 5,
    "DEBUG": 7,
}

class NokiaParser(BaseParser):
    vendor_name: str = "Nokia"

    def can_parse(self, raw_message: str) -> bool:
        raw_upper = raw_message.upper()
        if "NOKIA" in raw_upper or "TIMOS" in raw_upper or "7750" in raw_upper or "7250" in raw_upper:
            return True
        return bool(NOKIA_PATTERN.search(raw_message))

    def parse(self, raw_message: str, source_ip: str) -> Optional[NormalizedLog]:
        fac_code, pri_sev, remaining = self.extract_pri(raw_message)

        match = NOKIA_PATTERN.search(remaining)
        if not match:
            return None

        subsys = match.group("subsys").upper()
        sev_str = match.group("sev").upper()
        event_id = match.group("id")
        mnemonic = f"{subsys}-{sev_str}-{event_id}"
        body = match.group("body").strip()

        severity = NOKIA_SEV_MAP.get(sev_str, pri_sev)
        severity_name = self.get_severity_name(severity)

        header_part = remaining[:match.start()].strip()
        hostname = source_ip

        if header_part:
            tokens = header_part.split()
            if tokens:
                hostname = tokens[-1].strip("[]:")

        return NormalizedLog(
            timestamp=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            source_ip=source_ip,
            hostname=hostname,
            vendor=self.vendor_name,
            facility=fac_code,
            facility_name=subsys.lower(),
            severity=severity,
            severity_name=severity_name,
            mnemonic=mnemonic,
            event_category="GENERAL",
            raw_message=raw_message,
            clean_message=body,
            metadata={"nokia_subsystem": subsys, "nokia_severity": sev_str, "nokia_event_id": event_id}
        )
