from dataclasses import dataclass
from typing import Union

from .ZoneControllerRawDTO import ZoneControllerRawDTO


@dataclass
class ZoneControllerInfoDTO:
    id: int
    name: str
    set_temperature: Union[float, str]
    mode: str
    raw_data: ZoneControllerRawDTO
    current_temperature: Union[float, str]
