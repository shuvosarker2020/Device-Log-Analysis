import ipaddress
import logging
from typing import List
from app.config import cfg

logger = logging.getLogger("NetLogIQ.Security")

def is_ip_allowed(source_ip: str) -> bool:
    """
    Check if a source IP address is permitted to submit syslogs based on
    the security configuration.
    """
    sec = cfg.get("security", default={})
    if not sec.get("enable_ip_whitelist", False):
        return True

    allowed = sec.get("allowed_device_ips", [])
    if not allowed or "*" in allowed:
        return True

    # Allow localhost / loopback for health checks and local simulations
    if source_ip in ["127.0.0.1", "::1", "localhost"]:
        return True

    try:
        src_addr = ipaddress.ip_address(source_ip)
    except ValueError:
        logger.warning(f"[Security] Invalid IP address format: {source_ip}")
        return False

    for entry in allowed:
        entry = str(entry).strip()
        if not entry:
            continue
        try:
            if "/" in entry:
                if src_addr in ipaddress.ip_network(entry, strict=False):
                    return True
            else:
                if src_addr == ipaddress.ip_address(entry):
                    return True
        except ValueError:
            logger.warning(f"[Security] Malformed allowed IP/subnet entry: {entry}")
            continue

    return False
