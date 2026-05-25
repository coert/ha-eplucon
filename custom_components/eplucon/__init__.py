from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any, TypeVar

from homeassistant.components.frontend import add_extra_js_url, remove_extra_js_url
from homeassistant.components.http import StaticPathConfig
from dacite import from_dict
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .brine import BrineMonthlyStats, BrineStatsConfig, get_month_key
from .const import (
    BRINE_STATS_STORAGE_VERSION,
    CONF_BRINE_PUMP_THRESHOLD,
    CONF_BRINE_SAMPLE_INTERVAL_MINUTES,
    CONF_BRINE_VALID_MINUTES,
    CONF_ENABLE_BRINE_VALIDITY_STATS,
    DEFAULT_BRINE_PUMP_THRESHOLD,
    DEFAULT_BRINE_SAMPLE_INTERVAL_MINUTES,
    DEFAULT_BRINE_VALID_MINUTES,
    DEFAULT_ENABLE_BRINE_VALIDITY_STATS,
    DOMAIN,
    EPLUCON_PORTAL_URL,
    MANUFACTURER,
    PLATFORMS,
    SUPPORTED_TYPES,
)
from .eplucon_api.DTO.DeviceDTO import DeviceDTO
from .eplucon_api.eplucon_client import BASE_URL, ApiError, EpluconApi

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)
_RetryT = TypeVar("_RetryT")
FRONTEND_STATIC_URL = f"/{DOMAIN}_static"
FRONTEND_CARD_URL = f"{FRONTEND_STATIC_URL}/eplucon-card.js"
_FRONTEND_STATIC_REGISTERED = f"{DOMAIN}_frontend_static_registered"
_FRONTEND_MODULE_LOADED = f"{DOMAIN}_frontend_module_loaded"
_FRONTEND_DIRECTORY = Path(__file__).parent / "frontend"


def is_valid_realtime_info(info: Any) -> bool:
    """Return False if the payload is clearly invalid."""
    if info is None or info.common is None:
        return False

    indicators = [
        info.common.indoor_temperature,
        info.common.outdoor_temperature,
        info.common.operating_hours,
    ]
    return any(value not in (None, 0, "0", "0.0") for value in indicators)


async def fetch_with_retry(func, *args, retries: int = 3, delay: int = 2):
    """Retry transient API calls a small number of times."""
    for attempt in range(1, retries + 1):
        try:
            return await func(*args)
        except Exception as err:
            if attempt == retries:
                raise
            _LOGGER.warning(
                "API call %s failed (%s), retry %d/%d",
                func.__name__,
                err,
                attempt,
                retries,
            )
            await asyncio.sleep(delay)

    raise RuntimeError("Retry loop exited without returning or raising")


def coerce_float(value: Any) -> float | None:
    """Convert DTO values to floats where possible."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def _async_register_frontend_resources(hass: HomeAssistant) -> None:
    """Register static paths and the dashboard card module once."""
    if not hass.data.get(_FRONTEND_STATIC_REGISTERED):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    FRONTEND_STATIC_URL,
                    str(_FRONTEND_DIRECTORY),
                    cache_headers=False,
                )
            ]
        )
        hass.data[_FRONTEND_STATIC_REGISTERED] = True

    if not hass.data.get(_FRONTEND_MODULE_LOADED):
        add_extra_js_url(hass, FRONTEND_CARD_URL)
        hass.data[_FRONTEND_MODULE_LOADED] = True


def _async_unregister_frontend_resources(hass: HomeAssistant) -> None:
    """Remove the frontend card module when the integration is unloaded."""
    if hass.data.get(_FRONTEND_MODULE_LOADED):
        remove_extra_js_url(hass, FRONTEND_CARD_URL)
        hass.data[_FRONTEND_MODULE_LOADED] = False


async def device_dict_to_dto(device: DeviceDTO | dict[str, Any]) -> DeviceDTO:
    """Normalize persisted config-entry device payloads to DTOs."""
    if isinstance(device, dict):
        return from_dict(data_class=DeviceDTO, data=device)
    return device


class EpluconDataUpdateCoordinator(DataUpdateCoordinator[list[DeviceDTO]]):
    """Coordinate Eplucon API updates and derived brine statistics."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: EpluconApi,
        devices: list[DeviceDTO],
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Eplucon devices",
            update_method=self._async_update_data,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.client = client
        self._devices = devices
        self._last_good_devices: dict[int, DeviceDTO] = {}
        self._brine_store: Store[dict[str, Any]] = Store(
            hass,
            BRINE_STATS_STORAGE_VERSION,
            f"{DOMAIN}_{entry.entry_id}_brine_stats",
        )
        self._brine_stats: dict[str, BrineMonthlyStats] = {}

    @property
    def brine_feature_enabled(self) -> bool:
        """Return if the optional brine validity entities are enabled."""
        return bool(
            self.entry.options.get(
                CONF_ENABLE_BRINE_VALIDITY_STATS,
                DEFAULT_ENABLE_BRINE_VALIDITY_STATS,
            )
        )

    @property
    def brine_config(self) -> BrineStatsConfig:
        """Return the current brine statistics configuration."""
        return BrineStatsConfig(
            pump_threshold=float(
                self.entry.options.get(
                    CONF_BRINE_PUMP_THRESHOLD,
                    DEFAULT_BRINE_PUMP_THRESHOLD,
                )
            ),
            valid_after=timedelta(
                minutes=int(
                    self.entry.options.get(
                        CONF_BRINE_VALID_MINUTES,
                        DEFAULT_BRINE_VALID_MINUTES,
                    )
                )
            ),
            sample_interval=timedelta(
                minutes=int(
                    self.entry.options.get(
                        CONF_BRINE_SAMPLE_INTERVAL_MINUTES,
                        DEFAULT_BRINE_SAMPLE_INTERVAL_MINUTES,
                    )
                )
            ),
        )

    async def async_initialize(self) -> None:
        """Load persisted brine statistics before the first refresh."""
        if not self.brine_feature_enabled:
            return

        now = dt_util.now()
        stored_stats = await self._brine_store.async_load() or {}
        self._brine_stats = {
            str(device_id): BrineMonthlyStats.from_dict(payload, now=now)
            for device_id, payload in stored_stats.items()
            if isinstance(payload, dict)
        }

    def is_brine_valid(self, device_id: int | str) -> bool:
        """Return if brine circulation has been active long enough."""
        stats = self._brine_stats.get(str(device_id))
        if stats is None:
            return False
        return stats.is_valid(dt_util.now(), self.brine_config)

    def get_valid_brine_temperature(
        self, device_id: int | str, brine_temperature: float | None
    ) -> float | None:
        """Return the current brine input temperature when valid."""
        stats = self._brine_stats.get(str(device_id))
        if stats is None:
            return None
        return stats.valid_temperature(
            dt_util.now(), self.brine_config, brine_temperature
        )

    def get_monthly_brine_mean(self, device_id: int | str) -> float | None:
        """Return the persisted monthly mean brine temperature."""
        stats = self._brine_stats.get(str(device_id))
        if stats is None:
            return None
        return stats.monthly_mean

    def get_monthly_brine_sample_count(self, device_id: int | str) -> int:
        """Return the number of monthly brine samples."""
        stats = self._brine_stats.get(str(device_id))
        if stats is None:
            return 0
        return stats.sample_count

    def get_monthly_brine_month_key(self, device_id: int | str) -> str | None:
        """Return the month bucket used for the current statistics."""
        stats = self._brine_stats.get(str(device_id))
        if stats is None:
            return None
        return stats.month_key

    async def _async_update_data(self) -> list[DeviceDTO]:
        """Fetch Eplucon data from the API."""
        refreshed_devices: list[DeviceDTO] = []

        try:
            for entry_device in self._devices:
                if entry_device.type not in SUPPORTED_TYPES:
                    _LOGGER.debug(
                        "Device %s with type %s is not supported yet. Skipping",
                        entry_device.name,
                        entry_device.type,
                    )
                    continue

                if entry_device.type == "heat_pump":
                    realtime_info = await fetch_with_retry(
                        self.client.get_realtime_info,
                        entry_device.id,
                    )
                    heatloading_status = await fetch_with_retry(
                        self.client.get_heatpump_heatloading_status,
                        entry_device.id,
                    )

                    if is_valid_realtime_info(realtime_info):
                        entry_device.realtime_info = realtime_info
                        entry_device.heatloading_status = heatloading_status
                        self._last_good_devices[entry_device.id] = entry_device
                    else:
                        _LOGGER.warning(
                            "Invalid realtime data for device %s, keeping last known values",
                            entry_device.id,
                        )
                        last_good = self._last_good_devices.get(entry_device.id)
                        if last_good is not None:
                            entry_device.realtime_info = last_good.realtime_info
                            entry_device.heatloading_status = (
                                last_good.heatloading_status
                            )
                        else:
                            entry_device.realtime_info = realtime_info
                            entry_device.heatloading_status = heatloading_status

                elif entry_device.type == "zones_controller":
                    if entry_device.zone_controller_id is None:
                        _LOGGER.debug(
                            "Zone controller device %s has no parent id, skipping update",
                            entry_device.id,
                        )
                        continue

                    zone_controllers_info = await fetch_with_retry(
                        self.client.get_zone_controllers,
                        entry_device.zone_controller_id,
                    )
                    for zone_controller_info in zone_controllers_info:
                        if zone_controller_info.id == entry_device.id:
                            entry_device.zone_controller_info = zone_controller_info
                            break

                refreshed_devices.append(entry_device)

            if self.brine_feature_enabled:
                await self._async_update_brine_stats(refreshed_devices)

            _LOGGER.debug(
                "Fetched data from Eplucon API for %s devices",
                len(refreshed_devices),
            )
            return refreshed_devices

        except ApiError:
            raise
        except Exception as err:
            _LOGGER.error(
                "Something went wrong when updating Eplucon device data: %s",
                err,
            )
            raise

    async def _async_update_brine_stats(self, devices: list[DeviceDTO]) -> None:
        """Update and persist monthly brine statistics for heat pumps."""
        now = dt_util.now()
        config = self.brine_config
        stats_changed = False

        for device in devices:
            if device.type != "heat_pump" or device.realtime_info is None:
                continue

            device_key = str(device.id)
            stats = self._brine_stats.setdefault(
                device_key,
                BrineMonthlyStats(month_key=get_month_key(now)),
            )
            common = device.realtime_info.common
            stats_changed |= stats.update(
                now=now,
                config=config,
                pump_percentage=coerce_float(common.brine_circulation_pump),
                brine_temperature=coerce_float(common.brine_in_temperature),
            )

        if stats_changed:
            await self._brine_store.async_save(
                {
                    device_id: stats.as_dict()
                    for device_id, stats in self._brine_stats.items()
                }
            )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eplucon from a config entry."""
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    hass.data.setdefault(DOMAIN, {})
    await _async_register_frontend_resources(hass)

    api_token = entry.data["api_token"]
    api_endpoint = entry.data.get("api_endpoint", BASE_URL)
    session = async_get_clientsession(hass)
    client = EpluconApi(api_token, api_endpoint, session)

    dto_devices = await register_devices(entry.data["devices"], entry, hass, client)

    coordinator = EpluconDataUpdateCoordinator(hass, entry, client, dto_devices)
    await coordinator.async_initialize()
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _build_zone_device_name(controller_name: str, zone_name: str) -> str:
    """Build a stable zone device name without duplicating identical labels."""
    normalized_controller_name = controller_name.strip()
    normalized_zone_name = zone_name.strip()

    if not normalized_controller_name:
        return normalized_zone_name
    if not normalized_zone_name:
        return normalized_controller_name
    if normalized_controller_name.casefold() == normalized_zone_name.casefold():
        return normalized_zone_name

    return f"{normalized_controller_name}: {normalized_zone_name}"


async def register_device(
    device: DeviceDTO, entry: ConfigEntry, hass_device_registry: DeviceRegistry
) -> None:
    """Register a device in the Home Assistant device registry."""
    device_entry = hass_device_registry.async_get_or_create(
        configuration_url=EPLUCON_PORTAL_URL,
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, device.account_module_index)},
        manufacturer=MANUFACTURER,
        suggested_area="Utility Room",
        name=device.name,
        model=device.type,
    )
    if device_entry.name_by_user is None and device_entry.name != device.name:
        hass_device_registry.async_update_device(device_entry.id, name=device.name)


async def register_devices(
    devices: list[dict[str, Any] | DeviceDTO],
    entry: ConfigEntry,
    hass: HomeAssistant,
    client: EpluconApi,
) -> list[DeviceDTO]:
    """Register config-entry devices and expand zone controllers to child devices."""
    hass_device_registry = device_registry.async_get(hass)

    updated_devices: list[DeviceDTO] = []
    for device in devices:
        dto_device = await device_dict_to_dto(device)

        if (
            dto_device.type == "zones_controller"
            and dto_device.zone_controller_id is None
        ):
            zone_controllers_info = await fetch_with_retry(
                client.get_zone_controllers,
                dto_device.id,
            )
            for index, zone_controller_info in enumerate(zone_controllers_info):
                zone_device = DeviceDTO(
                    id=zone_controller_info.id,
                    account_module_index=f"{dto_device.account_module_index}{index}",
                    name=_build_zone_device_name(
                        dto_device.name,
                        zone_controller_info.name,
                    ),
                    type=dto_device.type,
                    zone_controller_id=dto_device.id,
                    zone_controller_info=zone_controller_info,
                )
                await register_device(zone_device, entry, hass_device_registry)
                updated_devices.append(zone_device)
            continue

        await register_device(dto_device, entry, hass_device_registry)
        updated_devices.append(dto_device)

    _LOGGER.debug(
        "Registered devices in device registry: %s",
        [device.name for device in updated_devices],
    )
    return updated_devices


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Eplucon config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            _async_unregister_frontend_resources(hass)

    return unload_ok
