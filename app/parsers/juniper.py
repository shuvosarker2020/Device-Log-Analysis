import re
from datetime import datetime, timezone
from typing import Optional
from app.core.models import NormalizedLog
from app.parsers.base import BaseParser

# Juniper Junos syslog format regex
# Example: Oct 15 11:30:00 Juniper-MX960 chassism[2841]: CHASSISD_POWER_SUPPLY_FAILED: Power Supply 0 failure
# Example: process[PID]: TAG: message
JUNIPER_PATTERN = re.compile(
    r'(?P<process>[a-zA-Z0-9_\-]+)(?:\[(?P<pid>\d+)\])?:\s*(?:%[A-Z0-9_]+:\s*)?(?P<tag>[A-Z0-9_]{3,}):\s*(?P<body>.*)'
)

# Known Juniper Junos processes
JUNIPER_PROCESSES = {
    "chassisd", "chassism", "eventd", "rpd", "snmpd", "alarmd", "cosd",
    "dcd", "dfwd", "mib2d", "pfed", "kernel", "mgd", "auth", "junos"
}

class JuniperParser(BaseParser):
    vendor_name: str = "Juniper"

    def can_parse(self, raw_message: str) -> bool:
        # Check for Juniper process signature or vendor keywords
        raw_lower = raw_message.lower()
        if "juniper" in raw_lower or "junos" in raw_lower:
            return True
        for proc in JUNIPER_PROCESSES:
            if f"{proc}[" in raw_lower or f"{proc}:" in raw_lower:
                return True
        return False

    def parse(self, raw_message: str, source_ip: str) -> Optional[NormalizedLog]:
        fac_code, pri_sev, remaining = self.extract_pri(raw_message)

        match = JUNIPER_PATTERN.search(remaining)
        if not match:
            return None

        process = match.group("process")
        tag = match.group("tag").upper()
        body = match.group("body").strip()
        mnemonic = f"{process.upper()}:{tag}"

        # Extract hostname from header
        header_part = remaining[:match.start()].strip()
        hostname = source_ip

        if header_part:
            tokens = header_part.split()
            # If standard syslog header "Oct 15 11:30:00 Juniper-MX960"
            if len(tokens) >= 4:
                hostname = tokens[3]
            elif len(tokens) >= 1:
                hostname = tokens[-1]

        # Determine severity:
        # Juniper PRI severity is typically used, but check critical tags
        severity = pri_sev
        if any(w in tag for w in ["FAILED", "FAILURE", "PANIC", "CRASH", "REBOOT", "CRITICAL"]):
            severity = min(severity, 2)
        elif any(w in tag for w in ["WARN", "HIGH", "DOWN", "ERROR"]):
            severity = min(severity, 4)

        severity_name = self.get_severity_name(severity)

        return NormalizedLog(
            timestamp=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            source_ip=source_ip,
            hostname=hostname,
            vendor=self.vendor_name,
            facility=fac_code,
            facility_name=process.lower(),
            severity=severity,
            severity_name=severity_name,
            mnemonic=mnemonic,
            event_category="GENERAL",
            raw_message=raw_message,
            clean_message=body,
            metadata={
                "juniper_process": process,
                "juniper_tag": tag,
            }
        )
