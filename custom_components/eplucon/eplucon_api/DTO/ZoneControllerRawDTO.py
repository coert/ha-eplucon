from dataclasses import dataclass
from typing import Any

from .ZoneControllerRawZoneDTO import ZoneControllerRawZoneDTO


@dataclass
class ZoneControllerRawDTO:
    zone: ZoneControllerRawZoneDTO
    description: dict[str, Any]
    mode: dict[str, Any]
    schedule: dict[str, Any]
    actuators: list
    underfloor: dict[str, Any]
    windowsSensors: list
    additionalContacts: list
    color: str

    @property
    def windows_sensors(self) -> list:
        return self.windowsSensors

    @property
    def additional_contacts(self) -> list:
        return self.additionalContacts
