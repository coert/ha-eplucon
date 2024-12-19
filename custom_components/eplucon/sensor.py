from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from dacite import from_dict
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, MANUFACTURER
from .eplucon_api.DTO.DeviceDTO import DeviceDTO

_LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True)
class EpluconSensorEntityDescription(SensorEntityDescription):
    """Describes an Eplucon sensor entity."""

    key: str
    name: str
    exists_fn: Callable[[Any], bool] = lambda _: True
    value_fn: Callable[[Any], SensorEntityDescription]


# Define the sensor types
SENSORS_HEATPUMP: tuple[EpluconSensorEntityDescription, ...] = (
    EpluconSensorEntityDescription(
        key="indoor_temperature",
        name="Indoor Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.indoor_temperature,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.indoor_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="act_vent_rpm",
        name="Act Vent RPM",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        value_fn=lambda device: device.realtime_info.common.act_vent_rpm,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.act_vent_rpm is not None,
    ),
    EpluconSensorEntityDescription(
        key="brine_circulation_pump",
        name="Brine Circulation Pump",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda device: device.realtime_info.common.brine_circulation_pump,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.brine_circulation_pump is not None,
    ),
    EpluconSensorEntityDescription(
        key="brine_in_temperature",
        name="Brine In Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.brine_in_temperature,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.brine_in_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="brine_out_temperature",
        name="Brine Out Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.brine_out_temperature,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.brine_out_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="brine_pressure",
        name="Brine Pressure",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE,
        value_fn=lambda device: device.realtime_info.common.brine_pressure,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.brine_pressure is not None,
    ),
    EpluconSensorEntityDescription(
        key="compressor_speed",
        name="Compressor Speed",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        value_fn=lambda device: device.realtime_info.common.compressor_speed,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.compressor_speed is not None,
    ),
    EpluconSensorEntityDescription(
        key="condensation_temperature",
        name="Condensation Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.condensation_temperature,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.condensation_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="configured_indoor_temperature",
        name="Configured Indoor Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.configured_indoor_temperature,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.configured_indoor_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="cv_pressure",
        name="CV Pressure",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE,
        value_fn=lambda device: device.realtime_info.common.cv_pressure,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.cv_pressure is not None,
    ),
    EpluconSensorEntityDescription(
        key="energy_delivered",
        name="Energy Delivered",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        value_fn=lambda device: device.realtime_info.common.energy_delivered,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.energy_delivered is not None,
    ),
    EpluconSensorEntityDescription(
        key="energy_usage",
        name="Energy Usage",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        value_fn=lambda device: device.realtime_info.common.energy_usage,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.energy_usage is not None,
    ),
    EpluconSensorEntityDescription(
        key="evaporation_temperature",
        name="Evaporation Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.evaporation_temperature,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.evaporation_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="export_energy",
        name="Export Energy",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        value_fn=lambda device: device.realtime_info.common.export_energy,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.export_energy is not None,
    ),
    EpluconSensorEntityDescription(
        key="heating_in_temperature",
        name="Heating In Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.heating_in_temperature,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.heating_in_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="heating_out_temperature",
        name="Heating Out Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.heating_out_temperature,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.heating_out_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="import_energy",
        name="Import Energy",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        value_fn=lambda device: device.realtime_info.common.import_energy,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.import_energy is not None,
    ),
    EpluconSensorEntityDescription(
        key="inverter_temperature",
        name="Inverter Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.inverter_temperature,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.inverter_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="operating_hours",
        name="Operating Hours",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda device: device.realtime_info.common.operating_hours,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.operating_hours is not None,
    ),
    EpluconSensorEntityDescription(
        key="outdoor_temperature",
        name="Outdoor Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.outdoor_temperature,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.outdoor_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="overheating",
        name="Overheating",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.overheating,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.overheating is not None,
    ),
    EpluconSensorEntityDescription(
        key="press_gas_pressure",
        name="Press Gas Pressure",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE,
        value_fn=lambda device: device.realtime_info.common.press_gas_pressure,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.press_gas_pressure is not None,
    ),
    EpluconSensorEntityDescription(
        key="press_gas_temperature",
        name="Press Gas Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.press_gas_temperature,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.press_gas_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="production_circulation_pump",
        name="Production Circulation Pump",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda device: device.realtime_info.common.production_circulation_pump,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.production_circulation_pump is not None,
    ),
    EpluconSensorEntityDescription(
        key="suction_gas_pressure",
        name="Suction Gas Pressure",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE,
        value_fn=lambda device: device.realtime_info.common.suction_gas_pressure,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.suction_gas_pressure is not None,
    ),
    EpluconSensorEntityDescription(
        key="suction_gas_temperature",
        name="Suction Gas Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.suction_gas_temperature,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.suction_gas_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="total_active_power",
        name="Total Active Power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda device: device.realtime_info.common.total_active_power,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.total_active_power is not None,
    ),
    EpluconSensorEntityDescription(
        key="ww_temperature",
        name="WW Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.ww_temperature,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.ww_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="ww_temperature_configured",
        name="WW Temperature Configured",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.realtime_info.common.ww_temperature_configured,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.ww_temperature_configured is not None,
    ),
    EpluconSensorEntityDescription(
        key="active_requests_ww",
        name="Active WW request",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda device: "ON"
        if device.realtime_info.common.active_requests_ww in ["ON", "1"]
        else "OFF",
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.active_requests_ww is not None,
    ),
    EpluconSensorEntityDescription(
        key="dg1",
        name="Direct Outlet (DG1)",
        value_fn=lambda device: "ON"
        if device.realtime_info.common.dg1 in ["ON", "1"]
        else "OFF",
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.dg1 is not None,
    ),
    EpluconSensorEntityDescription(
        key="sg2",
        name="Mixture Outlet (SG2)",
        value_fn=lambda device: "ON"
        if device.realtime_info.common.sg2 in ["ON", "1"]
        else "OFF",
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.sg2 is not None,
    ),
    EpluconSensorEntityDescription(
        key="sg3",
        name="Mixture Outlet (SG3)",
        value_fn=lambda device: "ON"
        if device.realtime_info.common.sg3 in ["ON", "1"]
        else "OFF",
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.sg3 is not None,
    ),
    EpluconSensorEntityDescription(
        key="sg4",
        name="Mixture Outlet (SG4)",
        value_fn=lambda device: "ON"
        if device.realtime_info.common.sg4 in ["ON", "1"]
        else "OFF",
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.sg4 is not None,
    ),
    EpluconSensorEntityDescription(
        key="spf",
        name="Seasonal Performance Factor (SPF)",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.realtime_info.common.spf,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.spf is not None,
    ),
    EpluconSensorEntityDescription(
        key="position_expansion_ventil",
        name="Position Expansion Ventil",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda device: device.realtime_info.common.position_expansion_ventil,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.position_expansion_ventil is not None,
    ),
    EpluconSensorEntityDescription(
        key="number_of_starts",
        name="Number of Starts",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda device: device.realtime_info.common.number_of_starts,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.number_of_starts is not None,
    ),
    EpluconSensorEntityDescription(
        key="heating_mode",
        name="Heating Mode",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda device: "ON"
        if device.realtime_info.common.heating_mode in ["ON", "1"]
        else "OFF",
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.heating_mode is not None,
    ),
    EpluconSensorEntityDescription(
        key="warmwater",
        name="Warm Water",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda device: "ON"
        if device.realtime_info.common.warmwater in ["ON", "1"]
        else "OFF",
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.warmwater is not None,
    ),
    EpluconSensorEntityDescription(
        key="alarm_active",
        name="Alarm Active",
        value_fn=lambda device: "ON"
        if device.realtime_info.common.alarm_active in ["ON", "1"]
        else "OFF",
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.alarm_active is not None,
    ),
    EpluconSensorEntityDescription(
        key="current_heating_pump_state",
        name="Current Heating Pump State",
        value_fn=lambda device: "ON"
        if device.realtime_info.common.current_heating_pump_state in ["ON", "1"]
        else "OFF",
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.current_heating_pump_state is not None,
    ),
    EpluconSensorEntityDescription(
        key="current_heating_state",
        name="Current Heating State",
        value_fn=lambda device: "ON"
        if device.realtime_info.common.current_heating_state in ["ON", "1"]
        else "OFF",
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.current_heating_state is not None,
    ),
    EpluconSensorEntityDescription(
        key="operation_mode",
        name="Operation Mode",
        device_class=SensorDeviceClass.ENUM,
        value_fn=lambda device: device.realtime_info.common.operation_mode,
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.operation_mode is not None,
    ),
    EpluconSensorEntityDescription(
        key="operation_mode_text",
        name="Operation Mode Text",
        device_class=SensorDeviceClass.ENUM,
        value_fn=lambda device: get_friendly_operation_mode_text(device),
        exists_fn=lambda device: device.realtime_info is not None
        and device.realtime_info.common is not None
        and device.realtime_info.common.operation_mode is not None,
    ),
)

SENSORS_ZONES_CONTROLLER: tuple[EpluconSensorEntityDescription, ...] = (
    EpluconSensorEntityDescription(
        key="set_temperature",
        name="Set Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.zone_controller_info.set_temperature,
        exists_fn=lambda device: device.zone_controller_info is not None
        and device.zone_controller_info.set_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="current_temperature",
        name="Current Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: device.zone_controller_info.current_temperature,
        exists_fn=lambda device: device.zone_controller_info is not None
        and device.zone_controller_info.current_temperature is not None,
    ),
    EpluconSensorEntityDescription(
        key="battery_level",
        name="Battery Level",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        value_fn=lambda device: device.zone_controller_info.raw_data.zone.battery_level,
        exists_fn=lambda device: device.zone_controller_info is not None
        and device.zone_controller_info.raw_data is not None
        and device.zone_controller_info.raw_data.zone is not None,
    ),
    EpluconSensorEntityDescription(
        key="signal_strength",
        name="Signal Strength",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        value_fn=lambda device: device.zone_controller_info.raw_data.zone.signal_strength,
        exists_fn=lambda device: device.zone_controller_info is not None
        and device.zone_controller_info.raw_data is not None
        and device.zone_controller_info.raw_data.zone is not None,
    ),
)


def get_friendly_operation_mode_text(device: DeviceDTO) -> str:
    # TODO: Consider adding localization options for the operation mode text, now hardcoded Dutch.
    try:
        operation_mode = int(device.realtime_info.common.operation_mode)
    except TypeError:
        _LOGGER.debug(f"Operation mode is not available for device {device.id}")
        return "Unavailable"

    match operation_mode:
        case 1:
            return "Koeling"
        case 2:
            return "Verwarming"
        case 3:
            return "Auto th-TOUCH"
        case 4:
            return "Auto Wp"
        case 5:
            return "Haard"
        case _:
            return "Unknown operation mode"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    _LOGGER.debug(f"{inspect.currentframe().f_code.co_name}")  # type: ignore
    """Set up Eplucon sensor based on a config entry."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Ensure the coordinator has refreshed its data
    await coordinator.async_config_entry_first_refresh()

    devices = coordinator.data

    list_device_dto_heat_pump: list[DeviceDTO] = []
    list_device_dto_zones_controllers: list[DeviceDTO] = []

    for device in devices:
        if isinstance(device, dict):
            device = from_dict(data_class=DeviceDTO, data=device)
        assert isinstance(device, DeviceDTO), f"Expected DeviceDTO, got {type(device)}"
        if device.type == "heat_pump":
            list_device_dto_heat_pump.append(device)
        elif device.type == "zones_controller":
            list_device_dto_zones_controllers.append(device)

    async_add_entities(
        EpluconSensorEntity(coordinator, device, description)
        for device in list_device_dto_heat_pump
        for description in SENSORS_HEATPUMP
        if description.exists_fn(device)
    )

    async_add_entities(
        EpluconZonesSensorEntity(coordinator, device, description)
        for device in list_device_dto_zones_controllers
        for description in SENSORS_ZONES_CONTROLLER
        if description.exists_fn(device)
    )


class EpluconSensorEntity(CoordinatorEntity, SensorEntity):
    """Representation of an Eplucon sensor."""

    entity_description: EpluconSensorEntityDescription

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
        self._attr_name = f"{entity_description.name}"
        self._attr_unique_id = f"{device.id}_{entity_description.key}"
        self._update_device_data()

    @property
    def device_info(self) -> dict:
        """Return information to link this entity with the correct device."""
        return {
            "manufacturer": MANUFACTURER,
            "identifiers": {(DOMAIN, self.device.account_module_index)},
        }

    def _update_device_data(self):
        """Update the internal data from the coordinator."""
        # Assuming devices are updated in the coordinator data
        for updated_device in self.coordinator.data:
            if isinstance(updated_device, dict):
                updated_device = from_dict(data_class=DeviceDTO, data=updated_device)
            if updated_device.id == self.device.id:
                self.device = updated_device

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.device)

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug(f"Getting update from coordinator in sensor {self.name}.")
        self._update_device_data()
        super()._handle_coordinator_update()


class EpluconZonesSensorEntity(EpluconSensorEntity):
    """Representation of an Eplucon sensor."""

    def __init__(
        self,
        coordinator,
        device: DeviceDTO,
        entity_description: EpluconSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, entity_description)
        self._attr_name = f"{device.name}, {entity_description.name}"
        self._attr_unique_id = f"{device.id}_{entity_description.key}"
        self._update_device_data()
