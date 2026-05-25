from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from custom_components.eplucon.sensor import (
    EpluconDashboardSummaryEntity,
    EpluconZonesSensorEntity,
    ZONE_CONTROLLER_SENSORS,
    _deduplicate_zone_object_id,
)
from custom_components.eplucon.eplucon_api.DTO.CommonInfoDTO import CommonInfoDTO
from custom_components.eplucon.eplucon_api.DTO.DeviceDTO import DeviceDTO
from custom_components.eplucon.eplucon_api.DTO.RealtimeInfoDTO import RealtimeInfoDTO
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


def _build_heat_pump_device() -> DeviceDTO:
    return DeviceDTO(
        id=42,
        account_module_index="heat-pump-0",
        name="Heat Pump",
        type="heat_pump",
        realtime_info=RealtimeInfoDTO(
            common=CommonInfoDTO(
                spf=4.2,
                indoor_temperature=21.3,
                outdoor_temperature=8.7,
                brine_in_temperature=9.1,
                brine_out_temperature=6.8,
                configured_indoor_temperature=20.5,
                heating_in_temperature=33.2,
                heating_out_temperature=28.4,
                energy_usage=1234,
                energy_delivered=4567,
                import_energy=0,
                export_energy=0,
                ww_temperature=49.0,
                ww_temperature_configured=50.0,
                brine_pressure=1.2,
                cv_pressure=1.8,
                evaporation_temperature=2.1,
                condensation_temperature=37.4,
                inverter_temperature=31.5,
                compressor_speed=55,
                suction_gas_temperature=12.0,
                suction_gas_pressure=2.4,
                press_gas_temperature=58.0,
                press_gas_pressure=14.1,
                overheating=6.0,
                position_expansion_ventil=22,
                total_active_power=2.9,
                number_of_starts=345,
                operating_hours=6789,
                operation_mode=1,
                heating_mode=1,
                dg1="ON",
                sg2="OFF",
                sg3="OFF",
                sg4="OFF",
                warmwater=0,
                brine_circulation_pump=41,
                production_circulation_pump=53,
                act_vent_rpm=1230,
                alarm_active=False,
                alarm_time=None,
                active_requests_ww="OFF",
                current_heating_pump_state=1,
                current_heating_state=1,
            ),
            heatpump=[],
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


def test_dashboard_summary_sensor_exposes_card_facing_attributes() -> None:
    """Heat pump summary entity should expose a stable card payload."""
    device = _build_heat_pump_device()
    coordinator = SimpleNamespace(
        data=[device],
        last_update_success_time=datetime(2026, 5, 25, 12, 30, 0),
    )

    entity = EpluconDashboardSummaryEntity(coordinator, device)

    assert entity.native_value == "Koeling"
    assert entity.extra_state_attributes == {
        "device_id": 42,
        "device_name": "Heat Pump",
        "operation_mode": 1,
        "operation_mode_text": "Koeling",
        "operation_mode_icon": "sun",
        "indoor_temperature": 21.3,
        "outdoor_temperature": 8.7,
        "configured_indoor_temperature": 20.5,
        "ww_temperature": 49,
        "ww_temperature_configured": 50,
        "brine_in_temperature": 9.1,
        "brine_out_temperature": 6.8,
        "heating_in_temperature": 33.2,
        "heating_out_temperature": 28.4,
        "energy_usage": 1234,
        "energy_delivered": 4567,
        "spf": 4.2,
        "last_updated": "2026-05-25T12:30:00",
    }
