import re
from datetime import datetime, timezone
from typing import Optional
from app.core.models import NormalizedLog
from app.parsers.base import BaseParser

# Regex to detect and match Cisco syslog format
# Example: <189>142: Oct 15 11:20:10.123: %SYS-5-RELOAD: Reload requested by vty0
# Example: Oct 15 11:20:10 Cisco-R1 : %ENVMON-1-POWER_SUPPLY: Power supply 1 failed
CISCO_MNEMONIC_RE = re.compile(
    r'%(?P<fac>[A-Z0-9_]+)-(?P<sev>[0-7])-(?P<mnemonic>[A-Z0-9_]+):\s*(?P<body>.*)',
    re.IGNORECASE
)

CISCO_HEADER_RE = re.compile(
    r'^(?:(?P<seq>\d+):\s*)?(?:(?P<month>[A-Za-z]{3})\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d+)?))?(?:\s+[A-Z]{3,4})?(?::\s*)?(?:(?P<host>[a-zA-Z0-9\.\-_]+)\s*:?\s*)?'
)

class CiscoParser(BaseParser):
    vendor_name: str = "Cisco"

    def can_parse(self, raw_message: str) -> bool:
        # Check for %FACILITY-[0-7]-MNEMONIC pattern
        return bool(re.search(r'%[A-Z0-9_]+-[0-7]-[A-Z0-9_]+:', raw_message, re.IGNORECASE))

    def parse(self, raw_message: str, source_ip: str) -> Optional[NormalizedLog]:
        fac_code, sev_code, remaining = self.extract_pri(raw_message)

        cisco_match = CISCO_MNEMONIC_RE.search(remaining)
        if not cisco_match:
            return None

        cisco_fac = cisco_match.group("fac").upper()
        cisco_sev = int(cisco_match.group("sev"))
        mnemonic = f"%{cisco_fac}-{cisco_sev}-{cisco_match.group('mnemonic').upper()}"
        clean_body = cisco_match.group("body").strip()

        # The header part is everything before the %FACILITY...
        header_part = remaining[:cisco_match.start()].strip()
        hostname = source_ip

        if header_part:
            # Try to extract hostname from header
            tokens = header_part.replace(":", " ").split()
            # If tokens contains words after timestamp
            candidates = [t for t in tokens if not re.match(r'^\d+$', t) and not re.match(r'^[A-Za-z]{3}$', t) and not re.match(r'^\d{2}:\d{2}:\d{2}', t)]
            if candidates:
                hostname = candidates[-1]

        # Use Cisco specific severity
        severity = cisco_sev
        severity_name = self.get_severity_name(severity)
        facility_name = cisco_fac.lower()

        return NormalizedLog(
            timestamp=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            source_ip=source_ip,
            hostname=hostname,
            vendor=self.vendor_name,
            facility=fac_code,
            facility_name=facility_name,
            severity=severity,
            severity_name=severity_name,
            mnemonic=mnemonic,
            event_category="GENERAL", # Engine will classify this
            raw_message=raw_message,
            clean_message=clean_body,
            metadata={"cisco_facility": cisco_fac, "cisco_mnemonic": cisco_match.group('mnemonic')}
        )
