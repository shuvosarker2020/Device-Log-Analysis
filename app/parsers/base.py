from abc import ABC, abstractmethod
from typing import Optional, Tuple
from app.core.models import NormalizedLog, SEVERITY_NAMES, FACILITY_NAMES

class BaseParser(ABC):
    vendor_name: str = "Generic"

    @abstractmethod
    def can_parse(self, raw_message: str) -> bool:
        """Return True if this parser is suitable for the given raw log message."""
        pass

    @abstractmethod
    def parse(self, raw_message: str, source_ip: str) -> Optional[NormalizedLog]:
        """Parse raw log string and return a NormalizedLog."""
        pass

    @staticmethod
    def extract_pri(message: str) -> Tuple[int, int, str]:
        """
        Extract RFC PRI (<number>) if present.
        Returns: (facility, severity, remaining_message)
        """
        msg = message.strip()
        if msg.startswith("<"):
            end_idx = msg.find(">")
            if end_idx != -1:
                pri_str = msg[1:end_idx]
                if pri_str.isdigit():
                    pri = int(pri_str)
                    severity = pri % 8
                    facility = pri // 8
                    return facility, severity, msg[end_idx + 1:].strip()
        # Default fallback
        return 16, 6, msg

    @staticmethod
    def get_severity_name(sev: int) -> str:
        return SEVERITY_NAMES.get(sev, f"Level {sev}")

    @staticmethod
    def get_facility_name(fac: int) -> str:
        return FACILITY_NAMES.get(fac, f"local{fac}")
