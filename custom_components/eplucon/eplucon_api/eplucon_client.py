from __future__ import annotations

import logging
from typing import Any

import aiohttp
import orjson

from .DTO.CommonInfoDTO import CommonInfoDTO
from .DTO.DeviceDTO import DeviceDTO
from .DTO.HeatLoadingDTO import HeatLoadingDTO
from .DTO.RealtimeInfoDTO import RealtimeInfoDTO
from .DTO.ZoneControllerInfoDTO import ZoneControllerInfoDTO
from .DTO.ZoneControllerRawDTO import ZoneControllerRawDTO
from .DTO.ZoneControllerRawZoneDTO import ZoneControllerRawZoneDTO

BASE_URL = "https://portaal.eplucon.nl/api/v2"

_LOGGER = logging.getLogger(__package__)


class ApiAuthError(Exception):
    """Authentication failed."""


class ApiError(Exception):
    """Generic API error."""


class EpluconApi:
    """Client to talk to the Eplucon API."""

    def __init__(
        self,
        api_token: str,
        api_endpoint: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        if session is None:
            raise RuntimeError("aiohttp ClientSession is required")

        self._base = api_endpoint or BASE_URL
        self._session = session
        self._headers = {
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "Authorization": f"Bearer {api_token}",
        }

    async def get_devices(self) -> list[DeviceDTO]:
        """Return the list of available Eplucon modules."""
        url = f"{self._base}/econtrol/modules"
        _LOGGER.debug("Fetching devices list: %s", url)

        async with self._session.get(url, headers=self._headers) as response:
            data = await response.json()

        self._validate_response(data)

        devices: list[DeviceDTO] = []
        for item in data.get("data", []):
            try:
                devices.append(DeviceDTO(**item))
            except Exception:
                _LOGGER.exception("Failed to parse device DTO: %s", item)

        return devices

    async def get_realtime_info(self, module_id: int) -> RealtimeInfoDTO:
        """Fetch realtime information for a heat pump."""
        url = f"{self._base}/econtrol/modules/{module_id}/get_realtime_info"
        _LOGGER.debug("Fetching realtime info for %s: %s", module_id, url)

        async with self._session.get(url, headers=self._headers) as response:
            data = await response.json()

        self._validate_response(data)

        common = CommonInfoDTO(**data["data"]["common"])
        heatpump = data["data"].get("heatpump", [])
        return RealtimeInfoDTO(common=common, heatpump=heatpump)

    async def get_heatpump_heatloading_status(self, module_id: int) -> HeatLoadingDTO:
        """Fetch heatloading status for a heat pump."""
        url = f"{self._base}/econtrol/modules/{module_id}/heatloading_status"
        _LOGGER.debug("Fetching heatloading status for %s: %s", module_id, url)

        async with self._session.get(url, headers=self._headers) as response:
            data = await response.json()

        self._validate_response(data)
        return HeatLoadingDTO(**data["data"])

    async def get_zone_controllers(self, module_id: int) -> list[ZoneControllerInfoDTO]:
        """Fetch zone controller children for a zone module."""
        url = f"{self._base}/econtrol/modules/{module_id}/zones"
        _LOGGER.debug("Fetching zone controllers for %s: %s", module_id, url)

        async with self._session.get(url, headers=self._headers) as response:
            data = await response.json()

        self._validate_response(data)

        zone_controllers_info: list[ZoneControllerInfoDTO] = []
        for controller in data.get("data", []):
            zone_controller_info = ZoneControllerInfoDTO(**controller)
            raw_data = orjson.loads(controller["raw_data"])
            zone_controller_info.raw_data = ZoneControllerRawDTO(**raw_data)
            zone_controller_info.raw_data.zone = ZoneControllerRawZoneDTO(
                **raw_data["zone"]
            )
            zone_controllers_info.append(zone_controller_info)

        return zone_controllers_info

    @staticmethod
    def _validate_response(response: Any) -> None:
        """Validate the basic response envelope from the API."""
        if not isinstance(response, dict):
            raise ApiError("Invalid API response type")

        if "auth" not in response:
            raise ApiError("Missing 'auth' field in API response")

        if response["auth"] is not True:
            raise ApiAuthError("Authentication failed")
