"""Network monitoring implementation."""
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import subprocess
import platform
from scapy.all import sniff, IP
from typing import Dict, Set, List
import ipaddress

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import MODE_LIGHTWEIGHT, MODE_INTENSIVE

_LOGGER = logging.getLogger(__name__)

class NetworkMonitor:
    """Base class for network monitoring."""
    def __init__(self, hass: HomeAssistant, threat_ips: Set[str]):
        self.hass = hass
        self.threat_ips = threat_ips
        self.suspicious_activity = defaultdict(list)

    async def start_monitoring(self):
        """Start monitoring - to be implemented by subclasses."""
        raise NotImplementedError()

    async def stop_monitoring(self):
        """Stop monitoring - to be implemented by subclasses."""
        raise NotImplementedError()

class LightweightMonitor(NetworkMonitor):
    """Lightweight network monitoring using netstat."""
    
    async def get_connections(self):
        """Get current network connections using netstat."""
        connections = {}
        
        def _run_netstat():
            if platform.system() == "Windows":
                cmd = ["netstat", "-n"]
            else:
                cmd = ["netstat", "-n", "-t"]
            
            try:
                output = subprocess.check_output(cmd, universal_newlines=True)
                return output
            except subprocess.CalledProcessError as e:
                _LOGGER.error(f"Error running netstat: {e}")
                return ""

        output = await self.hass.async_add_executor_job(_run_netstat)
        
        for line in output.splitlines():
            try:
                if "ESTABLISHED" in line or "SYN_SENT" in line:
                    parts = line.split()
                    local_addr = parts[3].split(":")[0]
                    remote_addr = parts[4].split(":")[0]
                    
                    if (not ipaddress.ip_address(remote_addr).is_private and
                        not ipaddress.ip_address(remote_addr).is_loopback):
                        connections[remote_addr] = {
                            "local_addr": local_addr,
                            "timestamp": datetime.now().isoformat()
                        }
            except (ValueError, IndexError):
                continue
                
        return connections

    async def start_monitoring(self):
        """Start monitoring - nothing to do for netstat mode."""
        pass

    async def stop_monitoring(self):
        """Stop monitoring - nothing to do for netstat mode."""
        pass

class IntensiveMonitor(NetworkMonitor):
    """Intensive network monitoring using packet sniffing."""
    
    def __init__(self, hass: HomeAssistant, threat_ips: Set[str]):
        super().__init__(hass, threat_ips)
        self._running = False
        self._sniffer = None
        self.connections = {}

    def packet_callback(self, packet):
        """Process each packet."""
        if IP in packet and self._running:
            src_ip = packet[IP].src
            dst_ip = packet[IP].dst
            
            if not ipaddress.ip_address(dst_ip).is_private:
                self.connections[dst_ip] = {
                    "local_addr": src_ip,
                    "timestamp": datetime.now().isoformat()
                }

    async def start_monitoring(self):
        """Start packet sniffing."""
        self._running = True
        
        def start_sniff():
            self._sniffer = sniff(
                filter="ip",
                prn=self.packet_callback,
                store=0,
                stop_filter=lambda _: not self._running
            )

        await self.hass.async_add_executor_job(start_sniff)

    async def stop_monitoring(self):
        """Stop packet sniffing."""
        self._running = False
        if self._sniffer:
            self._sniffer.stop()

class NetworkSecurityCoordinator(DataUpdateCoordinator):
    """Coordinator to handle updates and monitoring."""

    def __init__(self, hass: HomeAssistant, monitor_mode: str, scan_interval: int):
        super().__init__(
            hass,
            _LOGGER,
            name="Network Security Monitor",
            update_interval=timedelta(minutes=scan_interval),
        )
        self.monitor_mode = monitor_mode
        self.threat_ips: Set[str] = set()
        self.suspicious_activity = defaultdict(list)
        self.monitor = None

    async def initialize_monitor(self):
        """Initialize the appropriate monitor based on mode."""
        if self.monitor_mode == MODE_LIGHTWEIGHT:
            self.monitor = LightweightMonitor(self.hass, self.threat_ips)
        else:
            self.monitor = IntensiveMonitor(self.hass, self.threat_ips)
        
        await self.monitor.start_monitoring()

    async def _async_update_data(self):
        """Update data from the selected monitor."""
        if self.monitor_mode == MODE_LIGHTWEIGHT:
            connections = await self.monitor.get_connections()
        else:
            connections = self.monitor.connections

        # Analyze connections
        new_alerts = []
        for remote_ip, conn_info in connections.items():
            if remote_ip in self.threat_ips:
                alert = {
                    "ip": remote_ip,
                    "local_addr": conn_info["local_addr"],
                    "timestamp": conn_info["timestamp"],
                    "type": "Known malicious IP"
                }
                self.suspicious_activity[remote_ip].append(alert)
                new_alerts.append(alert)

        return {
            "alerts": new_alerts,
            "total_monitored": len(connections),
            "suspicious_count": len(self.suspicious_activity),
            "last_updated": datetime.now().isoformat(),
            "monitor_mode": self.monitor_mode
        }
