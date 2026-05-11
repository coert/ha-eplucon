from __future__ import annotations

from types import SimpleNamespace

from custom_components.eplucon.sensor import (
    EpluconZonesSensorEntity,
    ZONE_CONTROLLER_SENSORS,
    _deduplicate_zone_object_id,
)
from custom_components.eplucon.eplucon_api.DTO.DeviceDTO import DeviceDTO
from custom_components.eplucon.eplucon_api.DTO.ZoneControllerInfoDTO import (
    ZoneControllerInfoDTO,
)
from custom_components.eplucon.eplucon_api.DTO.ZoneControllerRawDTO import (
    ZoneControllerRawDTO,
)
from custom_components.eplucon.eplucon_api.DTO.ZoneControllerRawZoneDTO import (
    ZoneControllerRawZoneDTO,
)


def _build_zone_device(
    *,
    current_temperature: float | None,
    set_temperature: float | None,
) -> DeviceDTO:
    return DeviceDTO(
        id=5700,
        account_module_index="zone-0",
        name="Controller: Living",
        type="zones_controller",
        zone_controller_id=1234,
        zone_controller_info=ZoneControllerInfoDTO(
            id=5700,
            name="Living",
            set_temperature=set_temperature,
            mode="auto",
            raw_data=ZoneControllerRawDTO(
                zone=ZoneControllerRawZoneDTO(
                    id=5700,
                    parentId=1234,
                    time="2026-05-11T12:00:00",
                    duringChange=False,
                    index=0,
                    currentTemperature=210,
                    setTemperature=200,
                    flags={},
                    zoneState="idle",
                    signalStrength=-55,
                    batteryLevel=95,
                    actuatorsOpen=0,
                    humidity=None,
                    visibility=True,
                ),
                description={},
                mode={},
                schedule={},
                actuators=[],
                underfloor={},
                windowsSensors=[],
                additionalContacts=[],
                color="blue",
            ),
            current_temperature=current_temperature,
        ),
    )


def test_zone_temperature_sensors_exist_with_missing_initial_values() -> None:
    """Zone temperature entities should survive sparse startup payloads."""
    device = _build_zone_device(current_temperature=None, set_temperature=None)

    set_temperature_description = next(
        description
        for description in ZONE_CONTROLLER_SENSORS
        if description.key == "set_temperature"
    )
    current_temperature_description = next(
        description
        for description in ZONE_CONTROLLER_SENSORS
        if description.key == "current_temperature"
    )

    assert set_temperature_description.exists_fn(device) is True
    assert current_temperature_description.exists_fn(device) is True


def test_zone_temperature_sensor_returns_none_when_value_missing() -> None:
    """Zone temperature sensors should expose an unknown state instead of failing."""
    device = _build_zone_device(current_temperature=None, set_temperature=None)
    coordinator = SimpleNamespace(data=[device])
    current_temperature_description = next(
        description
        for description in ZONE_CONTROLLER_SENSORS
        if description.key == "current_temperature"
    )

    entity = EpluconZonesSensorEntity(
        coordinator,
        device,
        current_temperature_description,
    )

    assert entity.native_value is None


def test_zone_temperature_sensor_name_does_not_repeat_device_name() -> None:
    """Zone sensors should let Home Assistant prepend the device name once."""
    device = _build_zone_device(current_temperature=21.0, set_temperature=20.0)
    coordinator = SimpleNamespace(data=[device])
    current_temperature_description = next(
        description
        for description in ZONE_CONTROLLER_SENSORS
        if description.key == "current_temperature"
    )

    entity = EpluconZonesSensorEntity(
        coordinator,
        device,
        current_temperature_description,
    )

    assert entity.has_entity_name is True
    assert entity.name == "Current Temperature"


def test_deduplicate_zone_object_id_restores_original_slug() -> None:
    """Existing doubled zone slugs should migrate back to the original form."""
    assert (
        _deduplicate_zone_object_id(
            "thermostaat_bg_thermostaat_bg_current_temperature",
            "current_temperature",
        )
        == "thermostaat_bg_current_temperature"
    )
    assert (
        _deduplicate_zone_object_id(
            "thermostaat_bg_set_temperature",
            "set_temperature",
        )
        is None
    )
