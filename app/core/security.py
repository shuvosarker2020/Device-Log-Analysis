import ipaddress
import logging
from typing import List, Dict, Any
from collections import deque
from app.config import cfg

logger = logging.getLogger("NetLogIQ.Security")

# In-memory metrics for blocked unauthorized attempts
_blocked_attempts_count = 0
_recent_blocked_ips: deque = deque(maxlen=50)

def _normalize_ip(ip_str: str) -> str:
    """Strip whitespace and unwrap IPv4-mapped IPv6 addresses like ::ffff:10.0.0.1."""
    ip_str = ip_str.strip()
    try:
        addr = ipaddress.ip_address(ip_str)
        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
            return str(addr.ipv4_mapped)
        return str(addr)
    except ValueError:
        return ip_str

def is_ip_allowed(source_ip: str, record_block: bool = True) -> bool:
    """
    Check if a source IP address is permitted to submit syslogs based on
    the security prefix/CIDR whitelist configuration.
    """
    global _blocked_attempts_count
    sec = cfg.get("security", default={})

    if not sec.get("enable_ip_whitelist", True):
        return True

    norm_ip = _normalize_ip(source_ip)

    # Allow localhost / loopback for local health checks and simulations
    if norm_ip in ("127.0.0.1", "::1", "localhost"):
        return True

    allowed = sec.get("allowed_device_ips", [])
    # Strict mode: if whitelist is enabled and list is empty, block all external IPs
    if not allowed:
        if record_block:
            _record_blocked(norm_ip)
        return False

    if "*" in allowed:
        return True

    try:
        src_addr = ipaddress.ip_address(norm_ip)
    except ValueError:
        logger.warning(f"[Security] Invalid IP address format: {source_ip}")
        if record_block:
            _record_blocked(norm_ip)
        return False

    for entry in allowed:
        entry = str(entry).strip()
        if not entry:
            continue
        try:
            # Support wildcard/prefix shorthand like "10.10.*" or "192.168.1."
            if entry.endswith(".*") or entry.endswith("."):
                prefix = entry.rstrip("*")
                if norm_ip.startswith(prefix):
                    return True
            elif "/" in entry:
                net = ipaddress.ip_network(entry, strict=False)
                if src_addr in net:
                    return True
            else:
                if src_addr == ipaddress.ip_address(entry):
                    return True
        except ValueError:
            logger.warning(f"[Security] Malformed allowed IP/prefix entry: {entry}")
            continue

    if record_block:
        _record_blocked(norm_ip)
    return False

def _record_blocked(ip: str):
    global _blocked_attempts_count
    _blocked_attempts_count += 1
    if ip not in _recent_blocked_ips:
        _recent_blocked_ips.appendleft(ip)

def get_security_stats() -> Dict[str, Any]:
    return {
        "blocked_count": _blocked_attempts_count,
        "recent_blocked_ips": list(_recent_blocked_ips)
    }
