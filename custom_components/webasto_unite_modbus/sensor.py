"""Sensor platform for the Webasto Unite Modbus integration.

This module defines a set of sensor entities to expose the read‑only
Modbus registers from the Webasto Unite charger.  Each sensor
corresponds to a register defined in ``coordinator.py`` and is
described by a ``WebastoUniteSensorDescription``.  The entities
subscribe to a shared ``WebastoUniteCoordinator`` so that all
registers are polled in a single update and values are cached.

The sensors handle string, numeric and enumerated values and
optionally perform simple conversions (e.g. state codes into human
readable names, or YYMMDD/HHMMSS integers into ISO formatted dates
and times).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfEnergy,
    UnitOfTime,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import (
    WebastoUniteCoordinator,
    CHARGE_POINT_STATE,
    SENSOR_UNITS,
)


@dataclass
class WebastoUniteSensorDescription(SensorEntityDescription):
    """Describes Webasto Unite sensor entity."""

    # Key of the underlying data in the coordinator
    key: str
    # Optional callable to convert raw values into a human readable form
    value_fn: Optional[Callable[[Any], Any]] = None


def _decode_date(value: Any) -> Optional[str]:
    """Convert a YYMMDD integer into an ISO date string.

    The charger encodes the date using two digits for year, month and day.
    We assume all years >= 0 refer to the 21st century.  Invalid values
    return None.
    """
    if value is None:
        return None
    try:
        # Ensure integer
        value_int = int(value)
    except (ValueError, TypeError):
        return None
    year = value_int // 10000
    month = (value_int // 100) % 100
    day = value_int % 100
    # Guard against bogus values
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    year_full = 2000 + year if year < 80 else 1900 + year
    return f"{year_full:04d}-{month:02d}-{day:02d}"


def _decode_time(value: Any) -> Optional[str]:
    """Convert an HHMMSS integer into a time string."""
    if value is None:
        return None
    try:
        value_int = int(value)
    except (ValueError, TypeError):
        return None
    hour = value_int // 10000
    minute = (value_int // 100) % 100
    second = value_int % 100
    if not (0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60):
        return None
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def _decode_state(value: Any) -> Any:
    """Map a charge point state code to a descriptive string."""
    return CHARGE_POINT_STATE.get(value, value)


def _decode_phases(value: Any) -> Any:
    """Map the number of phases to a descriptive string."""
    if value is None:
        return None
    try:
        phases = int(value)
    except (ValueError, TypeError):
        return value
    if phases == 0:
        return "single-phase"
    if phases == 1:
        return "three-phase"
    return value


# List of all sensor descriptions.  For each entry specify the key and
# optionally a value transformation function.  Names and icons are
# chosen to be descriptive but can be adjusted by the user in the UI.
SENSOR_DESCRIPTIONS: tuple[WebastoUniteSensorDescription, ...] = (
    WebastoUniteSensorDescription(
        key="serial_number",
        name="Serial Number",
    ),
    WebastoUniteSensorDescription(
        key="charge_point_id",
        name="Charge Point ID",
    ),
    WebastoUniteSensorDescription(
        key="brand",
        name="Brand",
    ),
    WebastoUniteSensorDescription(
        key="model",
        name="Model",
    ),
    WebastoUniteSensorDescription(
        key="firmware_version",
        name="Firmware Version",
    ),
    WebastoUniteSensorDescription(
        key="date",
        name="Date",
        value_fn=_decode_date,
    ),
    WebastoUniteSensorDescription(
        key="time",
        name="Time",
        value_fn=_decode_time,
    ),
    WebastoUniteSensorDescription(
        key="charge_point_power",
        name="Rated Power",
    ),
    WebastoUniteSensorDescription(
        key="number_of_phases",
        name="Number of Phases",
        value_fn=_decode_phases,
    ),
    WebastoUniteSensorDescription(
        key="charge_point_state",
        name="Charge Point State",
        value_fn=_decode_state,
    ),
    WebastoUniteSensorDescription(
        key="charging_state",
        name="Charging State",
    ),
    WebastoUniteSensorDescription(
        key="equipment_state",
        name="Equipment State",
    ),
    WebastoUniteSensorDescription(
        key="cable_state",
        name="Cable State",
    ),
    WebastoUniteSensorDescription(
        key="fault_code",
        name="Fault Code",
    ),
    WebastoUniteSensorDescription(
        key="current_l1",
        name="Current L1",
    ),
    WebastoUniteSensorDescription(
        key="current_l2",
        name="Current L2",
    ),
    WebastoUniteSensorDescription(
        key="current_l3",
        name="Current L3",
    ),
    WebastoUniteSensorDescription(
        key="voltage_l1",
        name="Voltage L1",
    ),
    WebastoUniteSensorDescription(
        key="voltage_l2",
        name="Voltage L2",
    ),
    WebastoUniteSensorDescription(
        key="voltage_l3",
        name="Voltage L3",
    ),
    WebastoUniteSensorDescription(
        key="active_power_total",
        name="Active Power Total",
    ),
    WebastoUniteSensorDescription(
        key="active_power_l1",
        name="Active Power L1",
    ),
    WebastoUniteSensorDescription(
        key="active_power_l2",
        name="Active Power L2",
    ),
    WebastoUniteSensorDescription(
        key="active_power_l3",
        name="Active Power L3",
    ),
    WebastoUniteSensorDescription(
        key="meter_reading",
        name="Meter Reading",
    ),
    WebastoUniteSensorDescription(
        key="session_max_current",
        name="Session Max Current",
    ),
    WebastoUniteSensorDescription(
        key="evse_min_current",
        name="EVSE Min Current",
    ),
    WebastoUniteSensorDescription(
        key="evse_max_current",
        name="EVSE Max Current",
    ),
    WebastoUniteSensorDescription(
        key="cable_max_current",
        name="Cable Max Current",
    ),
    WebastoUniteSensorDescription(
        key="charged_energy",
        name="Charged Energy",
    ),
    WebastoUniteSensorDescription(
        key="session_start_time",
        name="Session Start Time",
    ),
    WebastoUniteSensorDescription(
        key="session_duration",
        name="Session Duration",
    ),
    WebastoUniteSensorDescription(
        key="session_end_time",
        name="Session End Time",
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Webasto Unite sensors for a config entry."""
    coordinator: WebastoUniteCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[WebastoUniteSensor] = []
    for description in SENSOR_DESCRIPTIONS:
        # Only create the sensor if the coordinator has initial data for this key
        if description.key in coordinator.data:
            entities.append(WebastoUniteSensor(coordinator, description))

    async_add_entities(entities)


class WebastoUniteSensor(CoordinatorEntity[WebastoUniteCoordinator], SensorEntity):
    """Representation of a Webasto Unite Modbus sensor."""

    entity_description: WebastoUniteSensorDescription

    def __init__(self, coordinator: WebastoUniteCoordinator, description: WebastoUniteSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        # Unique ID combines the config entry ID and the sensor key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"
        # Set a friendly name; use description.name or fall back to key
        self._attr_name = description.name or description.key.replace("_", " ").title()
        # Set device info to register this entity with the device
        self._attr_device_info = coordinator.get_device_info()
        # Set device class and state class when possible
        unit = SENSOR_UNITS.get(description.key)
        if unit is not None:
            self._attr_native_unit_of_measurement = unit
            # Use measurement state class for numeric units
            self._attr_state_class = SensorStateClass.MEASUREMENT
            # Attempt to set device class based on unit
            if unit == UnitOfElectricCurrent.AMPERE:
                self._attr_device_class = SensorDeviceClass.CURRENT
            elif unit == UnitOfElectricPotential.VOLT:
                self._attr_device_class = SensorDeviceClass.VOLTAGE
            elif unit == UnitOfPower.WATT:
                self._attr_device_class = SensorDeviceClass.POWER
            elif unit == UnitOfEnergy.KILO_WATT_HOUR:
                self._attr_device_class = SensorDeviceClass.ENERGY
            elif unit == UnitOfTime.SECONDS:
                self._attr_device_class = SensorDeviceClass.DURATION

    @property
    def native_value(self) -> Any:
        """Return the sensor value from the coordinator, applying any conversion."""
        value = self.coordinator.data.get(self.entity_description.key)
        if (fn := self.entity_description.value_fn) is not None:
            return fn(value)
        return value
