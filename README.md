# NetLogIQ - Multi-Vendor Device Syslog Analyzer & Critical Alerting System

**NetLogIQ** is a high-performance, asynchronous syslog collector, multi-vendor normalization engine, and real-time operational analytics dashboard built specifically for telecom and enterprise network devices.

It ingests syslog streams via **UDP & TCP (Port 1514 or 514)** from **Huawei**, **Cisco**, **Juniper**, **ZTE**, **Nokia**, and generic RFC appliances, analyzes them across 4 core operational dimensions, and triggers instant alerts for critical infrastructure events (e.g., **Device Reboot**, **Power Supply (PSU) Failure**, **High CPU Overload**, **Link/BGP Flap**).

---

## 🌟 Key Capabilities

### 1. Multi-Vendor Syslog Normalization
- **Huawei VRP**: Parses `%%ddFACILITY/severity/DIGEST(l)[tag]: message` (e.g. `%%01DEVM/1/POWER_OFF`, `%%01SYS/2/REBOOT`).
- **Cisco IOS/IOS-XE/XR/NX-OS**: Parses `%FACILITY-SEV-MNEMONIC: message` (e.g. `%SYS-5-RELOAD`, `%ENVMON-1-POWER_SUPPLY`, `%SYS-4-CPUMON`).
- **Juniper Junos**: Parses `process[PID]: TAG: message` (e.g. `chassism: CHASSISD_POWER_SUPPLY_FAILED`, `eventd: SYSTEM_REBOOT`).
- **ZTE ZXROS/ZXR10**: Parses `%TAG-SEV-NAME: message` (e.g. `%POWER-1-FAIL`, `%SYS-2-RELOAD`).
- **Nokia SR OS / TiMOS**: Parses `SUBSYSTEM-SEV-EVENTID: message` (e.g. `SYSTEM-CRITICAL-1002`, `SYSTEM-WARNING-2005`).
- **Generic / RFC 3164 / RFC 5424**: Automatic PRI calculation, facility/severity decomposition, and host resolution.

### 2. Multi-Dimensional Analytics Engine
- **Device-Wise**: Track top error-generating hostnames, total logs, active alerts, and last-seen timestamps.
- **IP-Wise**: Identify noisy source IPs, IP-to-device mappings, and error ratios.
- **Severity-Wise**: Real-time breakdown across RFC 5424 severities (0 Emergency -> 7 Debug).
- **Error & Event Classification**: Automatic classification into categories:
  - ⚡ `REBOOT` (Device reloads, kernel panics, warm/cold boots)
  - 🔋 `POWER_SUPPLY` (PSU failures, power cuts, redundancy lost)
  - 🔥 `HIGH_CPU` (CPU threshold overload, processor spikes)
  - ❄️ `FAN_TEMPERATURE` (Cooling fan stop, thermal alarms)
  - 🔌 `INTERFACE_DOWN` (Physical link down, line protocol loss)
  - 🌐 `BGP_OSPF` (Routing adjacency drop, hold-timer expired)
  - 🔒 `SECURITY` (Failed logins, authentication violations)

### 3. Critical Alerting & Notifications
- **Deduplication & Cooldown**: Smart throttling suppresses duplicate alert storms during device reboot loops.
- **Notification Channels**:
  - 📱 **Telegram Bot**: Formatted markdown messages sent directly to your NOC group/channel.
  - 💬 **Slack / Discord / MS Teams**: Webhook rich cards with color badges and device details.
  - 📧 **SMTP Email**: Responsive HTML email notifications with error details.
  - 🔔 **Real-Time Web UI Alerts**: WebSocket live toast alerts with audio alert sound.

### 4. High-Performance Architecture
- **Asynchronous Decoupled Ingestion**: Network UDP/TCP listener puts logs into an async queue (`asyncio.Queue`) so network buffers never drop packets even at high speeds.
- **Optimized SQLite with WAL**: Composite indexing on `(source_ip)`, `(hostname)`, `(severity)`, `(timestamp)` with Write-Ahead Logging (`WAL`).

### 5. Multi-Theme & Color Visibility Engine
- 🌙 **Dark NOC (Default)**: Deep midnight slate theme designed for command centers.
- ☀️ **Light Enterprise**: High-contrast, clean day mode with crisp dark typography for bright office/day environments.
- 🌊 **Ocean Blue**: Deep navy blue palette tailored for telecom NOCs.
- ⚡ **Cyber High-Contrast**: Electric neon on jet black for maximum glanceability from across control rooms.
- **Persistent & Reactive**: Persists your theme in `localStorage` and automatically updates Chart.js axes and legends.

---

## 🚀 Quick Start

### 1. Installation
Ensure Python 3.10+ is installed:
```bash
pip install -r requirements.txt
```

### 2. Start the Application
Run the launcher:
```bash
# Start server with sample logs preloaded
python run.py --simulate

# Or start clean server:
python run.py
```

- **Web Dashboard**: [http://localhost:8000](http://localhost:8000)
- **Syslog UDP Listener**: `0.0.0.0:1514`
- **Syslog TCP Listener**: `0.0.0.0:1514`

*(To listen on standard port 514 on Windows or Linux, specify `python run.py --syslog-port 514` with Administrator/root privileges).*

---

## 📡 Device Configuration Examples

Configure your routers and switches to forward syslog messages to NetLogIQ (replace `<NETLOG_IP>` with the IP of your analysis server):

### Cisco (IOS / IOS-XE / XR / NX-OS)
```cisco
logging host <NETLOG_IP> transport udp port 1514
logging trap informational
logging facility local7
logging source-interface GigabitEthernet0/0/0
```

### Huawei (VRP / NE40E / CloudEngine / S5700)
```huawei
info-center enable
info-center loghost <NETLOG_IP> port 1514 facility local7
info-center source default channel 2 log level informational
```

### Juniper (Junos)
```junos
set system syslog host <NETLOG_IP> port 1514 any any
set system syslog host <NETLOG_IP> match-strings ".*"
```

### ZTE (ZXROS / ZXR10)
```zte
logging host <NETLOG_IP> port 1514
logging level informational
```

### Nokia (SR OS / 7750 SR)
```nokia
configure log sys-log-server <NETLOG_IP> port 1514
configure log log-id 10 from main change to sys-log-server
```

---

## 🧪 Built-In Multi-Vendor Simulator

NetLogIQ includes a test console and simulation generator:
1. Navigate to the **Multi-Vendor Simulator** tab in the web UI.
2. Click **PSU Power Failure**, **Device Reboot**, or **High CPU Spike** to simulate instant real-world faults.
3. Test custom device raw strings directly using the manual syslog analyzer box.
4. Or trigger UDP packets directly via CLI:
```bash
python -c "from app.simulator.log_generator import send_udp_syslog; send_udp_syslog(port=1514, count=10)"
```

---

## ⚙️ Configuration (`config.yaml`)

Configuration can be edited directly via `config.yaml` or updated dynamically from the **Notifications & Config** tab in the Web UI:

```yaml
server:
  host: "0.0.0.0"
  web_port: 8000
  syslog_udp_port: 1514
  syslog_tcp_port: 1514

alerts:
  cooldown_seconds: 60    # Cooldown window to prevent alert storm

notifications:
  telegram:
    enabled: true
    bot_token: "123456789:ABCdef..."
    chat_id: "-100123456789"
  
  slack:
    enabled: true
    webhook_url: "https://hooks.slack.com/services/..."
    channel: "#network-alerts"

  email:
    enabled: false
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    to_emails: ["noc-team@company.com"]
```

---

## 📊 REST API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/stats/summary` | GET | Total logs, active alerts, device counts, critical errors |
| `/api/stats/severity` | GET | Breakdown of logs by severity (0-7) |
| `/api/stats/devices` | GET | Device-wise error and alert analytics |
| `/api/stats/ips` | GET | IP-wise log and error metrics |
| `/api/stats/categories`| GET | Error category counts (Reboots, PSU, CPU, Fans) |
| `/api/stats/timeline` | GET | 24-hour log volume and error trends |
| `/api/logs` | GET | Filterable and searchable paginated logs |
| `/api/logs/ingest` | POST | Ingest raw syslog via HTTP JSON |
| `/api/alerts` | GET | List active or acknowledged critical alerts |
| `/api/alerts/{id}/acknowledge` | POST | Acknowledge active alert |
| `/api/simulate` | POST | Trigger mock log generation |
| `/api/config/notifications` | POST | Update Telegram/Slack/Email settings |
| `/api/config/test-notification` | POST | Send live test alert |
