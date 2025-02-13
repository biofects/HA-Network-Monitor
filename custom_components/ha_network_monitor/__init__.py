"""Home Assistant component for monitoring network traffic."""
import asyncio
import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the HA Network Monitor component."""
    hass.data.setdefault(DOMAIN, {})
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

