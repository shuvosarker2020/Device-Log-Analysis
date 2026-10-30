import re
from datetime import datetime, timezone
from typing import Optional
from app.core.models import NormalizedLog
from app.parsers.base import BaseParser

# RFC 3164 header: Mmm dd hh:mm:ss hostname tag[pid]: message
RFC3164_RE = re.compile(
    r'^(?:(?P<month>[A-Za-z]{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2}))\s+(?P<host>[^\s:]+)\s+(?:(?P<tag>[a-zA-Z0-9_\-\.]+)(?:\[(?P<pid>\d+)\])?:\s*)?(?P<body>.*)',
    re.DOTALL
)

# RFC 5424 header: <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [SD] MSG
RFC5424_RE = re.compile(
    r'^1\s+(?P<ts>\S+)\s+(?P<host>\S+)\s+(?P<app>\S+)\s+(?P<procid>\S+)\s+(?P<msgid>\S+)\s+(?:\[(?P<sd>[^\]]+)\])?\s*(?P<body>.*)',
    re.DOTALL
)

class GenericParser(BaseParser):
    vendor_name: str = "Generic"

    def can_parse(self, raw_message: str) -> bool:
        return True  # Fallback for all messages

    def parse(self, raw_message: str, source_ip: str) -> Optional[NormalizedLog]:
        fac_code, sev_code, remaining = self.extract_pri(raw_message)

        hostname = source_ip
        mnemonic = "GENERIC-LOG"
        clean_body = remaining
        detected_vendor = "Generic"

        # Check for hints of other vendors
        raw_upper = raw_message.upper()
        if "MIKROTIK" in raw_upper or "ROUTEROS" in raw_upper:
            detected_vendor = "MikroTik"
        elif "FORTIGATE" in raw_upper or "FORTIOS" in raw_upper:
            detected_vendor = "Fortinet"
        elif "ARISTA" in raw_upper or "EOS" in raw_upper:
            detected_vendor = "Arista"
        elif "PALO ALTO" in raw_upper or "PAN-OS" in raw_upper:
            detected_vendor = "Palo Alto"
        elif "LINUX" in raw_upper or "SYSTEMD" in raw_upper:
            detected_vendor = "Linux"

        # Try RFC 5424
        m5424 = RFC5424_RE.match(remaining)
        if m5424:
            h = m5424.group("host")
            if h and h != "-":
                hostname = h
            app = m5424.group("app")
            if app and app != "-":
                mnemonic = app.upper()
            clean_body = m5424.group("body").strip()
        else:
            # Try RFC 3164
            m3164 = RFC3164_RE.match(remaining)
            if m3164:
                h = m3164.group("host")
                if h:
                    hostname = h
                tag = m3164.group("tag")
                if tag:
                    mnemonic = tag.upper()
                clean_body = m3164.group("body").strip()

        severity_name = self.get_severity_name(sev_code)
        facility_name = self.get_facility_name(fac_code)

        return NormalizedLog(
            timestamp=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            source_ip=source_ip,
            hostname=hostname,
            vendor=detected_vendor,
            facility=fac_code,
            facility_name=facility_name,
            severity=sev_code,
            severity_name=severity_name,
            mnemonic=mnemonic,
            event_category="GENERAL",
            raw_message=raw_message,
            clean_message=clean_body,
            metadata={"parser": "generic"}
        )
