from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from dacite import from_dict
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    MANUFACTURER,
    SENSORS,
    EpluconSensorEntityDescription,
    get_common_value,
    get_friendly_operation_mode_text,
    normalize_number,
)
from .eplucon_api.DTO.DeviceDTO import DeviceDTO

_LOGGER = logging.getLogger(__name__)

_DASHBOARD_OPERATION_MODE_ICONS = {
    1: "sun",
    2: "snow",
}


def _get_dashboard_operation_mode_icon(device: Any) -> str | None:
    """Return a stable icon token for the dashboard summary."""
    operation_mode = normalize_number(get_common_value(device, "operation_mode"))
    if not isinstance(operation_mode, int):
        return None
    return _DASHBOARD_OPERATION_MODE_ICONS.get(operation_mode)


def _build_dashboard_summary_attributes(
    device: DeviceDTO,
    last_updated: datetime | None,
) -> dict[str, Any]:
    """Build the card-facing attribute payload for a heat pump."""
    attributes: dict[str, Any] = {
        "device_id": device.id,
        "device_name": device.name,
        "operation_mode": normalize_number(get_common_value(device, "operation_mode")),
        "operation_mode_text": get_friendly_operation_mode_text(device),
        "operation_mode_icon": _get_dashboard_operation_mode_icon(device),
    }

    for attr in (
        "indoor_temperature",
        "outdoor_temperature",
        "configured_indoor_temperature",
        "ww_temperature",
        "ww_temperature_configured",
        "brine_in_temperature",
        "brine_out_temperature",
        "heating_in_temperature",
        "heating_out_temperature",
        "energy_usage",
        "energy_delivered",
        "spf",
    ):
        attributes[attr] = normalize_number(get_common_value(device, attr))

    if last_updated is not None:
        attributes["last_updated"] = last_updated.isoformat()

    return attributes


DASHBOARD_SUMMARY_DESCRIPTION = EpluconSensorEntityDescription(
    key="dashboard_summary",
    name="Dashboard Summary",
    value_fn=get_friendly_operation_mode_text,
    exists_fn=lambda device: (
        getattr(
            getattr(device, "realtime_info", None),
            "common",
            None,
        )
        is not None
    ),
)


def _deduplicate_zone_object_id(object_id: str, key: str) -> str | None:
    """Return the original object id when the device slug was doubled."""
    suffix = f"_{key}"
    if not object_id.endswith(suffix):
        return None

    base = object_id[: -len(suffix)]
    for split_index, char in enumerate(base):
        if char != "_":
            continue

        prefix = base[:split_index]
        if prefix and base[split_index + 1 :] == prefix:
            return f"{prefix}{suffix}"

    return None


def _migrate_zone_entity_id(
    entity_registry: er.EntityRegistry,
    unique_id: str,
    key: str,
) -> None:
    """Rename doubled zone sensor entity ids back to their original form."""
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    if entity_id is None:
        return

    domain, object_id = entity_id.split(".", maxsplit=1)
    target_object_id = _deduplicate_zone_object_id(object_id, key)
    if target_object_id is None or target_object_id == object_id:
        return

    try:
        entity_registry.async_update_entity(
            entity_id,
            new_entity_id=f"{domain}.{target_object_id}",
        )
    except ValueError:
        _LOGGER.warning(
            "Could not rename entity %s to %s",
            entity_id,
            f"{domain}.{target_object_id}",
        )


@dataclass(kw_only=True)
class EpluconZoneSensorEntityDescription(SensorEntityDescription):
    """Description for an Eplucon zone controller sensor."""

    key: str
    name: str
    value_fn: Callable[[Any], StateType]
    exists_fn: Callable[[Any], bool] = lambda _: True


ZONE_CONTROLLER_SENSORS: tuple[EpluconZoneSensorEntityDescription, ...] = (
    EpluconZoneSensorEntityDescription(
        key="set_temperature",
        name="Set Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.zone_controller_info.set_temperature,
        exists_fn=lambda device: device.zone_controller_info is not None,
    ),
    EpluconZoneSensorEntityDescription(
        key="current_temperature",
        name="Current Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.zone_controller_info.current_temperature,
        exists_fn=lambda device: device.zone_controller_info is not None,
    ),
    EpluconZoneSensorEntityDescription(
        key="battery_level",
        name="Battery Level",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        value_fn=lambda device: device.zone_controller_info.raw_data.zone.battery_level,
        exists_fn=lambda device: (
            device.zone_controller_info is not None
            and device.zone_controller_info.raw_data is not None
            and device.zone_controller_info.raw_data.zone is not None
        ),
    ),
    EpluconZoneSensorEntityDescription(
        key="signal_strength",
        name="Signal Strength",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        value_fn=lambda device: (
            device.zone_controller_info.raw_data.zone.signal_strength
        ),
        exists_fn=lambda device: (
            device.zone_controller_info is not None
            and device.zone_controller_info.raw_data is not None
            and device.zone_controller_info.raw_data.zone is not None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eplucon sensors from a config entry."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.async_config_entry_first_refresh()
    heat_pumps: list[DeviceDTO] = []
    zone_controllers: list[DeviceDTO] = []

    for device in coordinator.data:
        if isinstance(device, dict):
            device = from_dict(data_class=DeviceDTO, data=device)

        if device.type == "heat_pump":
            heat_pumps.append(device)
        elif device.type == "zones_controller":
            zone_controllers.append(device)

    entity_registry = er.async_get(hass)
    for device in zone_controllers:
        for description in ZONE_CONTROLLER_SENSORS:
            _migrate_zone_entity_id(
                entity_registry,
                unique_id=f"{device.id}_{description.key}",
                key=description.key,
            )

    entities: list[CoordinatorEntity] = [
        EpluconDashboardSummaryEntity(coordinator, device)
        for device in heat_pumps
        if DASHBOARD_SUMMARY_DESCRIPTION.exists_fn(device)
    ]
    entities.extend(
        EpluconSensorEntity(coordinator, device, description)
        for device in heat_pumps
        for description in SENSORS
        if description.exists_fn(device)
    )
    entities.extend(
        EpluconZonesSensorEntity(coordinator, device, description)
        for device in zone_controllers
        for description in ZONE_CONTROLLER_SENSORS
        if description.exists_fn(device)
    )

    if coordinator.brine_feature_enabled:
        entities.extend(
            EpluconBrineSensorEntity(coordinator, device, "valid_temperature")
            for device in heat_pumps
        )
        entities.extend(
            EpluconBrineSensorEntity(coordinator, device, "monthly_mean")
            for device in heat_pumps
        )

    _LOGGER.debug("Adding %d sensor entities", len(entities))
    async_add_entities(entities)


class EpluconSensorEntity(CoordinatorEntity, SensorEntity):
    """Representation of an Eplucon sensor."""

    entity_description: SensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        device: DeviceDTO,
        entity_description: EpluconSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.device = device
        self.entity_description = entity_description
        self._attr_name = entity_description.name
        self._attr_unique_id = f"{device.id}_{entity_description.key}"

    @property
    def device_info(self) -> dict:
        """Return device info for the device registry."""
        return {
            "manufacturer": MANUFACTURER,
            "identifiers": {(DOMAIN, self.device.account_module_index)},
        }

    def _update_device_data(self) -> None:
        """Update internal device data from coordinator."""
        for updated_device in self.coordinator.data:
            if isinstance(updated_device, dict):
                updated_device = from_dict(data_class=DeviceDTO, data=updated_device)
            if updated_device.id == self.device.id:
                self.device = updated_device
                break

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        try:
            return self.entity_description.value_fn(self.device)
        except (AttributeError, TypeError):
            _LOGGER.debug(
                "Value for sensor %s is temporarily unavailable on device %s",
                self.entity_description.key,
                self.device.id,
            )
            return None

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_device_data()
        super()._handle_coordinator_update()


class EpluconDashboardSummaryEntity(EpluconSensorEntity):
    """Representation of the card-facing Eplucon dashboard summary."""

    _attr_icon = "mdi:view-dashboard-outline"

    def __init__(self, coordinator, device: DeviceDTO) -> None:
        """Initialize the dashboard summary entity."""
        super().__init__(coordinator, device, DASHBOARD_SUMMARY_DESCRIPTION)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return a stable summary payload for the frontend card."""
        return _build_dashboard_summary_attributes(
            self.device,
            getattr(self.coordinator, "last_update_success_time", None),
        )


class EpluconZonesSensorEntity(EpluconSensorEntity):
    """Representation of an Eplucon zone controller sensor."""

    def __init__(
        self,
        coordinator,
        device: DeviceDTO,
        entity_description: EpluconZoneSensorEntityDescription,
    ) -> None:
        """Initialize the zone controller sensor."""
        super().__init__(coordinator, device, entity_description)
        self._attr_name = entity_description.name
        self._attr_unique_id = f"{device.id}_{entity_description.key}"
        self._update_device_data()


class EpluconBrineSensorEntity(CoordinatorEntity, SensorEntity):
    """Representation of a derived Eplucon brine sensor."""

    def __init__(self, coordinator, device: DeviceDTO, sensor_kind: str) -> None:
        """Initialize the derived brine sensor."""
        super().__init__(coordinator)
        self.device = device
        self.sensor_kind = sensor_kind

        if sensor_kind == "valid_temperature":
            self._attr_name = "Brine In Temperature Valid"
            self._attr_unique_id = f"{device.id}_brine_in_temperature_valid"
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        else:
            self._attr_name = "Brine In Temperature Mean Month"
            self._attr_unique_id = f"{device.id}_brine_in_temperature_mean_month"
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_device_class = SensorDeviceClass.TEMPERATURE

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
    def extra_state_attributes(self) -> dict[str, str | int] | None:
        """Return additional monthly statistics metadata."""
        if self.sensor_kind != "monthly_mean":
            return None

        return {
            "month": self.coordinator.get_monthly_brine_month_key(self.device.id),
            "sample_count": self.coordinator.get_monthly_brine_sample_count(
                self.device.id
            ),
        }

    @property
    def native_value(self) -> StateType:
        """Return the derived sensor value."""
        if self.sensor_kind == "valid_temperature":
            brine_temperature = None
            if self.device.realtime_info is not None:
                brine_temperature = (
                    self.device.realtime_info.common.brine_in_temperature
                )
            return self.coordinator.get_valid_brine_temperature(
                self.device.id,
                brine_temperature,
            )

        return self.coordinator.get_monthly_brine_mean(self.device.id)

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
