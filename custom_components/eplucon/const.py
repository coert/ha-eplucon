from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)

DOMAIN = "eplucon"
MANUFACTURER = "Eplucon"
PLATFORMS = ["sensor", "binary_sensor"]
EPLUCON_PORTAL_URL = "https://portaal.eplucon.nl/"
SUPPORTED_TYPES = ["heat_pump", "zones_controller"]

CONF_ENABLE_BRINE_VALIDITY_STATS = "enable_brine_validity_stats"
CONF_BRINE_PUMP_THRESHOLD = "brine_pump_threshold"
CONF_BRINE_VALID_MINUTES = "brine_valid_minutes"
CONF_BRINE_SAMPLE_INTERVAL_MINUTES = "brine_sample_interval_minutes"

DEFAULT_ENABLE_BRINE_VALIDITY_STATS = False
DEFAULT_BRINE_PUMP_THRESHOLD = 5.0
DEFAULT_BRINE_VALID_MINUTES = 15
DEFAULT_BRINE_SAMPLE_INTERVAL_MINUTES = 5

BRINE_STATS_STORAGE_VERSION = 1


def get_common_value(device: Any, attr: str) -> Any:
    """Safely read a value from the realtime common payload."""
    info = getattr(device, "realtime_info", None)
    common = getattr(info, "common", None)
    return getattr(common, attr, None)


def normalize_bool(value: Any) -> bool:
    """Normalize common API truthy values to a bool."""
    if isinstance(value, bool):
        return value
    return str(value).upper() in {"1", "ON", "TRUE"}


def normalize_number(value: Any) -> int | float | None:
    """Normalize numeric values while preserving unavailable states."""
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def get_friendly_operation_modes() -> dict[int, str]:
    """Return a mapping of operation mode integers to friendly labels."""
    return {
        1: "Koeling",
        2: "Verwarming",
        3: "Auto th-TOUCH",
        4: "Auto Wp",
        5: "Haard",
    }

def get_friendly_operation_mode_text(device: Any) -> str:
    """Return a friendly label for the operation mode."""
    try:
        operation_mode = int(get_common_value(device, "operation_mode"))
    except (TypeError, ValueError) :
        return "Unavailable"

    return get_friendly_operation_modes().get(operation_mode, "Unknown operation mode")


def get_friendly_heating_mode_text(device: Any) -> str:
    """Return a friendly label for the heating mode."""
    try:
        heating_mode = int(get_common_value(device, "heating_mode"))
    except (TypeError, ValueError):
        return "Unavailable"

    return {
        0: "Off",
        1: "On",
        2: "Emergency operation",
        3: "APX",
    }.get(heating_mode, "Unknown heating mode")


@dataclass(kw_only=True)
class EpluconSensorEntityDescription(SensorEntityDescription):
    """Description for an Eplucon sensor entity."""

    key: str
    name: str
    value_fn: Callable[[Any], Any]
    exists_fn: Callable[[Any], bool] = lambda _: True


@dataclass(kw_only=True)
class EpluconBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Description for an Eplucon binary sensor entity."""

    key: str
    name: str
    value_fn: Callable[[Any], bool]
    exists_fn: Callable[[Any], bool] = lambda _: True


RAW_SENSOR_DEFS = [
    {
        "key": "indoor_temperature",
        "name": "Indoor Temperature",
        "attr": "indoor_temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "outdoor_temperature",
        "name": "Outdoor Temperature",
        "attr": "outdoor_temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "brine_in_temperature",
        "name": "Brine In Temperature",
        "attr": "brine_in_temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "brine_out_temperature",
        "name": "Brine Out Temperature",
        "attr": "brine_out_temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "configured_indoor_temperature",
        "name": "Configured Indoor Temperature",
        "attr": "configured_indoor_temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "heating_in_temperature",
        "name": "Heating In Temperature",
        "attr": "heating_in_temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "heating_out_temperature",
        "name": "Heating Out Temperature",
        "attr": "heating_out_temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "ww_temperature",
        "name": "WW Temperature",
        "attr": "ww_temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "ww_temperature_configured",
        "name": "WW Temperature Configured",
        "attr": "ww_temperature_configured",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "brine_pressure",
        "name": "Brine Pressure",
        "attr": "brine_pressure",
        "unit": UnitOfPressure.BAR,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.PRESSURE,
    },
    {
        "key": "cv_pressure",
        "name": "CV Pressure",
        "attr": "cv_pressure",
        "unit": UnitOfPressure.BAR,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.PRESSURE,
    },
    {
        "key": "suction_gas_pressure",
        "name": "Suction Gas Pressure",
        "attr": "suction_gas_pressure",
        "unit": UnitOfPressure.BAR,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.PRESSURE,
    },
    {
        "key": "press_gas_pressure",
        "name": "Press Gas Pressure",
        "attr": "press_gas_pressure",
        "unit": UnitOfPressure.BAR,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.PRESSURE,
    },
    {
        "key": "suction_gas_temperature",
        "name": "Suction Gas Temperature",
        "attr": "suction_gas_temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "press_gas_temperature",
        "name": "Press Gas Temperature",
        "attr": "press_gas_temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "condensation_temperature",
        "name": "Condensation Temperature",
        "attr": "condensation_temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "evaporation_temperature",
        "name": "Evaporation Temperature",
        "attr": "evaporation_temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "inverter_temperature",
        "name": "Inverter Temperature",
        "attr": "inverter_temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "compressor_speed",
        "name": "Compressor Speed",
        "attr": "compressor_speed",
        "unit": REVOLUTIONS_PER_MINUTE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "brine_circulation_pump",
        "name": "Brine Circulation Pump",
        "attr": "brine_circulation_pump",
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "production_circulation_pump",
        "name": "Production Circulation Pump",
        "attr": "production_circulation_pump",
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "act_vent_rpm",
        "name": "Act Vent RPM",
        "attr": "act_vent_rpm",
        "unit": REVOLUTIONS_PER_MINUTE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "total_active_power",
        "name": "Total Active Power",
        "attr": "total_active_power",
        "unit": UnitOfPower.WATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.POWER,
    },
    {
        "key": "energy_usage",
        "name": "Energy Usage",
        "attr": "energy_usage",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "device_class": SensorDeviceClass.ENERGY,
    },
    {
        "key": "energy_delivered",
        "name": "Energy Delivered",
        "attr": "energy_delivered",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "device_class": SensorDeviceClass.ENERGY,
    },
    {
        "key": "import_energy",
        "name": "Import Energy",
        "attr": "import_energy",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "device_class": SensorDeviceClass.ENERGY,
    },
    {
        "key": "export_energy",
        "name": "Export Energy",
        "attr": "export_energy",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "device_class": SensorDeviceClass.ENERGY,
    },
    {
        "key": "spf",
        "name": "Seasonal Performance Factor (SPF)",
        "attr": "spf",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "overheating",
        "name": "Overheating",
        "attr": "overheating",
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "key": "position_expansion_ventil",
        "name": "Position Expansion Ventil",
        "attr": "position_expansion_ventil",
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "number_of_starts",
        "name": "Number of Starts",
        "attr": "number_of_starts",
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    {
        "key": "operating_hours",
        "name": "Operating Hours",
        "attr": "operating_hours",
        "unit": UnitOfTime.HOURS,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.DURATION,
    },
]

ONOFF_SENSOR_DEFS = [
    {
        "key": "dg1",
        "name": "Direct Outlet (DG1)",
        "attr": "dg1",
        "device_class": BinarySensorDeviceClass.RUNNING,
    },
    {
        "key": "sg2",
        "name": "Mixture Outlet (SG2)",
        "attr": "sg2",
        "device_class": BinarySensorDeviceClass.RUNNING,
    },
    {
        "key": "sg3",
        "name": "Mixture Outlet (SG3)",
        "attr": "sg3",
        "device_class": BinarySensorDeviceClass.RUNNING,
    },
    {
        "key": "sg4",
        "name": "Mixture Outlet (SG4)",
        "attr": "sg4",
        "device_class": BinarySensorDeviceClass.RUNNING,
    },
    {
        "key": "warmwater",
        "name": "Warm Water",
        "attr": "warmwater",
        "device_class": BinarySensorDeviceClass.HEAT,
    },
    {
        "key": "alarm_active",
        "name": "Alarm Active",
        "attr": "alarm_active",
        "device_class": BinarySensorDeviceClass.PROBLEM,
    },
    {
        "key": "current_heating_pump_state",
        "name": "Current Heating Pump State",
        "attr": "current_heating_pump_state",
        "device_class": BinarySensorDeviceClass.RUNNING,
    },
    {
        "key": "current_heating_state",
        "name": "Current Heating State",
        "attr": "current_heating_state",
        "device_class": BinarySensorDeviceClass.HEAT,
    },
    {
        "key": "active_requests_ww",
        "name": "Active WW Request",
        "attr": "active_requests_ww",
        "device_class": BinarySensorDeviceClass.HEAT,
    },
]

HEATLOADING_SENSOR_DEFS = [
    {
        "key": "heatloading_active",
        "name": "Heatloading Active",
        "value_fn": lambda device: bool(device.heatloading_status.heatloading_active),
        "exists_fn": lambda device: device.heatloading_status is not None,
    },
    {
        "key": "domestic_hot_water",
        "name": "Domestic Hot Water",
        "value_fn": lambda device: bool(
            device.heatloading_status.configurations.get("domestic_hot_water")
        ),
        "exists_fn": lambda device: (
            device.heatloading_status is not None
            and device.heatloading_status.configurations is not None
            and "domestic_hot_water" in device.heatloading_status.configurations
        ),
    },
    {
        "key": "heatloading_for_heating",
        "name": "Heatloading For Heating",
        "value_fn": lambda device: bool(
            device.heatloading_status.configurations.get("heatloading_for_heating")
        ),
        "exists_fn": lambda device: (
            device.heatloading_status is not None
            and device.heatloading_status.configurations is not None
            and "heatloading_for_heating" in device.heatloading_status.configurations
        ),
    },
]

FRIENDLY_TEXT_SENSOR_DEFS = [
    {
        "key": "operation_mode_text",
        "name": "Operation Mode",
        "value_fn": get_friendly_operation_mode_text,
    },
    {
        "key": "heating_mode_text",
        "name": "Heating Mode",
        "value_fn": get_friendly_heating_mode_text,
    },
]

sensor_list: list[EpluconSensorEntityDescription] = []
for sensor_def in RAW_SENSOR_DEFS:
    attr = sensor_def["attr"]
    sensor_list.append(
        EpluconSensorEntityDescription(
            key=sensor_def["key"],
            name=sensor_def["name"],
            device_class=sensor_def.get("device_class"),
            native_unit_of_measurement=sensor_def.get("unit"),
            state_class=sensor_def.get("state_class"),
            value_fn=lambda device, attr=attr: normalize_number(
                get_common_value(device, attr)
            ),
            exists_fn=lambda device, attr=attr: (
                get_common_value(device, attr) is not None
            ),
        )
    )

for sensor_def in FRIENDLY_TEXT_SENSOR_DEFS:
    sensor_list.append(
        EpluconSensorEntityDescription(
            key=sensor_def["key"],
            name=sensor_def["name"],
            value_fn=sensor_def["value_fn"],
            exists_fn=lambda device: (
                getattr(
                    getattr(device, "realtime_info", None),
                    "common",
                    None,
                )
                is not None
            ),
        )
    )

binary_sensor_list: list[EpluconBinarySensorEntityDescription] = []
for sensor_def in ONOFF_SENSOR_DEFS:
    attr = sensor_def["attr"]
    binary_sensor_list.append(
        EpluconBinarySensorEntityDescription(
            key=sensor_def["key"],
            name=sensor_def["name"],
            device_class=sensor_def.get("device_class"),
            value_fn=lambda device, attr=attr: normalize_bool(
                get_common_value(device, attr)
            ),
            exists_fn=lambda device, attr=attr: (
                get_common_value(device, attr) is not None
            ),
        )
    )

for sensor_def in HEATLOADING_SENSOR_DEFS:
    binary_sensor_list.append(
        EpluconBinarySensorEntityDescription(
            key=sensor_def["key"],
            name=sensor_def["name"],
            value_fn=sensor_def["value_fn"],
            exists_fn=sensor_def["exists_fn"],
        )
    )

SENSORS = tuple(sensor_list)
BINARY_SENSORS = tuple(binary_sensor_list)
