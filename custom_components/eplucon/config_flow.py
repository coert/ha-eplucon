import logging
import inspect
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client

# from homeassistant.data_entry_flow import FlowResult
from .const import (
    CONF_BRINE_PUMP_THRESHOLD,
    CONF_BRINE_SAMPLE_INTERVAL_MINUTES,
    CONF_BRINE_VALID_MINUTES,
    CONF_ENABLE_BRINE_VALIDITY_STATS,
    DEFAULT_BRINE_PUMP_THRESHOLD,
    DEFAULT_BRINE_SAMPLE_INTERVAL_MINUTES,
    DEFAULT_BRINE_VALID_MINUTES,
    DEFAULT_ENABLE_BRINE_VALIDITY_STATS,
    DOMAIN,
    SUPPORTED_TYPES,
)
from .eplucon_api.eplucon_client import BASE_URL, ApiAuthError, ApiError, EpluconApi

_LOGGER = logging.getLogger(__name__)

# Define the schema for the user input (API token)
DATA_SCHEMA = vol.Schema(
    {
        vol.Required("api_token"): str,
        vol.Required("api_endpoint", default=BASE_URL): str,
    }
)


class EpluconConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eplucon."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        _LOGGER.debug("Starting Eplucon config flow")

        if user_input is not None:
            # Attempt to connect to the API using the provided API token & endpoint
            api_token: str = user_input["api_token"]
            api_endpoint: str = user_input["api_endpoint"]
            client = EpluconApi(
                api_token,
                api_endpoint,
                aiohttp_client.async_get_clientsession(self.hass),
            )

            try:
                devices = await client.get_devices()

                _LOGGER.debug(f"Received the following devices from API: {devices}")

                unsupported_devices = [
                    device for device in devices if device.type not in SUPPORTED_TYPES
                ]
                for device in unsupported_devices:
                    _LOGGER.warning(
                        f"Device {device.name} with type {device.type} is not supported yet. Skipping..."
                    )
                devices = [
                    device for device in devices if device.type in SUPPORTED_TYPES
                ]

                if len(devices) > 0:
                    return self.async_create_entry(
                        title="Eplucon",
                        data={
                            "devices": devices,
                            "api_token": api_token,
                            "api_endpoint": api_endpoint,
                        },
                    )

                errors["base"] = "no-devices"

            except ApiAuthError:
                # Handle authentication error
                _LOGGER.info("Authentication failed with the provided API token")
                errors["base"] = "auth"

            except ApiError:
                # Handle general API error
                _LOGGER.info("Failed to fetch devices from Eplucon API")
                errors["base"] = "api"

            except Exception as e:
                # Handle any other unexpected exceptions
                _LOGGER.exception("Unexpected exception: %s", e)
                errors["base"] = "unknown"

        # If the user input is not valid or an error occurred, show the form again with the error message
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return EpluconOptionsFlowHandler(config_entry)


class EpluconOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Eplucon options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize Eplucon options flow."""
        self.config_entry = config_entry

    def _build_options_schema(self) -> vol.Schema:
        """Build the options schema with current values."""
        return vol.Schema(
            {
                vol.Required(
                    "api_token",
                    default=self.config_entry.data.get("api_token"),
                ): str,
                vol.Required(
                    "api_endpoint",
                    default=self.config_entry.data.get("api_endpoint", BASE_URL),
                ): str,
                vol.Required(
                    CONF_ENABLE_BRINE_VALIDITY_STATS,
                    default=self.config_entry.options.get(
                        CONF_ENABLE_BRINE_VALIDITY_STATS,
                        DEFAULT_ENABLE_BRINE_VALIDITY_STATS,
                    ),
                ): bool,
                vol.Required(
                    CONF_BRINE_PUMP_THRESHOLD,
                    default=self.config_entry.options.get(
                        CONF_BRINE_PUMP_THRESHOLD,
                        DEFAULT_BRINE_PUMP_THRESHOLD,
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
                vol.Required(
                    CONF_BRINE_VALID_MINUTES,
                    default=self.config_entry.options.get(
                        CONF_BRINE_VALID_MINUTES,
                        DEFAULT_BRINE_VALID_MINUTES,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
                vol.Required(
                    CONF_BRINE_SAMPLE_INTERVAL_MINUTES,
                    default=self.config_entry.options.get(
                        CONF_BRINE_SAMPLE_INTERVAL_MINUTES,
                        DEFAULT_BRINE_SAMPLE_INTERVAL_MINUTES,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
            }
        )

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        _LOGGER.debug("%s", inspect.currentframe().f_code.co_name)  # type: ignore[union-attr]
        """Manage the options for the integration."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # If the user has provided new data, update the config entry
            api_token = str(user_input.get("api_token"))
            api_endpoint = user_input.get("api_endpoint")

            # Revalidate the API token to ensure it's correct
            client = EpluconApi(
                api_token,
                api_endpoint,
                aiohttp_client.async_get_clientsession(self.hass),
            )

            try:
                devices = await client.get_devices()

                # Skip unsupported devices
                unsupported_devices = [
                    device for device in devices if device.type not in SUPPORTED_TYPES
                ]
                for device in unsupported_devices:
                    _LOGGER.debug(
                        f"Device {device.name} with type {device.type} is not supported yet. Skipping..."
                    )
                devices = [
                    device for device in devices if device.type in SUPPORTED_TYPES
                ]

                if len(devices) > 0:
                    # Update the configuration entry with the new API token and devices
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={
                            "api_token": api_token,
                            "api_endpoint": api_endpoint,
                            "devices": devices,
                        },
                    )
                    return self.async_create_entry(
                        title="",
                        data={
                            CONF_ENABLE_BRINE_VALIDITY_STATS: user_input[
                                CONF_ENABLE_BRINE_VALIDITY_STATS
                            ],
                            CONF_BRINE_PUMP_THRESHOLD: user_input[
                                CONF_BRINE_PUMP_THRESHOLD
                            ],
                            CONF_BRINE_VALID_MINUTES: user_input[
                                CONF_BRINE_VALID_MINUTES
                            ],
                            CONF_BRINE_SAMPLE_INTERVAL_MINUTES: user_input[
                                CONF_BRINE_SAMPLE_INTERVAL_MINUTES
                            ],
                        },
                    )

                errors["base"] = "no-devices"

            except ApiAuthError:
                # Handle authentication error
                _LOGGER.info("Authentication failed with the provided API token")
                errors["base"] = "auth"

            except ApiError:
                # Handle general API error
                _LOGGER.info("Failed to fetch devices from Eplucon API")
                errors["base"] = "api"

            except Exception as e:
                # Handle any other unexpected exceptions
                _LOGGER.exception("Unexpected exception: %s", e)
                errors["base"] = "unknown"

        # Show the options form with the current API token as the default value
        return self.async_show_form(
            step_id="init",
            data_schema=self._build_options_schema(),
            errors=errors,
        )
