import re
from typing import List, Dict, Any, Optional

class AlertRule:
    def __init__(
        self,
        name: str,
        category: str,
        pattern: str,
        severity_override: Optional[int] = None,
        description: str = "",
        is_critical: bool = True
    ):
        self.name = name
        self.category = category  # REBOOT, POWER_SUPPLY, HIGH_CPU, FAN_FAILURE, TEMPERATURE, INTERFACE_DOWN, BGP_FLAP, SECURITY
        self.regex = re.compile(pattern, re.IGNORECASE)
        self.severity_override = severity_override
        self.description = description
        self.is_critical = is_critical

    def matches(self, full_text: str) -> bool:
        return bool(self.regex.search(full_text))

# Built-in multi-vendor rule sets
DEFAULT_RULES: List[AlertRule] = [
    # 1. Device Reboot & Crash
    AlertRule(
        name="Device Reboot Detected",
        category="REBOOT",
        pattern=r"(%SYS-[0-7]-RELOAD|%SYS-[0-7]-REBOOT|SYSTEM_REBOOT|%%01SYS/[0-7]/REBOOT|SYSTEM-WARNING-2005|%SYS-2-RELOAD|reload requested|system restart|cold start|warm start|kernel panic|system is rebooting|reboot initiated|system is going to reboot|CHASSISD_REBOOT|CRASH_DUMP)",
        severity_override=1,  # Alert / Critical
        description="Device reboot or unexpected restart detected",
        is_critical=True
    ),
    
    # 2. Power Supply Unit (PSU) Issue
    AlertRule(
        name="Power Supply (PSU) Failure",
        category="POWER_SUPPLY",
        pattern=r"(%ENVMON-[0-7]-POWER_SUPPLY|%PLATFORM_ENV-[0-7]-PWR|DEVM/[0-7]/POWER_OFF|CHASSISD_POWER_SUPPLY_FAILED|%POWER-[0-7]-FAIL|SYSTEM-CRITICAL-1002|power supply.*fail|power supply.*down|power supply.*off|redundant power lost|psu.*fault|power module.*abnormal|power supply.*removed)",
        severity_override=1,
        description="Power supply unit failed, powered off, or redundant power lost",
        is_critical=True
    ),

    # 3. High CPU Utilization
    AlertRule(
        name="High CPU Utilization",
        category="HIGH_CPU",
        pattern=r"(%SYS-[0-7]-CPUMON|%CPUMON-[0-7]-HIGH_CPU|CPU_OVERLOAD|CHASSISD_CPU_UTIL_HIGH|%DEV-[0-7]-CPU_HIGH|SYSTEM-MAJOR-1014|high cpu utilization|cpu usage exceeds|cpu overload|host cpu utilization.*exceeds|cpm slot.*high cpu)",
        severity_override=2,
        description="High CPU threshold exceeded on device processor/controller",
        is_critical=True
    ),

    # 4. Fan Failure & Thermal Alarms
    AlertRule(
        name="Fan or Thermal Alarm",
        category="FAN_TEMPERATURE",
        pattern=r"(%ENVMON-[0-7]-FAN|DEVM/[0-7]/FAN_FAILED|CHASSISD_FAN_FAILURE|CHASSISD_BLOWER_FAILURE|%FAN-[0-7]-FAIL|CHASSIS-CRITICAL-1005|fan.*fail|fan tray.*failed|fan stopped|temperature.*exceed|temperature critical|high temperature alarm)",
        severity_override=2,
        description="Cooling fan failure or high temperature alarm detected",
        is_critical=True
    ),

    # 5. Interface Link Down
    AlertRule(
        name="Interface Link Down",
        category="INTERFACE_DOWN",
        pattern=r"(%LINK-[0-7]-UPDOWN:.*state to down|%LINEPROTO-[0-7]-UPDOWN:.*state to down|IFNET/[0-7]/LINK_DOWN|SNMP_TRAP_LINK_DOWN|%PORT-[0-7]-LINKDOWN|PORT-MAJOR-2001:.*operational down|interface.*changed state to down)",
        severity_override=3,
        description="Physical network interface or line protocol transitioned to DOWN state",
        is_critical=False
    ),

    # 6. BGP / Routing Flap
    AlertRule(
        name="BGP Routing Flap",
        category="BGP_OSPF",
        pattern=r"(%BGP-[0-7]-ADJCHANGE|%BGP-[0-7]-NOTIFICATION|BGP/[0-7]/STATE_CHANGE|RPD_BGP_NEIGHBOR_STATE_CHANGED|ROUTING-WARNING-3001|bgp peer.*down|bgp.*hold timer expired|ospf.*from full to down)",
        severity_override=3,
        description="BGP peering or OSPF neighbor adjacency dropped",
        is_critical=False
    ),

    # 7. Hardware & Memory Faults
    AlertRule(
        name="Hardware / Memory Fault",
        category="HARDWARE_FAULT",
        pattern=r"(ECC_ERROR|MEMORY_OVERLOAD|OUT_OF_MEMORY|HARDWARE_FAULT|CHASSISD_CARD_FAILED|SLOT_FAIL|PARITY_ERROR|CHASSIS-MAJOR-1001)",
        severity_override=2,
        description="Hardware component or ECC memory parity failure",
        is_critical=True
    ),

    # 8. Security & Authentication Failure
    AlertRule(
        name="Authentication Failure / Security Alert",
        category="SECURITY",
        pattern=r"(%SEC_LOGIN-[0-7]-LOGIN_FAILED|SSH_AUTH_FAIL|authentication failure|failed password for|login failed for user|unauthorized access denied)",
        severity_override=3,
        description="Security event or repeated authentication failure",
        is_critical=False
    ),
]
