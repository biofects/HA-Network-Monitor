"""Constants for HA Network Monitor."""
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
