from dataclasses import dataclass, field
from typing import Any


@dataclass
class ZoneControllerRawZoneDTO:
    id: int
    parentId: int
    time: str = field(repr=False)
    duringChange: bool
    index: int
    currentTemperature: int
    setTemperature: int
    flags: dict[str, Any]
    zoneState: str
    signalStrength: int
    batteryLevel: int
    actuatorsOpen: int
    humidity: int | None
    visibility: bool

    @property
    def parent_id(self) -> int:
        return self.parentId

    @property
    def during_change(self) -> bool:
        return self.duringChange

    @property
    def current_temperature(self) -> int:
        return self.currentTemperature

    @property
    def set_temperature(self) -> int:
        return self.setTemperature

    @property
    def zone_state(self) -> str:
        return self.zoneState

    @property
    def signal_strength(self) -> int:
        return self.signalStrength

    @property
    def battery_level(self) -> int:
        return self.batteryLevel

    @property
    def actuators_open(self) -> int:
        return self.actuatorsOpen
