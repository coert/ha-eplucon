from __future__ import annotations

import logging

from dacite import from_dict
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BINARY_SENSORS, DOMAIN, MANUFACTURER
from .eplucon_api.DTO.DeviceDTO import DeviceDTO

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eplucon binary sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.async_config_entry_first_refresh()

    heat_pumps: list[DeviceDTO] = []
    entities: list[CoordinatorEntity] = []
    for device in coordinator.data:
        if isinstance(device, dict):
            device = from_dict(data_class=DeviceDTO, data=device)

        if device.type != "heat_pump":
            continue

        heat_pumps.append(device)
        for description in BINARY_SENSORS:
            if description.exists_fn(device):
                entities.append(
                    EpluconBinarySensorEntity(coordinator, device, description)
                )

    if coordinator.brine_feature_enabled:
        entities.extend(
            EpluconBrineValidityBinarySensor(coordinator, device)
            for device in heat_pumps
        )

    _LOGGER.debug("Adding %d binary sensor entities", len(entities))
    async_add_entities(entities)


class EpluconBinarySensorEntity(CoordinatorEntity, BinarySensorEntity):
    """Representation of an Eplucon binary sensor."""

    def __init__(self, coordinator, device: DeviceDTO, description) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.device = device
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{device.id}_{description.key}"

    @property
    def device_info(self) -> dict:
        """Return information to link this entity with the correct device."""
        return {
            "manufacturer": MANUFACTURER,
            "identifiers": {(DOMAIN, self.device.account_module_index)},
        }

    @property
    def is_on(self) -> bool:
        """Return if the binary sensor is currently on."""
        return bool(self.entity_description.value_fn(self.device))

    def _update_device_data(self) -> None:
        """Update internal device data from the coordinator."""
        for updated_device in self.coordinator.data:
            if isinstance(updated_device, dict):
                updated_device = from_dict(data_class=DeviceDTO, data=updated_device)
            if updated_device.id == self.device.id:
                self.device = updated_device
                break

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_device_data()
        super()._handle_coordinator_update()


class EpluconBrineValidityBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of the derived brine validity binary sensor."""

    def __init__(self, coordinator, device: DeviceDTO) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.device = device
        self._attr_name = "Brine Circulation Valid"
        self._attr_unique_id = f"{device.id}_brine_circulation_valid"
        self._update_device_data()

    @property
    def device_info(self) -> dict:
        """Return information to link this entity with the correct device."""
        return {
            "manufacturer": MANUFACTURER,
            "identifiers": {(DOMAIN, self.device.account_module_index)},
        }

    @property
    def available(self) -> bool:
        """Return if the source heat pump data is available."""
        return (
            super().available
            and self.device.realtime_info is not None
            and self.device.realtime_info.common is not None
        )

    @property
    def is_on(self) -> bool:
        """Return if the brine circulation is currently valid."""
        return self.coordinator.is_brine_valid(self.device.id)

    def _update_device_data(self) -> None:
        """Update the internal data from the coordinator."""
        for updated_device in self.coordinator.data:
            if isinstance(updated_device, dict):
                updated_device = from_dict(data_class=DeviceDTO, data=updated_device)
            if updated_device.id == self.device.id:
                self.device = updated_device
                break

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_device_data()
        super()._handle_coordinator_update()
