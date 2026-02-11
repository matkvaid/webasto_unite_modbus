"""Number entities for Webasto Unite Modbus."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
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
    """Set up Webasto Unite number entities."""
    coordinator: WebastoUniteCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WebastoUniteChargingCurrentLimitNumber(coordinator, entry)])


class WebastoUniteChargingCurrentLimitNumber(CoordinatorEntity[WebastoUniteCoordinator], NumberEntity):
    """Charging current limit control."""

    _attr_has_entity_name = True
    _attr_name = "Charging Current Limit"
    _attr_native_min_value = 0
    _attr_native_max_value = 32
    _attr_native_step = 1
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    def __init__(self, coordinator: WebastoUniteCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_charging_current_limit_number"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Webasto Unite ({entry.data['host']})",
            "manufacturer": "Webasto",
            "model": "Unite",
        }

    @property
    def native_value(self) -> float | None:
        """Return the current configured charging limit."""
        return self.coordinator.data.get("charging_current_limit")

    async def async_set_native_value(self, value: float) -> None:
        """Set charging current limit in register 5004."""
        await self.coordinator.async_write_holding_register(5004, int(value))