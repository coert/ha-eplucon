import logging
import inspect
from datetime import timedelta
from typing import Any

from dacite import from_dict
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceRegistry

from .const import DOMAIN, EPLUCON_PORTAL_URL, MANUFACTURER, PLATFORMS, SUPPORTED_TYPES
from .eplucon_api.eplucon_client import BASE_URL, ApiError, DeviceDTO, EpluconApi

_LOGGER = logging.getLogger(__name__)

# Time between data updates
UPDATE_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eplucon from a config entry."""
    _LOGGER.debug(f"{inspect.currentframe().f_code.co_name}")  # type: ignore
    api_token = entry.data["api_token"]
    api_endpoint = entry.data.get("api_endpoint", BASE_URL)

    session = async_get_clientsession(hass)
    client = EpluconApi(api_token, api_endpoint, session)

    dto_devices = await register_devices(entry.data["devices"], entry, hass, client)

    async def async_update_data() -> list[DeviceDTO]:
        """Fetch Eplucon data from API endpoint."""
        _LOGGER.debug(f"{inspect.currentframe().f_code.co_name}")  # type: ignore
        try:
            entry_devices = dto_devices

            # For each device, fetch the real-time info and combine it with the device data
            for entry_device in entry_devices:
                # Skip unsupported devices
                if entry_device.type not in SUPPORTED_TYPES:
                    _LOGGER.debug(
                        f"Device {entry_device.name} with type {entry_device.type} is not supported yet. Skipping..."
                    )
                    entry_devices.remove(entry_device)
                    continue

                if entry_device.type == "heat_pump":
                    realtime_info = await client.get_realtime_info(entry_device.id)
                    entry_device.realtime_info = realtime_info

                elif entry_device.type == "zones_controller":
                    assert (
                        entry_device.zone_controller_id is not None
                    ), "Zone controller ID is None, it should have been set in register_devices"
                    zone_controllers_info = await client.get_zone_controllers(
                        entry_device.zone_controller_id
                    )
                    for zone_controller_info in zone_controllers_info:
                        if zone_controller_info.id == entry_device.id:
                            entry_device.zone_controller_info = zone_controller_info

            _LOGGER.debug(
                f"Fetched data from Eplucon API for {len(entry_devices)} devices"
            )
            return entry_devices

        except ApiError as err:
            _LOGGER.error(f"Error fetching data from Eplucon API: {err}")
            raise err

        except Exception as err:
            _LOGGER.error(
                f"Something went wrong when updating Eplucon device from API: {err}"
            )
            raise err

    # Set up the coordinator to manage fetching data from the API
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Eplucon devices",
        update_method=async_update_data,
        update_interval=UPDATE_INTERVAL,
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    # Store the coordinator in hass.data, so it's accessible in other parts of the integration
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def register_device(
    device: DeviceDTO, entry: ConfigEntry, hass_device_registry: DeviceRegistry
):
    _LOGGER.debug(f"{inspect.currentframe().f_code.co_name}")  # type: ignore
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
    _LOGGER.debug(f"{inspect.currentframe().f_code.co_name}")  # type: ignore
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
        f"Registered {[device.name for device in updated_devices]} devices in device registry"
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
