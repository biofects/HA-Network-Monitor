ha_network_monitor/const.py                                                                         0000644 0000000 0000000 00000000746 14753455224 015206  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   """Constants for HA Network Monitor."""
DOMAIN = "ha_network_monitor"
THREAT_FEED_URL = "https://feodotracker.abuse.ch/downloads/ipblocklist.txt"
PRIVATE_IP_RANGES = [
    "192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25."
]

# Monitor modes
MODE_LIGHTWEIGHT = "lightweight"
MODE_INTENSIVE = "intensive"

MONITOR_MODES = [
    MODE_LIGHTWEIGHT,
    MODE_INTENSIVE
]

DEFAULT_SCAN_INTERVAL = 15  # minutes
                          ha_network_monitor/__init__.py                                                                      0000644 0000000 0000000 00000002106 14753454214 015605  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   """Home Assistant component for monitoring network traffic."""
import asyncio
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the HA Network Monitor component."""
    hass.data[DOMAIN] = {}
    _LOGGER.info("HA Network Monitor Component Loaded")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the integration from UI configuration."""
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
                                                                                                                                                                                                                                                                                                                                                                                                                                                          ha_network_monitor/manifest.json                                                                    0000644 0000000 0000000 00000000521 14753455407 016201  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   {
  "domain": "ha_network_monitor",
  "name": "HA Network Monitor",
  "config_flow": true,
  "version": "1.0.0",
  "documentation": "https://github.com/biofects/HA-Network_Monitor",
  "dependencies": [],
  "codeowners": ["@biofects"],
  "requirements": [
    "scapy",
    "aiohttp",
    "ipaddress"
  ],
  "iot_class": "local_polling"
}
                                                                                                                                                                               ha_network_monitor/monitor.py                                                                       0000644 0000000 0000000 00000013666 14753455263 015557  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   """Network monitoring implementation."""
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
                                                                          ha_network_monitor/__pycache__/                                                                     0000755 0000000 0000000 00000000000 14753455456 015716  5                                                                                                    ustar   root                            root                                                                                                                                                                                                                   ha_network_monitor/__pycache__/monitor.cpython-313.pyc                                              0000644 0000000 0000000 00000023017 14753455456 022114  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   �
    �Z�g�  �                   �  � S r SSKrSSKrSSKrSSKJrJr  SSKJr  SSKrSSK	r	SSK
JrJr  SSKJrJrJr  SSKrSSKJr  SSKJr  S	S
KJrJr  \R2                  " \5      r " S S5      r " S S\5      r " S S\5      r " S S\5      rg)z"Network monitoring implementation.�    N)�datetime�	timedelta)�defaultdict)�sniff�IP)�Dict�Set�List)�HomeAssistant)�DataUpdateCoordinator�   )�MODE_LIGHTWEIGHT�MODE_INTENSIVEc                   �<   � \ rS rSrSrS\S\\   4S jrS r	S r
Srg	)
�NetworkMonitor�   z"Base class for network monitoring.�hass�
threat_ipsc                 �D   � Xl         X l        [        [        5      U l        g �N)r   r   r   �list�suspicious_activity)�selfr   r   s      �7/config/custom_components/ha_network_monitor/monitor.py�__init__�NetworkMonitor.__init__   s   � ��	�$��#.�t�#4�� �    c              �   �   #   � [        5       e7f)z3Start monitoring - to be implemented by subclasses.��NotImplementedError�r   s    r   �start_monitoring�NetworkMonitor.start_monitoring   �   � � �!�#�#��   �c              �   �   #   � [        5       e7f)z2Stop monitoring - to be implemented by subclasses.r   r!   s    r   �stop_monitoring�NetworkMonitor.stop_monitoring   r$   r%   )r   r   r   N)�__name__�
__module__�__qualname__�__firstlineno__�__doc__r   r	   �strr   r"   r'   �__static_attributes__� r   r   r   r      s&   � �,�5�]� 5��C�� 5�
$�$r   r   c                   �*   � \ rS rSrSrS rS rS rSrg)�LightweightMonitor�"   z-Lightweight network monitoring using netstat.c              �   �D  #   � 0 nS nU R                   R                  U5      I Sh  v�N nUR                  5        H�  n SU;   d  SU;   a�  UR                  5       nUS   R                  S5      S   nUS   R                  S5      S   n[        R
                  " U5      R                  (       dQ  [        R
                  " U5      R                  (       d*  U[        R                  " 5       R                  5       S	.X'   M�  M�  M�  M�     U$  N�! [        [        4 a     M�  f = f7f)
z.Get current network connections using netstat.c                  ��   � [         R                  " 5       S:X  a  SS/n O/ SQn  [        R                  " U SS9nU$ ! [        R                   a"  n[
        R                  SU 35         S nAgS nAff = f)	N�Windows�netstat�-n)r7   r8   z-tT)�universal_newlineszError running netstat: � )�platform�system�
subprocess�check_output�CalledProcessError�_LOGGER�error)�cmd�output�es      r   �_run_netstat�8LightweightMonitor.get_connections.<locals>._run_netstat)   si   � ���� �I�-� �$�'��-���#�0�0���N������0�0� ���� 7��s�;�<����s   �; �A1�A,�,A1N�ESTABLISHED�SYN_SENT�   �:r   �   ��
local_addr�	timestamp)r   �async_add_executor_job�
splitlines�split�	ipaddress�
ip_address�
is_private�is_loopbackr   �now�	isoformat�
ValueError�
IndexError)r   �connectionsrE   rC   �line�partsrM   �remote_addrs           r   �get_connections�"LightweightMonitor.get_connections%   s  � � ���	� �y�y�7�7��E�E���%�%�'�D�� �D�(�J�$�,>� �J�J�L�E�!&�q�����!4�Q�!7�J�"'��(�.�.��"5�a�"8�K�%�0�0��=�H�H�%�0�0��=�I�I�*4�)1����)A�)A�)C�4��0� J� I� -?� (�  ��% F�� �
�+� ���s3   �$D �D�D �B<D	�;D �	D�D �D�D c              �   �   #   � g7f)z2Start monitoring - nothing to do for netstat mode.Nr0   r!   s    r   r"   �#LightweightMonitor.start_monitoringJ   �   � � ���   �c              �   �   #   � g7f)z1Stop monitoring - nothing to do for netstat mode.Nr0   r!   s    r   r'   �"LightweightMonitor.stop_monitoringN   rb   rc   r0   N)	r)   r*   r+   r,   r-   r^   r"   r'   r/   r0   r   r   r2   r2   "   s   � �7�#�J�r   r2   c                   �P   ^ � \ rS rSrSrS\S\\   4U 4S jjrS r	S r
S rS	rU =r$ )
�IntensiveMonitor�R   z3Intensive network monitoring using packet sniffing.r   r   c                 �N   >� [         TU ]  X5        SU l        S U l        0 U l        g )NF)�superr   �_running�_snifferrZ   )r   r   r   �	__class__s      �r   r   �IntensiveMonitor.__init__U   s&   �� �����*���������r   c                 �<  � [         U;   a�  U R                  (       a�  U[            R                  nU[            R                  n[        R
                  " U5      R                  (       d4  U[        R                  " 5       R                  5       S.U R                  U'   gggg)zProcess each packet.rL   N)r   rk   �src�dstrR   rS   rT   r   rV   rW   rZ   )r   �packet�src_ip�dst_ips       r   �packet_callback� IntensiveMonitor.packet_callback[   sp   � ���<�D�M�M��B�Z�^�^�F��B�Z�^�^�F��'�'��/�:�:�"(�!)����!9�!9�!;�,�� � ��(� ;�	 *�<r   c              �   �r   ^ #   � ST l         U 4S jnT R                  R                  U5      I Sh  v�N   g N7f)zStart packet sniffing.Tc                  �D   >� [        ST R                  SU 4S jS9T l        g )N�ipr   c                 �&   >� TR                   (       + $ r   )rk   )�_r   s    �r   �<lambda>�HIntensiveMonitor.start_monitoring.<locals>.start_sniff.<locals>.<lambda>p   s   �� �$�-�-�&7r   )�filter�prn�store�stop_filter)r   ru   rl   r!   s   �r   �start_sniff�6IntensiveMonitor.start_monitoring.<locals>.start_sniffk   s!   �� �!���(�(��7�	�D�Mr   N)rk   r   rO   )r   r�   s   ` r   r"   �!IntensiveMonitor.start_monitoringg   s,   �� � ����	� �i�i�.�.�{�;�;�;�s   �,7�5�7c              �   �r   #   � SU l         U R                  (       a  U R                  R                  5         gg7f)zStop packet sniffing.FN)rk   rl   �stopr!   s    r   r'   � IntensiveMonitor.stop_monitoringu   s(   � � �����=�=��M�M��� � �s   �57)rk   rl   rZ   )r)   r*   r+   r,   r-   r   r	   r.   r   ru   r"   r'   r/   �__classcell__�rm   s   @r   rg   rg   R   s1   �� �=��]� ��C�� �
�<�!� !r   rg   c                   �H   ^ � \ rS rSrSrS\S\S\4U 4S jjrS r	S r
S	rU =r$ )
�NetworkSecurityCoordinator�{   z-Coordinator to handle updates and monitoring.r   �monitor_mode�scan_intervalc           	      �   >� [         TU ]  U[        S[        US9S9  X l        [        5       U l        [        [        5      U l	        S U l
        g )NzNetwork Security Monitor)�minutes)�name�update_interval)rj   r   r@   r   r�   �setr   r   r   r   �monitor)r   r   r�   r�   rm   s       �r   r   �#NetworkSecurityCoordinator.__init__~   sK   �� ������+�%�m�<�	 	� 	
� )��$'�E���#.�t�#4�� ���r   c              �   �  #   � U R                   [        :X  a&  [        U R                  U R                  5      U l        O%[        U R                  U R                  5      U l        U R
                  R                  5       I Sh  v�N   g N7f)z1Initialize the appropriate monitor based on mode.N)r�   r   r2   r   r   r�   rg   r"   r!   s    r   �initialize_monitor�-NetworkSecurityCoordinator.initialize_monitor�   sV   � � ���� 0�0�-�d�i�i����I�D�L�+�D�I�I�t���G�D�L��l�l�+�+�-�-�-�s   �A=B�?B� Bc              �   �  #   � U R                   [        :X  a#  U R                  R                  5       I Sh  v�N nOU R                  R                  n/ nUR                  5        HR  u  p4X0R                  ;   d  M  UUS   US   SS.nU R                  U   R                  U5        UR                  U5        MT     U[        U5      [        U R                  5      [        R                  " 5       R                  5       U R                   S.$  N�7f)z&Update data from the selected monitor.NrM   rN   zKnown malicious IP)ry   rM   rN   �type)�alerts�total_monitored�suspicious_count�last_updatedr�   )r�   r   r�   r^   rZ   �itemsr   r   �append�lenr   rV   rW   )r   rZ   �
new_alerts�	remote_ip�	conn_info�alerts         r   �_async_update_data�-NetworkSecurityCoordinator._async_update_data�   s�   � � ���� 0�0� $��� <� <� >�>�K��,�,�2�2�K� �
�$/�$5�$5�$7� �I��O�O�+�#�"+�L�"9�!*�;�!7�0�	�� �(�(��3�:�:�5�A��!�!�%�(� %8� !�"�;�/� #�D�$<�$<� =�$�L�L�N�4�4�6� �-�-�
� 	
�# ?�s   �2D	�D�?D	�8BD	)r�   r�   r   r   )r)   r*   r+   r,   r-   r   r.   �intr   r�   r�   r/   r�   r�   s   @r   r�   r�   {   s/   �� �7�
�]� 
�#� 
�c� 
�.�
� 
r   r�   ) r-   �asyncio�aiohttp�loggingr   r   �collectionsr   r=   r;   �	scapy.allr   r   �typingr   r	   r
   rR   �homeassistant.corer   �(homeassistant.helpers.update_coordinatorr   �constr   r   �	getLoggerr)   r@   r   r2   rg   r�   r0   r   r   �<module>r�      ss   �� (� � � � (� #� � � � "� "� � ,� J� 3�
�
�
�H�
%��$� $�.�� .�`'!�~� '!�R2
�!6� 2
r                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    ha_network_monitor/__pycache__/__init__.cpython-313.pyc                                             0000644 0000000 0000000 00000003753 14753454251 022161  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   �
    �X�gF  �                   �   � S r SSKrSSKrSSKJr  SSKJr  SSKJr  SSK	J
r
  \R                  " \5      rS/rS	\S
\4S jrS	\S\4S jrS	\S\4S jrg)z8Home Assistant component for monitoring network traffic.�    N)�HomeAssistant)�ConfigEntry)�
ConfigType�   )�DOMAIN�sensor�hass�configc              �   �\   #   � 0 U R                   [        '   [        R                  S5        g7f)z(Set up the HA Network Monitor component.z#HA Network Monitor Component LoadedT)�datar   �_LOGGER�info)r	   r
   s     �8/config/custom_components/ha_network_monitor/__init__.py�async_setupr      s#   � � ��D�I�I�f���L�L�6�7��s   �*,�entryc              �   �   #   � UR                   U R                   [           UR                  '   U R                  R	                  U[
        5      I Sh  v�N   g N7f)z-Set up the integration from UI configuration.NT)r   r   �entry_id�config_entries�async_forward_entry_setups�	PLATFORMS)r	   r   s     r   �async_setup_entryr      sE   � � �(-�
�
�D�I�I�f��e�n�n�%�
�
�
�
8�
8��	�
J�J�J�� K�s   �AA�A�Ac              �   ��   #   � U R                   R                  U[        5      I Sh  v�N nU(       a,  U R                  [           R                  UR                  5        U$  N97f)zUnload a config entry.N)r   �async_unload_platformsr   r   r   �popr   )r	   r   �	unload_oks      r   �async_unload_entryr      sJ   � � ��)�)�@�@��	�R�R�I���	�	�&����e�n�n�-��� S�s   �$A"�A �:A")�__doc__�asyncio�logging�homeassistant.corer   �homeassistant.config_entriesr   �homeassistant.helpers.typingr   �constr   �	getLogger�__name__r   r   r   r   r   � �    r   �<module>r(      sj   �� >� � � ,� 4� 3� �
�
�
�H�
%���J�	��M� �:� ��-� �� ��=� �� r'                        ha_network_monitor/__pycache__/config_flow.cpython-313.pyc                                          0000644 0000000 0000000 00000003746 14753455450 022722  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   �
    �Z�gK  �                   �   � S r SSKrSSKrSSKJr  SSKJr  SSKJ	r	J
r
JrJr  \R                  " \5      r " S S\R                   \	S	9rg)
z#Config Flow for HA Network Monitor.�    N)�config_entries)�callback�   )�DOMAIN�MONITOR_MODES�MODE_LIGHTWEIGHT�DEFAULT_SCAN_INTERVALc                   �"   � \ rS rSrSrSS jrSrg)�HANetworkMonitorConfigFlow�   z,Handle a config flow for HA Network Monitor.Nc              �   �T  #   � 0 nUb  U R                  SUS9$ U R                  S[        R                  " [        R                  " S[
        S9[        R                  " [        5      [        R                  " SSS9[        [        R                  " S[        S9[        05      US	S
S.S9$ 7f)zHandle the initial step.zHA Network Monitor)�title�data�user�monitor_mode)�default�enable_notificationsT�scan_intervalz)Uses netstat - safe, lower resource usagez4Uses packet sniffing - requires elevated permissions)�lightweight_desc�intensive_desc)�step_id�data_schema�errors�description_placeholders)�async_create_entry�async_show_form�vol�Schema�Requiredr   �Inr   �boolr	   �int)�self�
user_inputr   s      �;/config/custom_components/ha_network_monitor/config_flow.py�async_step_user�*HANetworkMonitorConfigFlow.async_step_user   s�   � � ����!��*�*�*�� +� � �
 �#�#���
�
����^�5E�F����}�H]����3�T�B�D����_�6K�L�c�$� �
 �$O�"X�&� $� 
� 	
�s   �B&B(� )N)�__name__�
__module__�__qualname__�__firstlineno__�__doc__r&   �__static_attributes__r(   �    r%   r   r      s
   � �6�
r/   r   )�domain)r-   �logging�
voluptuousr   �homeassistantr   �homeassistant.corer   �constr   r   r   r	   �	getLoggerr)   �_LOGGER�
ConfigFlowr   r(   r/   r%   �<module>r9      sD   �� )� � � (� '�� � �
�
�H�
%��
��!:�!:�6� 
r/                             ha_network_monitor/__pycache__/const.cpython-313.pyc                                                0000644 0000000 0000000 00000001151 14753455450 021540  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   �
    �Z�g�  �                   �,   � S r SrSr/ SQrSrSr\\/rSrg)z!Constants for HA Network Monitor.�ha_network_monitorz7https://feodotracker.abuse.ch/downloads/ipblocklist.txt)z192.168.z10.z172.16.z172.17.z172.18.z172.19.z172.20.z172.21.z172.22.z172.23.z172.24.z172.25.�lightweight�	intensive�   N)�__doc__�DOMAIN�THREAT_FEED_URL�PRIVATE_IP_RANGES�MODE_LIGHTWEIGHT�MODE_INTENSIVE�MONITOR_MODES�DEFAULT_SCAN_INTERVAL� �    �5/config/custom_components/ha_network_monitor/const.py�<module>r      s>   �� '�	��K��� � !� ��� ����
 � r                                                                                                                                                                                                                                                                                                                                                                                                                          ha_network_monitor/__pycache__/sensor.cpython-313.pyc                                               0000644 0000000 0000000 00000007445 14753455456 021745  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   �
    �Z�g	  �                   �   � S r SSKrSSKJr  SSKJr  SSKJr  SSKJ	r	  SSK
Jr  SS	KJr  SS
KJr  \R                   " \5      r " S S\\5      rS\S\S\	4S jrg)z'Sensor platform for HA Network Monitor.�    N)�HomeAssistant)�Entity)�CoordinatorEntity)�AddEntitiesCallback)�ConfigEntry�   )�NetworkSecurityCoordinator)�DOMAINc                   �T   ^ � \ rS rSrSrS\4U 4S jjr\S 5       r\S 5       r	Sr
U =r$ )�NetworkSecuritySensor�   z#Network security monitoring sensor.�coordinatorc                 �Z   >� [         TU ]  U5        SU l        SUR                   3U l        g )NzNetwork Security Monitor�network_security_monitor_)�super�__init__�
_attr_name�monitor_mode�_attr_unique_id)�selfr   �	__class__s     ��6/config/custom_components/ha_network_monitor/sensor.pyr   �NetworkSecuritySensor.__init__   s-   �� �����%�4���!:�;�;S�;S�:T�U���    c                 �   � U R                   R                  (       a-  U R                   R                  R                  S/ 5      (       a  ggg)zReturn the state of the sensor.�alerts�Alert�
Monitoring�Initializing)r   �data�get�r   s    r   �state�NetworkSecuritySensor.state   s;   � � ��� � ����$�$�(�(��2�6�6���r   c                 ��  � U R                   R                  (       a�  U R                   R                  R                  SS5      U R                   R                  R                  SS5      U R                   R                  R                  SS5      U R                   R                  R                  S/ 5      U R                   R                  R                  S5      [        U R                   R                  5      S.$ 0 $ )	zReturn the state attributes.r   �unknown�total_monitoredr   �suspicious_countr   �last_updated)r   �total_connections_monitored�suspicious_connections�recent_alertsr)   �all_suspicious_activity)r   r    r!   �dict�suspicious_activityr"   s    r   �extra_state_attributes�,NetworkSecuritySensor.extra_state_attributes   s�   � � ��� � � $� 0� 0� 5� 5� 9� 9�.�)� T�/3�/?�/?�/D�/D�/H�/H�IZ�\]�/^�*.�*:�*:�*?�*?�*C�*C�DV�XY�*Z�!%�!1�!1�!6�!6�!:�!:�8�R�!H� $� 0� 0� 5� 5� 9� 9�.� I�+/��0@�0@�0T�0T�+U�� � �	r   )r   r   )�__name__�
__module__�__qualname__�__firstlineno__�__doc__r	   r   �propertyr#   r0   �__static_attributes__�__classcell__)r   s   @r   r   r      s=   �� �-�V�$>� V�
 �� �� �� �r   r   �hass�entry�async_add_entitiesc              �   �  #   � UR                   R                  S5      nUR                   R                  S5      n[        XU5      nUR                  5       I Sh  v�N   UR	                  5       I Sh  v�N   U" [        U5      /S5        g N0 N7f)z9Set up the network security sensor based on config entry.r   �scan_intervalNT)r    r!   r	   �initialize_monitor� async_config_entry_first_refreshr   )r:   r;   r<   r   r>   r   s         r   �async_setup_entryrA   -   sv   � � � �:�:�>�>�.�1�L��J�J�N�N�?�3�M�,�T��O�K�
�
(�
(�
*�*�*�
�
6�
6�
8�8�8��-�k�:�;�T�B� +�8�s$   �AB�B	�B�0B�1B�B)r6   �logging�homeassistant.corer   �homeassistant.helpers.entityr   �(homeassistant.helpers.update_coordinatorr   �%homeassistant.helpers.entity_platformr   �homeassistant.config_entriesr   �monitorr	   �constr
   �	getLoggerr2   �_LOGGERr   rA   � r   r   �<module>rM      sb   �� -� � ,� /� F� E� 4� /� �
�
�
�H�
%���-�v� �>C�
�C��C� ,�Cr                                                                                                                                                                                                                              ha_network_monitor/sensor.py                                                                        0000644 0000000 0000000 00000004414 14753455301 015361  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   """Sensor platform for HA Network Monitor."""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .monitor import NetworkSecurityCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class NetworkSecuritySensor(CoordinatorEntity, Entity):
    """Network security monitoring sensor."""

    def __init__(self, coordinator: NetworkSecurityCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Network Security Monitor"
        self._attr_unique_id = f"network_security_monitor_{coordinator.monitor_mode}"

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            if self.coordinator.data.get("alerts", []):
                return "Alert"
            return "Monitoring"
        return "Initializing"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self.coordinator.data:
            return {
                "monitor_mode": self.coordinator.data.get("monitor_mode", "unknown"),
                "total_connections_monitored": self.coordinator.data.get("total_monitored", 0),
                "suspicious_connections": self.coordinator.data.get("suspicious_count", 0),
                "recent_alerts": self.coordinator.data.get("alerts", []),
                "last_updated": self.coordinator.data.get("last_updated"),
                "all_suspicious_activity": dict(self.coordinator.suspicious_activity)
            }
        return {}

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
):
    """Set up the network security sensor based on config entry."""
    monitor_mode = entry.data.get("monitor_mode")
    scan_interval = entry.data.get("scan_interval")

    coordinator = NetworkSecurityCoordinator(hass, monitor_mode, scan_interval)
    await coordinator.initialize_monitor()
    await coordinator.async_config_entry_first_refresh()
    
    async_add_entities([NetworkSecuritySensor(coordinator)], True)
                                                                                                                                                                                                                                                    ha_network_monitor/translations/                                                                    0000755 0000000 0000000 00000000000 14753453234 016217  5                                                                                                    ustar   root                            root                                                                                                                                                                                                                   ha_network_monitor/translations/en.json                                                             0000644 0000000 0000000 00000001666 14753453234 017525  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   {
  "title": "HA Network Monitor",
  "config": {
    "step": {
      "user": {
        "title": "Configure HA Network Monitor",
        "description": "Monitor outbound network traffic for suspicious activity.",
        "data": {
          "enable_notifications": "Enable Threat Notifications",
          "scan_interval": "Scan Interval (seconds)"
        }
      }
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Options for HA Network Monitor",
        "data": {
          "enable_notifications": "Enable Threat Notifications",
          "scan_interval": "Scan Interval (seconds)"
        }
      }
    }
  },
  "entity": {
    "sensor": {
      "ha_network_threat_monitor": {
        "name": "Network Threat Monitor",
        "state": {
          "idle": "Idle",
          "threat_detected": "Threat detected"
        },
        "attributes": {
          "suspicious_ips": "Suspicious IPs"
        }
      }
    }
  }
}

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          