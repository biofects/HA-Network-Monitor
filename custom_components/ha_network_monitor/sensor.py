"""Sensor platform for HA Network Monitor."""
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
