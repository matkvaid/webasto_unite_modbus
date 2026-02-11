"""Config flow for Webasto Unite Modbus."""

from __future__ import annotations

import voluptuous as vol
from pymodbus.client import AsyncModbusTcpClient

from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DOMAIN,
)


class WebastoUniteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Webasto Unite Modbus."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial step of the config flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            title = f"Webasto Unite {user_input[CONF_HOST]}"
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:{user_input[CONF_UNIT_ID]}"
            )
            self._abort_if_unique_id_configured()

            client = AsyncModbusTcpClient(host=user_input[CONF_HOST], port=user_input[CONF_PORT])
            try:
                connected = await client.connect()
                if not connected:
                    errors["base"] = "cannot_connect"
                else:
                    # Read from a known register (serial number start) to verify communication
                    result = await client.read_input_registers(
                        address=100, count=1, slave=user_input[CONF_UNIT_ID]
                    )
                    if result.isError():
                        errors["base"] = "invalid_slave"
            except Exception:
                errors["base"] = "cannot_connect"
            finally:
                client.close()

            if not errors:
                return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=255)
                ),
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=2, max=300)
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
