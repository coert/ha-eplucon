from dataclasses import dataclass
from typing import List

from . import CommonInfoDTO

@dataclass
class RealtimeInfoDTO:
    common: CommonInfoDTO
    heatpump: List  # I'm always getting an empty list here... the docs say array[string].