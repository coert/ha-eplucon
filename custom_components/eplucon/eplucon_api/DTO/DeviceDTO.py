from __future__ import annotations

from dataclasses import dataclass

from .HeatLoadingDTO import HeatLoadingDTO
from .RealtimeInfoDTO import RealtimeInfoDTO
from .ZoneControllerInfoDTO import ZoneControllerInfoDTO


@dataclass
class DeviceDTO:
    id: int
    account_module_index: str
    name: str
    type: str
    realtime_info: RealtimeInfoDTO | None = None
    heatloading_status: HeatLoadingDTO | None = None
    zone_controller_id: int | None = None
    zone_controller_info: ZoneControllerInfoDTO | None = None
