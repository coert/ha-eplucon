from dataclasses import dataclass
from typing import Optional

from .RealtimeInfoDTO import RealtimeInfoDTO
from .ZoneControllerInfoDTO import ZoneControllerInfoDTO


@dataclass
class DeviceDTO:
    id: int
    account_module_index: str
    name: str
    type: str
    realtime_info: Optional[RealtimeInfoDTO] = None
    zone_controller_id: int | None = None
    zone_controller_info: Optional[ZoneControllerInfoDTO] = None
