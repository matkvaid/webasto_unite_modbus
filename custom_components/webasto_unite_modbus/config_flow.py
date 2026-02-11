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
                    # Attempt to read from a known register to verify communication.
                    # Newer firmware exposes the serial number starting at register 100,
                    # while very old firmware uses register 1000.  Try 100 first and
                    # fall back to 1000 if the read returns an error.  Only if both
                    # attempts fail will we abort the flow.
                    test_addresses = [100, 1000]
                    read_success = False
                    for address in test_addresses:
                        result = await client.read_input_registers(
                            address=address,
                            count=1,
                            slave=user_input[CONF_UNIT_ID],
                        )
                        if not result.isError():
                            read_success = True
                            break
                    if not read_success:
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
