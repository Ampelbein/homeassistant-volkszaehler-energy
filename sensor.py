"""Sensor platform for the Volkszaehler integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.integration.sensor import IntegrationSensor
from homeassistant.components.rest.data import RestData
from homeassistant.components.rest.const import SSLCipherList
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo

from .const import CONF_CHANNELS, DOMAIN

# Sensor type configurations for Volkszaehler channels
SENSOR_CONFIGS = {
    "current_power": {
        "name": "Current power",
        "unit": UnitOfPower.WATT,
        "device_class": SensorDeviceClass.POWER,
        "icon": "mdi:power",
        "value_template": "{{ value_json.data.tuples[-1][1] if value_json.data.tuples else None }}",
        "state_class": "measurement",
        "extract_from": "tuples",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Volkszaehler sensors from a config entry using REST platform."""
    host = entry.data["host"]
    port = entry.data["port"]
    channels: dict[str, str] = entry.options.get(CONF_CHANNELS, {})
    
    # Handle old list format for backwards compatibility
    if isinstance(channels, list):
        channels = {uuid: f"Volkszaehler {uuid[:8]}" for uuid in channels}

    entities = []

    for uuid, name in channels.items():
        # Build base URL with optional scheme support; default to http when none is provided
        if host.startswith(("http://", "https://")):
            base_url = host.rstrip("/")
        else:
            base_url = f"http://{host}:{port}"

        # Get current power from recent data (fast query)
        resource_url = f"{base_url}/middleware.php/data/{uuid}.json?from=now-10min&rows=1"

        rest_data = RestData(
            hass,
            "GET",
            resource_url,
            headers=None,
            auth=None,
            encoding="utf-8",
            params=None,
            data=None,
            verify_ssl=True,
            ssl_cipher_list=SSLCipherList.PYTHON_DEFAULT,
        )

        config = SENSOR_CONFIGS["current_power"]
        power_sensor = VolkszaehlerRestSensor(
            hass,
            rest_data,
            entry,
            uuid,
            name,
            "current_power",
            config,
        )
        entities.append(power_sensor)

        # Resolve the power sensor entity_id via the entity registry (fallback to guessed id)
        registry = er.async_get(hass)
        source_entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{uuid}_current_power")
        if not source_entity_id:
            source_entity_id = f"sensor.{name.lower().replace(' ', '_')}_current_power"

        # Create energy sensor using integration platform
        energy_sensor = VolkszaehlerEnergySensor(
            hass=hass,
            source_entity=source_entity_id,
            name=f"{name} energy",
            unique_id=f"{uuid}_energy",
            device_info=DeviceInfo(
                identifiers={(DOMAIN, uuid)},
                name=name,
                manufacturer="Volkszaehler",
            ),
        )
        entities.append(energy_sensor)

    async_add_entities(entities)


class VolkszaehlerRestSensor(SensorEntity):
    """Representation of a Volkszaehler REST sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        rest_data: RestData,
        entry,
        uuid: str,
        device_name: str,
        condition: str,
        config: dict[str, Any],
    ) -> None:
        """Initialize the REST sensor."""
        self.hass = hass
        self._rest_data = rest_data
        self.uuid = uuid
        self._condition = condition
        self._attr_unique_id = f"{uuid}_{condition}"
        self._attr_name = config["name"]
        self._attr_native_unit_of_measurement = config["unit"]
        self._attr_device_class = config["device_class"]
        self._attr_icon = config["icon"]
        self._value_template = config["value_template"]
        self._state_class = config["state_class"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uuid)},
            name=device_name,
            manufacturer="Volkszaehler",
        )

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await self._rest_data.async_update()

    async def async_update(self) -> None:
        """Update the sensor by fetching data from REST API."""
        await self._rest_data.async_update()

        if self._rest_data.data is None:
            self._attr_available = False
            return

        try:
            # Parse the JSON response and extract value
            import json

            data = self._rest_data.data
            if isinstance(data, str):
                data = json.loads(data)

            # Extract the current value from the tuples
            value = self._extract_value(data)
            if value is not None:
                self._attr_native_value = round(float(value), 2)
                self._attr_available = True
            else:
                self._attr_available = False
        except Exception:  # pylint: disable=broad-except
            self._attr_available = False

    def _extract_value(self, data: dict[str, Any]) -> Any:
        """Extract value from JSON response - the last tuple's value."""
        if "data" not in data:
            return None

        channel_data = data["data"]
        if not isinstance(channel_data, dict):
            return None

        # Extract from tuples array (for current power)
        tuples = channel_data.get("tuples")
        if not tuples or not isinstance(tuples, list) or len(tuples) == 0:
            return None

        # Return the value from the last tuple (index 1)
        last_tuple = tuples[-1]
        if isinstance(last_tuple, (list, tuple)) and len(last_tuple) > 1:
            return last_tuple[1]

        return None


class VolkszaehlerEnergySensor(IntegrationSensor):
    """Energy sensor that integrates power to calculate consumption."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        source_entity: str,
        name: str,
        unique_id: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the energy sensor."""
        super().__init__(
            hass,
            integration_method="left",
            name=name,
            round_digits=2,
            source_entity=source_entity,
            unique_id=unique_id,
            unit_prefix="k",
            unit_time=UnitOfTime.HOURS,
            max_sub_interval=None,
        )
        self._attr_device_info = device_info
