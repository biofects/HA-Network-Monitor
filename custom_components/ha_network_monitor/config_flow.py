"""Config Flow for HA Network Monitor."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import (
    DOMAIN, 
    MONITOR_MODES, 
    MODE_LIGHTWEIGHT, 
    DEFAULT_SCAN_INTERVAL
)

_LOGGER = logging.getLogger(__name__)

class HANetworkMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA Network Monitor."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title="HA Network Monitor", 
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("monitor_mode", default=MODE_LIGHTWEIGHT): vol.In(MONITOR_MODES),
                vol.Required("enable_notifications", default=True): bool,
                vol.Required("scan_interval", default=DEFAULT_SCAN_INTERVAL): int,
            }),
            errors=errors,
            description_placeholders={
                "lightweight_desc": "Uses netstat - safe, lower resource usage",
                "intensive_desc": "Uses packet sniffing - requires elevated permissions"
            }
        )
