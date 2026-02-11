"""Number platform for the Webasto Unite Modbus integration.

This module defines number entities for writeable Modbus registers such as
failsafe current, failsafe timeout and dynamic charging current limit.  Each
entity uses the ``WebastoUniteCoordinator`` to read its current value and
write updates to the charger.  The ranges and units are based on the
published Modbus specification for the Webasto Unite wallbox.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfElectricCurrent, UnitOfTime
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WebastoUniteCoordinator, SENSOR_UNITS


@dataclass
class WebastoUniteNumberDescription(NumberEntityDescription):
    """Describes a writeable Webasto Unite number entity."""

    # Register address used for writing
    address: int


NUMBER_DESCRIPTIONS: tuple[WebastoUniteNumberDescription, ...] = (
    WebastoUniteNumberDescription(
        key="failsafe_current",
        name="Failsafe Current",
        address=2000,
        min_value=6,
        max_value=32,
        step=1,
        mode=NumberMode.SLIDER,
    ),
    WebastoUniteNumberDescription(
        key="failsafe_timeout",
        name="Failsafe Timeout",
        address=2002,
        min_value=0,
        max_value=3600,
        step=1,
        mode=NumberMode.SLIDER,
    ),
    WebastoUniteNumberDescription(
        key="charging_current_limit",
        name="Charging Current Limit",
        address=5004,
        min_value=0,
        max_value=32,
        step=1,
        mode=NumberMode.SLIDER,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Webasto Unite numbers based on a config entry."""
    coordinator: WebastoUniteCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[WebastoUniteNumber] = []
    for description in NUMBER_DESCRIPTIONS:
        if description.key in coordinator.data:
            entities.append(WebastoUniteNumber(coordinator, description))
    async_add_entities(entities)


class WebastoUniteNumber(CoordinatorEntity[WebastoUniteCoordinator], NumberEntity):
    """Representation of a Webasto Unite Modbus number entity."""

    entity_description: WebastoUniteNumberDescription

    def __init__(self, coordinator: WebastoUniteCoordinator, description: WebastoUniteNumberDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"
        self._attr_name = description.name or description.key.replace("_", " ").title()
        # Set unit of measurement from SENSOR_UNITS if defined
        unit = SENSOR_UNITS.get(description.key)
        if unit is not None:
            self._attr_native_unit_of_measurement = unit

        # Pass through other description values (min_value, max_value, step, mode)
        self._attr_native_min_value = description.min_value
        self._attr_native_max_value = description.max_value
        self._attr_native_step = description.step
        self._attr_mode = description.mode

    @property
    def native_value(self) -> Optional[float]:
        """Return the current value from the coordinator."""
        value = self.coordinator.data.get(self.entity_description.key)
        # Ensure return type is float for number entities
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Write a new value to the charger holding register."""
        # Round the value to an integer for writing
        int_value = int(round(value))
        await self.coordinator.async_write_holding_register(
            address=self.entity_description.address,
            value=int_value,
        )
