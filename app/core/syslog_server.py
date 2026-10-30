import asyncio
import logging
from typing import Optional
from app.config import cfg
from app.core.queue_worker import log_queue

logger = logging.getLogger("NetLogIQ.SyslogServer")

class SyslogUDPProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        super().__init__()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        source_ip = addr[0]
        try:
            # Handle UTF-8 and fallback to Latin-1
            try:
                message = data.decode("utf-8")
            except UnicodeDecodeError:
                message = data.decode("latin-1", errors="replace")

            # A single UDP packet may contain multiple lines
            for line in message.splitlines():
                line = line.strip()
                if line:
                    try:
                        log_queue.put_nowait((line, source_ip))
                    except asyncio.QueueFull:
                        logger.warning(f"[SyslogUDP] Queue full! Dropping log from {source_ip}")
        except Exception as e:
            logger.error(f"[SyslogUDP] Error receiving datagram from {addr}: {e}")

async def handle_tcp_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info("peername")
    source_ip = peer[0] if peer else "unknown"
    buffer = ""
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            try:
                chunk = data.decode("utf-8")
            except UnicodeDecodeError:
                chunk = data.decode("latin-1", errors="replace")

            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if line:
                    try:
                        log_queue.put_nowait((line, source_ip))
                    except asyncio.QueueFull:
                        logger.warning(f"[SyslogTCP] Queue full! Dropping log from {source_ip}")
    except Exception as e:
        logger.debug(f"[SyslogTCP] Connection closed with {source_ip}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

class SyslogServer:
    def __init__(self):
        self.udp_transport = None
        self.tcp_server = None
        self.host = cfg.get("server", "host", default="0.0.0.0")
        self.udp_port = cfg.get("server", "syslog_udp_port", default=1514)
        self.tcp_port = cfg.get("server", "syslog_tcp_port", default=1514)
        self.enable_udp = cfg.get("server", "enable_udp", default=True)
        self.enable_tcp = cfg.get("server", "enable_tcp", default=True)

    async def start(self):
        loop = asyncio.get_running_loop()

        # Start UDP listener
        if self.enable_udp:
            try:
                self.udp_transport, _ = await loop.create_datagram_endpoint(
                    lambda: SyslogUDPProtocol(),
                    local_addr=(self.host, self.udp_port)
                )
                logger.info(f"[SyslogServer] UDP Syslog listening on {self.host}:{self.udp_port}")
            except Exception as e:
                logger.error(f"[SyslogServer] Failed to bind UDP port {self.udp_port}: {e}")

        # Start TCP listener
        if self.enable_tcp:
            try:
                self.tcp_server = await asyncio.start_server(
                    handle_tcp_client,
                    host=self.host,
                    port=self.tcp_port
                )
                logger.info(f"[SyslogServer] TCP Syslog listening on {self.host}:{self.tcp_port}")
            except Exception as e:
                logger.error(f"[SyslogServer] Failed to bind TCP port {self.tcp_port}: {e}")

    async def stop(self):
        if self.udp_transport:
            self.udp_transport.close()
            logger.info("[SyslogServer] UDP server stopped.")
        if self.tcp_server:
            self.tcp_server.close()
            await self.tcp_server.wait_closed()
            logger.info("[SyslogServer] TCP server stopped.")

syslog_server = SyslogServer()
