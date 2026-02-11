"""Sensors for Webasto Unite Modbus."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CHARGE_POINT_STATE, SENSOR_UNITS, WebastoUniteCoordinator


@dataclass(frozen=True, kw_only=True)
class WebastoUniteSensorDescription(SensorEntityDescription):
    """Webasto Unite sensor description."""


SENSOR_DESCRIPTIONS: tuple[WebastoUniteSensorDescription, ...] = (
    WebastoUniteSensorDescription(key="charge_point_state", name="Charge Point State"),
    WebastoUniteSensorDescription(key="charging_state", name="Charging State"),
    WebastoUniteSensorDescription(key="equipment_state", name="Equipment State"),
    WebastoUniteSensorDescription(key="cable_state", name="Cable State"),
    WebastoUniteSensorDescription(key="fault_code", name="EVSE Fault Code"),
    WebastoUniteSensorDescription(key="current_l1", name="Charging Current L1", device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    WebastoUniteSensorDescription(key="current_l2", name="Charging Current L2", device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    WebastoUniteSensorDescription(key="current_l3", name="Charging Current L3", device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    WebastoUniteSensorDescription(key="voltage_l1", name="Charging Voltage L1", device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT),
    WebastoUniteSensorDescription(key="voltage_l2", name="Charging Voltage L2", device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT),
    WebastoUniteSensorDescription(key="voltage_l3", name="Charging Voltage L3", device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT),
    WebastoUniteSensorDescription(key="active_power_total", name="Active Power Total", device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    WebastoUniteSensorDescription(key="meter_reading", name="Meter Reading", device_class=SensorDeviceClass.ENERGY, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, state_class=SensorStateClass.TOTAL_INCREASING),
    WebastoUniteSensorDescription(key="session_max_current", name="Session Max Current", device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    WebastoUniteSensorDescription(key="evse_min_current", name="EVSE Min Current", device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    WebastoUniteSensorDescription(key="evse_max_current", name="EVSE Max Current", device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    WebastoUniteSensorDescription(key="cable_max_current", name="Cable Max Current", device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    WebastoUniteSensorDescription(key="charged_energy", name="Charged Energy", device_class=SensorDeviceClass.ENERGY, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, state_class=SensorStateClass.TOTAL),
    WebastoUniteSensorDescription(key="session_duration", name="Session Duration", device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.SECONDS, state_class=SensorStateClass.MEASUREMENT),
    WebastoUniteSensorDescription(key="failsafe_current", name="Failsafe Current", device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    WebastoUniteSensorDescription(key="failsafe_timeout", name="Failsafe Timeout", native_unit_of_measurement=UnitOfTime.SECONDS, state_class=SensorStateClass.MEASUREMENT),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Webasto Unite sensors."""
    coordinator: WebastoUniteCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(WebastoUniteSensor(coordinator, entry, description) for description in SENSOR_DESCRIPTIONS)


class WebastoUniteSensor(CoordinatorEntity[WebastoUniteCoordinator], SensorEntity):
    """Webasto Unite sensor."""

    entity_description: WebastoUniteSensorDescription

    def __init__(
        self,
        coordinator: WebastoUniteCoordinator,
        entry: ConfigEntry,
        description: WebastoUniteSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_name = description.name
        if description.key in SENSOR_UNITS and not description.native_unit_of_measurement:
            self._attr_native_unit_of_measurement = SENSOR_UNITS[description.key]

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Webasto Unite ({entry.data['host']})",
            "manufacturer": "Webasto",
            "model": "Unite",
        }

    @property
    def native_value(self):
        """Return current sensor value."""
        value = self.coordinator.data.get(self.entity_description.key)
        if self.entity_description.key == "charge_point_state":
            return CHARGE_POINT_STATE.get(value, value)
        return value