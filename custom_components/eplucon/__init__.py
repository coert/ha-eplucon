import logging
import inspect
from datetime import timedelta
from typing import Any

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
from .eplucon_api.eplucon_client import BASE_URL, ApiError, DeviceDTO, EpluconApi

_LOGGER = logging.getLogger(__name__)

# Time between data updates
UPDATE_INTERVAL = timedelta(seconds=30)


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
            device_id: BrineMonthlyStats.from_dict(payload, now=now)
            for device_id, payload in stored_stats.items()
            if isinstance(payload, dict)
        }

    def is_brine_valid(self, device_id: str) -> bool:
        """Return if brine circulation has been active long enough."""
        stats = self._brine_stats.get(device_id)
        if stats is None:
            return False
        return stats.is_valid(dt_util.now(), self.brine_config)

    def get_valid_brine_temperature(
        self, device_id: str, brine_temperature: float | None
    ) -> float | None:
        """Return the current brine input temperature when valid."""
        stats = self._brine_stats.get(device_id)
        if stats is None:
            return None
        return stats.valid_temperature(
            dt_util.now(), self.brine_config, brine_temperature
        )

    def get_monthly_brine_mean(self, device_id: str) -> float | None:
        """Return the persisted monthly mean brine temperature."""
        stats = self._brine_stats.get(device_id)
        if stats is None:
            return None
        return stats.monthly_mean

    def get_monthly_brine_sample_count(self, device_id: str) -> int:
        """Return the number of monthly brine samples."""
        stats = self._brine_stats.get(device_id)
        if stats is None:
            return 0
        return stats.sample_count

    def get_monthly_brine_month_key(self, device_id: str) -> str | None:
        """Return the month bucket used for the current statistics."""
        stats = self._brine_stats.get(device_id)
        if stats is None:
            return None
        return stats.month_key

    async def _async_update_data(self) -> list[DeviceDTO]:
        """Fetch Eplucon data from API endpoint."""
        _LOGGER.debug("%s", inspect.currentframe().f_code.co_name)  # type: ignore[union-attr]

        try:
            refreshed_devices: list[DeviceDTO] = []

            for entry_device in self._devices:
                if entry_device.type not in SUPPORTED_TYPES:
                    _LOGGER.debug(
                        "Device %s with type %s is not supported yet. Skipping",
                        entry_device.name,
                        entry_device.type,
                    )
                    continue

                if entry_device.type == "heat_pump":
                    entry_device.realtime_info = await self.client.get_realtime_info(
                        entry_device.id
                    )

                elif entry_device.type == "zones_controller":
                    assert entry_device.zone_controller_id is not None
                    zone_controllers_info = await self.client.get_zone_controllers(
                        entry_device.zone_controller_id
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

        except ApiError as err:
            _LOGGER.error("Error fetching data from Eplucon API: %s", err)
            raise
        except Exception as err:
            _LOGGER.error(
                "Something went wrong when updating Eplucon device from API: %s",
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

            stats = self._brine_stats.setdefault(
                device.id,
                BrineMonthlyStats(month_key=get_month_key(now)),
            )
            common = device.realtime_info.common
            stats_changed |= stats.update(
                now=now,
                config=config,
                pump_percentage=common.brine_circulation_pump,
                brine_temperature=common.brine_in_temperature,
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
    _LOGGER.debug("%s", inspect.currentframe().f_code.co_name)  # type: ignore[union-attr]
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    api_token = entry.data["api_token"]
    api_endpoint = entry.data.get("api_endpoint", BASE_URL)

    session = async_get_clientsession(hass)
    client = EpluconApi(api_token, api_endpoint, session)

    dto_devices = await register_devices(entry.data["devices"], entry, hass, client)

    coordinator = EpluconDataUpdateCoordinator(hass, entry, client, dto_devices)
    await coordinator.async_initialize()

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    # Store the coordinator in hass.data, so it's accessible in other parts of the integration
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def register_device(
    device: DeviceDTO, entry: ConfigEntry, hass_device_registry: DeviceRegistry
) -> None:
    _LOGGER.debug("%s", inspect.currentframe().f_code.co_name)  # type: ignore[union-attr]
    hass_device_registry.async_get_or_create(
        configuration_url=EPLUCON_PORTAL_URL,
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, device.account_module_index)},
        manufacturer=MANUFACTURER,
        suggested_area="Utility Room",
        name=device.name,
        model=device.type,
    )


async def register_devices(
    devices: list[dict[str, Any]],
    entry: ConfigEntry,
    hass: HomeAssistant,
    client: EpluconApi,
) -> list[DeviceDTO]:
    _LOGGER.debug("%s", inspect.currentframe().f_code.co_name)  # type: ignore[union-attr]
    hass_device_registry = device_registry.async_get(hass)

    updated_devices: list[DeviceDTO] = []
    for device in devices:
        device = await device_dict_to_dto(device)

        if device.type == "zones_controller" and device.zone_controller_id is None:
            zone_controllers_info = await client.get_zone_controllers(device.id)
            for zidx, zone_controller_info in enumerate(zone_controllers_info):
                zone_device = DeviceDTO(
                    id=zone_controller_info.id,
                    account_module_index=f"{device.account_module_index}{zidx}",
                    name=f"{device.name}: {zone_controller_info.name}",
                    type=device.type,
                    zone_controller_id=device.id,
                    zone_controller_info=zone_controller_info,
                )
                await register_device(zone_device, entry, hass_device_registry)
                updated_devices.append(zone_device)

        else:
            await register_device(device, entry, hass_device_registry)
            updated_devices.append(device)

    _LOGGER.debug(
        "Registered %s devices in device registry",
        [device.name for device in updated_devices],
    )

    return updated_devices


async def device_dict_to_dto(device_dict: DeviceDTO | dict) -> DeviceDTO:
    """
    When retrieving given devices from HASS config flow the entry.data["devices"]
    is type list[DeviceDTO] but on boot this is a list[dict], not sure why and if this is intended,
    but this method will ensure we can parse the correct format here.
    """
    if isinstance(device_dict, dict):
        device_dict = from_dict(data_class=DeviceDTO, data=device_dict)
    return device_dict


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
