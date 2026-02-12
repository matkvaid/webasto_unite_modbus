"""Switch platform for the Webasto Unite Modbus integration.

This module defines a single switch entity that controls the charger
"alive" register.  Toggling the switch on writes a 1 to register
6000, indicating to the wallbox that the energy management system is
active.  Turning the switch off writes a 0.  The state of the switch
reflects the last value read from the register via the data
coordinator.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WebastoUniteCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the alive switch for a config entry."""
    coordinator: WebastoUniteCoordinator = hass.data[DOMAIN][entry.entry_id]
    # Only add the switch if the coordinator exposes the alive register
    if "alive_register" in coordinator.data:
        async_add_entities([WebastoUniteAliveSwitch(coordinator)])


class WebastoUniteAliveSwitch(CoordinatorEntity[WebastoUniteCoordinator], SwitchEntity):
    """Representation of the Webasto Unite alive switch."""

    def __init__(self, coordinator: WebastoUniteCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_alive_register"
        self._attr_name = "Alive Register"
        # Link to device
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return true if the alive register reports 1."""
        value = self.coordinator.data.get("alive_register")
        return bool(value == 1)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Write a value of 1 to the alive register."""
        await self.coordinator.async_write_holding_register(6000, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Write a value of 0 to the alive register."""
        await self.coordinator.async_write_holding_register(6000, 0)
