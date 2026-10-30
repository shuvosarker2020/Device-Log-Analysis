import re
from datetime import datetime, timezone
from typing import Optional
from app.core.models import NormalizedLog
from app.parsers.base import BaseParser

# Huawei VRP syslog format regex
# Example: %%01DEVM/1/POWER_OFF(l)[12]: The power supply 1 was powered off.
# Example: %%ddFACILITY/severity/DIGEST(l)[tag]: message
HUAWEI_PATTERN = re.compile(
    r'%%(?P<version>\d{2})?(?P<fac>[A-Za-z0-9_\-]+)/(?P<sev>[0-7])/(?P<digest>[A-Za-z0-9_\-]+)(?:\([a-z]\))?(?:\[\d+\])?:\s*(?P<body>.*)',
    re.IGNORECASE
)

class HuaweiParser(BaseParser):
    vendor_name: str = "Huawei"

    def can_parse(self, raw_message: str) -> bool:
        return "%%" in raw_message and "/" in raw_message

    def parse(self, raw_message: str, source_ip: str) -> Optional[NormalizedLog]:
        fac_code, pri_sev, remaining = self.extract_pri(raw_message)

        match = HUAWEI_PATTERN.search(remaining)
        if not match:
            return None

        huawei_fac = match.group("fac").upper()
        huawei_sev = int(match.group("sev"))
        digest = match.group("digest").upper()
        body = match.group("body").strip()
        mnemonic = f"{huawei_fac}/{huawei_sev}/{digest}"

        # Extract hostname from text before '%%'
        header_part = remaining[:match.start()].strip()
        hostname = source_ip

        if header_part:
            tokens = header_part.split()
            # Often format is: 'Oct 15 2026 11:25:00 Huawei-NE40E'
            if len(tokens) >= 1:
                # The token right before '%%' is usually the device hostname
                hostname = tokens[-1]

        # Huawei severity directly corresponds to 0-7 standard
        severity = huawei_sev
        severity_name = self.get_severity_name(severity)

        return NormalizedLog(
            timestamp=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            source_ip=source_ip,
            hostname=hostname,
            vendor=self.vendor_name,
            facility=fac_code,
            facility_name=huawei_fac.lower(),
            severity=severity,
            severity_name=severity_name,
            mnemonic=mnemonic,
            event_category="GENERAL",
            raw_message=raw_message,
            clean_message=body,
            metadata={
                "huawei_module": huawei_fac,
                "huawei_digest": digest,
            }
        )
