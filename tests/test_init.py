"""Test component setup."""

from homeassistant.setup import async_setup_component

from custom_components.eplucon import _build_zone_device_name
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
