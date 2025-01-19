from __future__ import annotations

import inspect
import logging
from typing import Any, Optional

import aiohttp
import orjson

from .DTO.CommonInfoDTO import CommonInfoDTO
from .DTO.DeviceDTO import DeviceDTO
from .DTO.RealtimeInfoDTO import RealtimeInfoDTO
from .DTO.ZoneControllerInfoDTO import ZoneControllerInfoDTO
from .DTO.ZoneControllerRawDTO import ZoneControllerRawDTO
from .DTO.ZoneControllerRawZoneDTO import ZoneControllerRawZoneDTO

BASE_URL = "https://portaal.eplucon.nl/api/v2"
_LOGGER: logging.Logger = logging.getLogger(__package__)


class ApiAuthError(Exception):
    pass


class ApiError(Exception):
    pass


class EpluconApi:
    """Client to talk to Eplucon API"""

    def __init__(
        self,
        api_token: str,
        api_endpoint: str | None,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self._base = api_endpoint if api_endpoint else BASE_URL
        self._session = session or aiohttp.ClientSession()
        self._headers = {
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "Authorization": f"Bearer {api_token}",
        }

        _LOGGER.debug("Initialize Eplucon API client")

    async def close(self) -> None:
        await self._session.close()

    async def get_devices(self) -> list[DeviceDTO]:
        _LOGGER.debug(f"{inspect.currentframe().f_code.co_name}")  # type: ignore
        url = f"{self._base}/econtrol/modules"

        parent_devices = []
        async with self._session.get(url, headers=self._headers) as response:
            devices: dict[str, Any] = await response.json()
            self.validate_response(devices)
            data = devices.get("data", [])
            parent_devices = [DeviceDTO(**device) for device in data]

        # _LOGGER.debug(f"Received the following devices from API: {parent_devices}")

        dto_devices: list[DeviceDTO] = []
        for device in parent_devices:
            _LOGGER.debug(f"Processing device {device.name}")

            if (
                device.type == "zones_controller"
                and device.zone_controller_info is None
            ):
                zone_controllers_info = await self.get_zone_controllers(device.id)

                for zidx, zone_controller_info in enumerate(zone_controllers_info):
                    zone_device = DeviceDTO(
                        id=zone_controller_info.id,
                        account_module_index=f"{device.account_module_index}{zidx}",
                        name=f"{device.name}: {zone_controller_info.name}",
                        type=device.type,
                        zone_controller_id=device.id,
                        zone_controller_info=zone_controller_info,
                    )

                    dto_devices.append(zone_device)
            else:
                dto_devices.append(device)

        _LOGGER.debug([device.name for device in dto_devices])
        return dto_devices

    async def get_realtime_info(self, module_id: int) -> RealtimeInfoDTO:
        url = f"{self._base}/econtrol/modules/{module_id}/get_realtime_info"
        _LOGGER.debug(f"Eplucon Get realtime info for {module_id}: {url}")

        async with self._session.get(url, headers=self._headers) as response:
            data = await response.json()
            self.validate_response(data)

            if "data" not in data:
                raise ApiError("Error from Eplucon API, expecting data key in response.")
            
            else:
                try:
                    common_info = CommonInfoDTO(**data["data"]["common"])
                    heatpump_info = data["data"]["heatpump"]  # Not sure what this could be
                    realtime_info = RealtimeInfoDTO(common=common_info, heatpump=heatpump_info)
                    return realtime_info

                except Exception as e:
                    raise ApiError(f"Error from Eplucon API, unexpected response: {e}")

    async def get_zone_controllers(self, module_id: int) -> list[ZoneControllerInfoDTO]:
        _LOGGER.debug(f"{inspect.currentframe().f_code.co_name}")  # type: ignore

        url = f"{self._base}/econtrol/modules/{module_id}/zones"
        zone_controllers_info = []
        async with self._session.get(url, headers=self._headers) as response:
            data = await response.json()
            # _LOGGER.debug(f"Received zone controllers from API ({url}): {data}")
            self.validate_response(data)

            if "data" not in data:
                _LOGGER.error(f"Failed to parse realtime info: {data}")
                raise ApiError("Error from Eplucon API, expecting data key in response.")

            for controller in data["data"]:
                zone_controller_info = ZoneControllerInfoDTO(**controller)
                raw_data = orjson.loads(controller["raw_data"])
                zone_controller_info.raw_data = ZoneControllerRawDTO(**raw_data)
                zone_controller_info.raw_data.zone = ZoneControllerRawZoneDTO(
                    **raw_data["zone"]
                )
                zone_controllers_info.append(zone_controller_info)

        return zone_controllers_info

    @staticmethod
    def validate_response(response: Any):
        if "auth" not in response:
            raise ApiError("Error from Eplucon API, expecting auth key in response.")

        if not response["auth"]:
            raise ApiAuthError("Authentication failed: Please check the given API key.")
