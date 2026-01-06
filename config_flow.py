"""Config flow for Volkszaehler-Energy integration."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_CHANNELS, DEFAULT_HOST, DEFAULT_PORT, DOMAIN


class VolkszaehlerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Volkszaehler-Energy."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input.get("host", DEFAULT_HOST)
            port = user_input.get("port", DEFAULT_PORT)

            # Test connection to the Volkszaehler API
            if not await self._test_connection(host, port):
                errors["base"] = "cannot_connect"
            else:
                # Use host:port as unique ID to prevent duplicate servers
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Volkszaehler ({host}:{port})",
                    data={
                        "host": host,
                        "port": port,
                    },
                    options={
                        CONF_CHANNELS: {},
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Optional("host", default=DEFAULT_HOST): str,
                vol.Optional("port", default=DEFAULT_PORT): int,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def _test_connection(self, host: str, port: int) -> bool:
        """Test connection to Volkszaehler API."""
        try:
            session = async_get_clientsession(self.hass)
            # Try to reach the middleware endpoint
            url = f"http://{host}:{port}/middleware.php"

            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                # Volkszaehler middleware returns 400 without parameters, but connection is valid
                return response.status in (200, 400)
        except aiohttp.ClientError:
            return False
        except Exception:  # pylint: disable=broad-except
            return False

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return VolkszaehlerOptionsFlow(config_entry)

class VolkszaehlerOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Volkszaehler."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage channels - add one channel at a time."""
        if user_input is not None:
            # Add the new channel
            current_channels = dict(self.entry.options.get(CONF_CHANNELS, {}))

            # Handle old format (list) for backwards compatibility
            if isinstance(current_channels, list):
                current_channels = {uuid: f"Volkszaehler {uuid[:8]}" for uuid in current_channels}

            name = user_input.get("channel_name", "").strip()
            uuid = user_input.get("channel_uuid", "").strip()

            if name and uuid:
                current_channels[uuid] = name

            # Save and show the form again to add more channels
            self.hass.config_entries.async_update_entry(
                self.entry,
                options={CONF_CHANNELS: current_channels},
            )

            # Return to the same form to add more channels
            return await self.async_step_init()

        # Get current channels to display
        current_channels = self.entry.options.get(CONF_CHANNELS, {})
        if isinstance(current_channels, list):
            current_channels = {uuid: f"Volkszaehler {uuid[:8]}" for uuid in current_channels}

        # Build description showing current channels
        if current_channels:
            channels_list = "\n".join(
                [f"• {name}: {uuid}" for uuid, name in current_channels.items()]
            )
            description = f"Current channels:\n{channels_list}\n\nAdd a new channel below:"
        else:
            description = "No channels configured yet. Add your first channel below:"

        schema = vol.Schema(
            {
                vol.Optional("channel_name", default=""): str,
                vol.Optional("channel_uuid", default=""): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={"current": description},
        )
