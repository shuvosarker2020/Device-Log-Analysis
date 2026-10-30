import argparse
import sys
import uvicorn
from app.config import cfg
from app.database.db import init_db

def main():
    parser = argparse.ArgumentParser(
        description="NetLogIQ - Multi-Vendor Device Syslog Analysis & Alerting System"
    )
    parser.add_argument("--host", default=None, help="Host to bind the web interface")
    parser.add_argument("--port", type=int, default=None, help="Port to bind the web interface (default: 8000)")
    parser.add_argument("--syslog-port", type=int, default=None, help="Port to bind Syslog UDP/TCP (default: 1514)")
    parser.add_argument("--init-only", action="store_true", help="Initialize database tables and exit")
    parser.add_argument("--simulate", action="store_true", help="Preload realistic multi-vendor logs on startup")

    args = parser.parse_args()

    # Initialize Database
    init_db()
    if args.init_only:
        print("[NetLogIQ] Database initialized. Exiting.")
        sys.exit(0)

    # Override config if CLI args passed
    if args.host:
        cfg.set(["server", "host"], args.host)
    if args.port:
        cfg.set(["server", "web_port"], args.port)
    if args.syslog_port:
        cfg.set(["server", "syslog_udp_port"], args.syslog_port)
        cfg.set(["server", "syslog_tcp_port"], args.syslog_port)

    web_host = cfg.get("server", "host", default="0.0.0.0")
    web_port = cfg.get("server", "web_port", default=8000)
    syslog_udp = cfg.get("server", "syslog_udp_port", default=1514)
    syslog_tcp = cfg.get("server", "syslog_tcp_port", default=1514)

    print("=" * 65)
    print("  NETLOGIQ - MULTI-VENDOR DEVICE SYSLOG ANALYZER & ALERTING")
    print("=" * 65)
    print(f"  Web Dashboard:       http://localhost:{web_port}")
    print(f"  Syslog UDP Listener: {web_host}:{syslog_udp}")
    print(f"  Syslog TCP Listener: {web_host}:{syslog_tcp}")
    print(f"  Supported Vendors:   Huawei, Cisco, Juniper, ZTE, Nokia, Generic")
    print(f"  Critical Alerts:     Reboot, PSU Failure, High CPU Spike, Link Down")
    print("=" * 65)

    if args.simulate:
        import asyncio
        from app.simulator.log_generator import simulate_batch
        print("[NetLogIQ] Preloading sample multi-vendor logs...")
        asyncio.run(simulate_batch(count=25))
        print("[NetLogIQ] Preloaded 25 sample logs.")

    # Start Uvicorn server (App lifespan will automatically start syslog server and queue worker)
    uvicorn.run("app.api.app:app", host=web_host, port=web_port, reload=False)

if __name__ == "__main__":
    main()
