"""Test component setup."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eplucon import (
    FRONTEND_CARD_URL,
    _build_zone_device_name,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.eplucon.const import DOMAIN


async def test_async_setup(hass):
    """Test the component gets setup."""
    assert await async_setup_component(hass, DOMAIN, {}) is True


def test_build_zone_device_name_deduplicates_identical_labels() -> None:
    """Zone device names should not repeat the same label twice."""
    assert (
        _build_zone_device_name("Thermostaat bg", "Thermostaat bg") == "Thermostaat bg"
    )
    assert (
        _build_zone_device_name("thermostaat bg", "Thermostaat bg") == "Thermostaat bg"
    )
    assert (
        _build_zone_device_name("Verdeler bg", "Thermostaat bg")
        == "Verdeler bg: Thermostaat bg"
    )


async def test_async_setup_entry_registers_frontend_card_resources(hass) -> None:
    """Integration setup should register and load the Eplucon card module."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "api_token": "token",
            "api_endpoint": "https://example.invalid",
            "devices": [],
        },
    )
    entry.add_to_hass(hass)

    coordinator = SimpleNamespace(
        async_initialize=AsyncMock(),
        async_config_entry_first_refresh=AsyncMock(),
    )
    hass.http = SimpleNamespace(async_register_static_paths=AsyncMock())

    with (
        patch("custom_components.eplucon.register_devices", AsyncMock(return_value=[])),
        patch(
            "custom_components.eplucon.EpluconDataUpdateCoordinator",
            return_value=coordinator,
        ),
        patch.object(
            hass.http,
            "async_register_static_paths",
            AsyncMock(),
        ) as register_static_paths,
        patch("custom_components.eplucon.add_extra_js_url") as add_extra_js,
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            AsyncMock(return_value=True),
        ) as forward_entry_setups,
    ):
        assert await async_setup_entry(hass, entry) is True

    register_static_paths.assert_awaited_once()
    add_extra_js.assert_called_once_with(hass, FRONTEND_CARD_URL)
    coordinator.async_initialize.assert_awaited_once()
    coordinator.async_config_entry_first_refresh.assert_awaited_once()
    forward_entry_setups.assert_awaited_once()


async def test_async_unload_entry_unregisters_frontend_card_resources(hass) -> None:
    """Integration unload should remove the frontend card module."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    hass.data[DOMAIN] = {entry.entry_id: object()}
    hass.data[f"{DOMAIN}_frontend_module_loaded"] = True

    with (
        patch.object(
            hass.config_entries,
            "async_unload_platforms",
            AsyncMock(return_value=True),
        ),
        patch("custom_components.eplucon.remove_extra_js_url") as remove_extra_js,
    ):
        assert await async_unload_entry(hass, entry) is True

    remove_extra_js.assert_called_once_with(hass, FRONTEND_CARD_URL)
    assert hass.data[DOMAIN] == {}
