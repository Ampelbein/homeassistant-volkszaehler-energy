"""Volkszaehler-Energy integration entry setup."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Typed config entry runtime_data for strict typing (PEP-695 type aliases)
type VolkszaehlerConfigEntry = ConfigEntry

async def async_setup_entry(hass: HomeAssistant, entry: VolkszaehlerConfigEntry) -> bool:
	"""Set up Volkszaehler from a config entry."""
	await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

	# Listen for options updates to reload platforms
	entry.async_on_unload(entry.add_update_listener(async_reload_entry))

	return True

async def async_unload_entry(hass: HomeAssistant, entry: VolkszaehlerConfigEntry) -> bool:
	"""Unload a config entry."""
	return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def async_reload_entry(hass: HomeAssistant, entry: VolkszaehlerConfigEntry) -> None:
	"""Reload config entry when options change."""
	await hass.config_entries.async_reload(entry.entry_id)
