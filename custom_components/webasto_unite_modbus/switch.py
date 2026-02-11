"""Switch entities for Webasto Unite Modbus."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WebastoUniteCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Webasto Unite switch entities."""
    coordinator: WebastoUniteCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WebastoUniteAliveRegisterSwitch(coordinator, entry)])


class WebastoUniteAliveRegisterSwitch(CoordinatorEntity[WebastoUniteCoordinator], SwitchEntity):
    """Alive register switch (register 6000)."""

    _attr_has_entity_name = True
    _attr_name = "Alive Register"

    def __init__(self, coordinator: WebastoUniteCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_alive_register"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Webasto Unite ({entry.data['host']})",
            "manufacturer": "Webasto",
            "model": "Unite",
        }

    @property
    def is_on(self) -> bool:
        """Return alive register state."""
        return bool(self.coordinator.data.get("alive_register", 0))

    async def async_turn_on(self, **kwargs) -> None:
        """Write 1 to alive register."""
        await self.coordinator.async_write_holding_register(6000, 1)

    async def async_turn_off(self, **kwargs) -> None:
        """Write 0 to alive register."""
        await self.coordinator.async_write_holding_register(6000, 0)