import re
from datetime import datetime, timezone
from typing import Optional
from app.core.models import NormalizedLog
from app.parsers.base import BaseParser

# ZTE ZXROS syslog format
# Example: [ZXR10] %POWER-1-FAIL: Power Supply Unit 2 output failure.
# Example: %SYS-2-RELOAD: System is reloading by command line.
ZTE_PATTERN = re.compile(
    r'%(?P<module>[A-Za-z0-9_\-]+)-(?P<sev>[0-7])-(?P<name>[A-Za-z0-9_\-]+):\s*(?P<body>.*)',
    re.IGNORECASE
)

class ZTEParser(BaseParser):
    vendor_name: str = "ZTE"

    def can_parse(self, raw_message: str) -> bool:
        raw_upper = raw_message.upper()
        if "ZTE" in raw_upper or "ZXR10" in raw_upper or "ZXROS" in raw_upper or "ZXHN" in raw_upper:
            return True
        return False

    def parse(self, raw_message: str, source_ip: str) -> Optional[NormalizedLog]:
        fac_code, pri_sev, remaining = self.extract_pri(raw_message)

        match = ZTE_PATTERN.search(remaining)
        if not match:
            # Fallback for generic ZTE message without standard mnemonic
            header_part = remaining
            mnemonic = "ZTE-EVENT"
            body = remaining
            severity = pri_sev
            hostname = source_ip
            tokens = header_part.split()
            if tokens:
                for t in tokens:
                    if "ZTE" in t.upper() or "ZXR" in t.upper():
                        hostname = t.strip("[]:")
        else:
            module = match.group("module").upper()
            sev_num = int(match.group("sev"))
            name = match.group("name").upper()
            mnemonic = f"%{module}-{sev_num}-{name}"
            body = match.group("body").strip()
            severity = sev_num

            header_part = remaining[:match.start()].strip()
            hostname = source_ip
            if header_part:
                tokens = header_part.split()
                if tokens:
                    hostname = tokens[-1].strip("[]:")

        severity_name = self.get_severity_name(severity)

        return NormalizedLog(
            timestamp=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            source_ip=source_ip,
            hostname=hostname,
            vendor=self.vendor_name,
            facility=fac_code,
            facility_name="zte",
            severity=severity,
            severity_name=severity_name,
            mnemonic=mnemonic,
            event_category="GENERAL",
            raw_message=raw_message,
            clean_message=body,
            metadata={"zte_device": hostname}
        )
