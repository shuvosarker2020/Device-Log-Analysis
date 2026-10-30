import random
import socket
import time
from datetime import datetime, timezone
from typing import List, Dict, Any
from app.core.queue_worker import process_log_pipeline

# Preset multi-vendor device mock inventories
MOCK_DEVICES = [
    # Cisco Devices
    {"ip": "10.100.1.1", "host": "Core-R1-Cisco-ASR9k", "vendor": "Cisco"},
    {"ip": "10.100.1.2", "host": "Dist-SW1-Cisco-Catalyst", "vendor": "Cisco"},
    {"ip": "10.100.1.3", "host": "DC-Spine-Cisco-Nexus", "vendor": "Cisco"},

    # Huawei Devices
    {"ip": "10.100.2.1", "host": "Edge-NE40E-Huawei-01", "vendor": "Huawei"},
    {"ip": "10.100.2.2", "host": "Aggr-CE6800-Huawei-02", "vendor": "Huawei"},
    {"ip": "10.100.2.3", "host": "Access-S5700-Huawei-03", "vendor": "Huawei"},

    # Juniper Devices
    {"ip": "10.100.3.1", "host": "Core-MX960-Juniper-01", "vendor": "Juniper"},
    {"ip": "10.100.3.2", "host": "DC-QFX5100-Juniper-02", "vendor": "Juniper"},
    {"ip": "10.100.3.3", "host": "FW-SRX300-Juniper-03", "vendor": "Juniper"},

    # ZTE Devices
    {"ip": "10.100.4.1", "host": "OLT-C300-ZTE-01", "vendor": "ZTE"},
    {"ip": "10.100.4.2", "host": "Router-M6000-ZTE-02", "vendor": "ZTE"},
    {"ip": "10.100.4.3", "host": "Metro-ZXR10-ZTE-03", "vendor": "ZTE"},

    # Nokia Devices
    {"ip": "10.100.5.1", "host": "PE-7750SR-Nokia-01", "vendor": "Nokia"},
    {"ip": "10.100.5.2", "host": "IXR-7250-Nokia-02", "vendor": "Nokia"},
]

# Vendor-specific log templates
SAMPLE_LOG_TEMPLATES = {
    "Cisco": [
        # Critical Alert scenarios
        ("<187>Oct 15 11:20:10.123 {host}: %SYS-5-RELOAD: Reload requested by vty0 (user admin, cold reboot)", "REBOOT"),
        ("<185>Oct 15 11:21:05.456 {host}: %ENVMON-1-POWER_SUPPLY: Power supply 1 failed! Redundant power lost", "POWER_SUPPLY"),
        ("<188>Oct 15 11:22:12.789 {host}: %SYS-4-CPUMON: High CPU utilization detected: 96% for 5 mins (process: BGP Router)", "HIGH_CPU"),
        ("<185>Oct 15 11:22:45.111 {host}: %ENVMON-1-FAN_FAILED: Fan Module 2 failure detected! RPM below threshold", "FAN_TEMPERATURE"),
        # Operational scenarios
        ("<187>Oct 15 11:23:45.012 {host}: %LINK-3-UPDOWN: Interface GigabitEthernet0/0/1, changed state to down", "INTERFACE_DOWN"),
        ("<189>Oct 15 11:24:00.000 {host}: %BGP-5-ADJCHANGE: neighbor 10.200.1.5 Down Hold Timer Expired", "BGP_OSPF"),
        ("<190>Oct 15 11:25:30.222 {host}: %SEC_LOGIN-5-LOGIN_SUCCESS: Login Success [user: netadmin] [Source: 192.168.1.100]", "SECURITY"),
        ("<190>Oct 15 11:26:00.333 {host}: %SYS-6-LOGGINGHOST_STARTSTOP: Logging to host 10.10.10.50 started", "GENERAL"),
    ],
    "Huawei": [
        # Critical Alert scenarios
        ("<186>Oct 15 2026 11:25:00 {host} %%01SYS/2/REBOOT(l)[15]: System is going to reboot by admin command.", "REBOOT"),
        ("<185>Oct 15 2026 11:26:10 {host} %%01DEVM/1/POWER_OFF(l)[12]: The power supply 1 was powered off. Redundancy lost.", "POWER_SUPPLY"),
        ("<188>Oct 15 2026 11:27:00 {host} %%01SYSTEM/4/CPU_OVERLOAD(l)[20]: CPU usage exceeds the threshold (94% > 80%).", "HIGH_CPU"),
        ("<185>Oct 15 2026 11:28:15 {host} %%01DEVM/1/FAN_FAILED(l)[25]: Fan module 2 failed or RPM abnormal.", "FAN_TEMPERATURE"),
        # Operational scenarios
        ("<187>Oct 15 2026 11:29:00 {host} %%01IFNET/3/LINK_DOWN(l)[22]: Interface 10GE1/0/1 turned into DOWN state.", "INTERFACE_DOWN"),
        ("<187>Oct 15 2026 11:30:10 {host} %%01BGP/3/STATE_CHANGE(l)[33]: The BGP peer 10.1.1.2 changed state from ESTABLISHED to IDLE.", "BGP_OSPF"),
        ("<190>Oct 15 2026 11:31:00 {host} %%01SHELL/6/USERLOGIN(l)[44]: User admin logged in from 10.5.0.2 via SSH.", "SECURITY"),
        ("<190>Oct 15 2026 11:32:00 {host} %%01NTP/6/SYNC(l)[50]: System clock synchronized with NTP server 10.0.0.1.", "GENERAL"),
    ],
    "Juniper": [
        # Critical Alert scenarios
        ("<186>Oct 15 11:31:00 {host} eventd[1200]: SYSTEM_REBOOT: Reboot initiated by user 'root' via CLI", "REBOOT"),
        ("<185>Oct 15 11:30:00 {host} chassism[2841]: CHASSISD_POWER_SUPPLY_FAILED: Power Supply 0 failure, DC feed cut", "POWER_SUPPLY"),
        ("<188>Oct 15 11:32:00 {host} chassisd[1902]: CHASSISD_CPU_UTIL_HIGH: Host CPU utilization 95% exceeds threshold 85%", "HIGH_CPU"),
        ("<185>Oct 15 11:32:30 {host} chassisd[2100]: CHASSISD_FAN_FAILURE: Fan Tray 1 failed or missing", "FAN_TEMPERATURE"),
        # Operational scenarios
        ("<187>Oct 15 11:33:00 {host} mib2d[2900]: SNMP_TRAP_LINK_DOWN: ifIndex 543, ifAdminStatus up(1), ifOperStatus down(2), ifName ge-0/0/0", "INTERFACE_DOWN"),
        ("<187>Oct 15 11:33:45 {host} rpd[4210]: RPD_BGP_NEIGHBOR_STATE_CHANGED: BGP peer 10.10.10.1 changed state from Established to Idle", "BGP_OSPF"),
        ("<190>Oct 15 11:34:20 {host} mgd[1500]: UI_AUTH_EVENT: Authenticated user 'operator' successfully from 192.168.10.22", "SECURITY"),
        ("<190>Oct 15 11:35:00 {host} snmpd[1122]: SNMPD_AUTH_FAILURE: SNMP authentication failure from 192.168.99.1", "GENERAL"),
    ],
    "ZTE": [
        # Critical Alert scenarios
        ("<186>Oct 15 11:35:00 {host} %SYS-2-RELOAD: System is reloading by command line from admin terminal.", "REBOOT"),
        ("<185>Oct 15 11:34:00 {host} %POWER-1-FAIL: Power Supply Unit 2 output failure, voltage dropped below limit.", "POWER_SUPPLY"),
        ("<188>Oct 15 11:36:00 {host} %DEV-4-CPU_HIGH: Slot 1 CPU usage is high: 93% for 180s.", "HIGH_CPU"),
        ("<185>Oct 15 11:36:30 {host} %FAN-1-FAIL: Fan unit 1 stopped working or abnormal speed.", "FAN_TEMPERATURE"),
        # Operational scenarios
        ("<187>Oct 15 11:37:00 {host} %PORT-3-LINKDOWN: Port gei_1/1 is down, link pulse absent.", "INTERFACE_DOWN"),
        ("<187>Oct 15 11:37:45 {host} %BGP-3-PEER_DOWN: Peer 192.168.10.1 is DOWN, HoldTimer Expired.", "BGP_OSPF"),
        ("<190>Oct 15 11:38:00 {host} %SEC-6-LOGIN: User zteadmin login succeeded via Telnet/SSH.", "SECURITY"),
        ("<190>Oct 15 11:39:00 {host} %SYSTEM-6-CONFIG: Configuration committed to flash memory.", "GENERAL"),
    ],
    "Nokia": [
        # Critical Alert scenarios
        ("<186>Oct 15 11:39:00 {host} SYSTEM-WARNING-2005: Reboot initiated from CLI by admin", "REBOOT"),
        ("<185>Oct 15 11:38:00 {host} SYSTEM-CRITICAL-1002: Base Chassis Power Supply 1 Failed or Removed", "POWER_SUPPLY"),
        ("<188>Oct 15 11:40:00 {host} SYSTEM-MAJOR-1014: High CPU threshold exceeded on CPM slot A (95%)", "HIGH_CPU"),
        ("<185>Oct 15 11:40:40 {host} CHASSIS-CRITICAL-1005: Fan Tray 1 has failed, chassis cooling impaired", "FAN_TEMPERATURE"),
        # Operational scenarios
        ("<187>Oct 15 11:41:00 {host} PORT-MAJOR-2001: Port 1/1/c1/1 is operational down", "INTERFACE_DOWN"),
        ("<187>Oct 15 11:41:45 {host} ROUTING-WARNING-3001: BGP neighbor 192.168.100.2 session terminated", "BGP_OSPF"),
        ("<190>Oct 15 11:42:00 {host} SECURITY-INFO-4001: CLI login successful for admin via SSH", "SECURITY"),
        ("<190>Oct 15 11:43:00 {host} SYSTEM-INFO-1001: System time synchronized successfully", "GENERAL"),
    ]
}

def generate_sample_log(vendor: str = None, scenario: str = None) -> tuple:
    """Generate a single sample log (raw_message, source_ip, hostname, vendor)"""
    if vendor and vendor in SAMPLE_LOG_TEMPLATES:
        dev_candidates = [d for d in MOCK_DEVICES if d["vendor"].lower() == vendor.lower()]
    else:
        dev_candidates = MOCK_DEVICES

    device = random.choice(dev_candidates)
    dev_vendor = device["vendor"]
    templates = SAMPLE_LOG_TEMPLATES[dev_vendor]

    if scenario:
        filtered = [t for t in templates if t[1] == scenario]
        if filtered:
            chosen_tmpl = random.choice(filtered)[0]
        else:
            chosen_tmpl = random.choice(templates)[0]
    else:
        chosen_tmpl = random.choice(templates)[0]

    raw_msg = chosen_tmpl.format(host=device["host"])
    return raw_msg, device["ip"], device["host"], dev_vendor

async def simulate_batch(count: int = 15, vendor: str = None, scenario: str = None) -> List[dict]:
    """Inject a batch of logs directly through the processing pipeline"""
    results = []
    for _ in range(count):
        raw_msg, ip, host, vend = generate_sample_log(vendor=vendor, scenario=scenario)
        log, alert = await process_log_pipeline(raw_msg, ip)
        results.append({
            "log": log.model_dump(mode="json"),
            "alert": alert.model_dump(mode="json") if alert else None
        })
    return results

def send_udp_syslog(target_host: str = "127.0.0.1", port: int = 1514, count: int = 5, vendor: str = None):
    """Send real UDP packets to the syslog port"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for _ in range(count):
        raw_msg, ip, host, vend = generate_sample_log(vendor=vendor)
        sock.sendto(raw_msg.encode("utf-8"), (target_host, port))
        time.sleep(0.05)
    sock.close()
