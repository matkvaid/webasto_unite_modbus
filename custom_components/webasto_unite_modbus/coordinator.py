"""Data coordinator for Webasto Unite Modbus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from pymodbus.client import AsyncModbusTcpClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, CONF_UNIT_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegisterDef:
    """Register descriptor."""

    key: str
    address: int
    input_type: str = "input"
    data_type: str = "uint16"
    count: int = 1
    scale: float = 1.0


REGISTER_MAP: tuple[RegisterDef, ...] = (
    RegisterDef("charge_point_state", 1000),
    RegisterDef("charging_state", 1001),
    RegisterDef("equipment_state", 1002),
    RegisterDef("cable_state", 1004),
    RegisterDef("fault_code", 1006),
    RegisterDef("current_l1", 1008, data_type="uint16", scale=0.001),
    RegisterDef("current_l2", 1010, data_type="uint16", scale=0.001),
    RegisterDef("current_l3", 1012, data_type="uint16", scale=0.001),
    RegisterDef("voltage_l1", 1014),
    RegisterDef("voltage_l2", 1016),
    RegisterDef("voltage_l3", 1018),
    RegisterDef("active_power_total", 1020, data_type="uint32"),
    RegisterDef("meter_reading", 1036, data_type="uint32", scale=0.001),
    RegisterDef("session_max_current", 1100),
    RegisterDef("evse_min_current", 1102),
    RegisterDef("evse_max_current", 1104),
    RegisterDef("cable_max_current", 1106),
    RegisterDef("charged_energy", 1502, data_type="uint32", scale=0.001),
    RegisterDef("session_duration", 1508, data_type="uint32"),
    RegisterDef("failsafe_current", 2000, input_type="holding"),
    RegisterDef("failsafe_timeout", 2002, input_type="holding"),
    RegisterDef("charging_current_limit", 5004, input_type="holding"),
    RegisterDef("alive_register", 6000, input_type="holding"),
)


class WebastoUniteCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate Webasto Unite Modbus updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.client = AsyncModbusTcpClient(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            timeout=5,
        )
        self._unit_id = entry.data[CONF_UNIT_ID]

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=entry.data[CONF_SCAN_INTERVAL]),
        )

    async def async_shutdown(self) -> None:
        """Close Modbus client."""
        self.client.close()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest data from charger."""
        if not self.client.connected:
            connected = await self.client.connect()
            if not connected:
                raise UpdateFailed("Could not connect to Webasto Unite")

        data: dict[str, Any] = {
            "last_update": dt_util.utcnow().isoformat(),
        }

        for register in REGISTER_MAP:
            raw_value = await self._read_register(register)
            data[register.key] = self._decode_value(raw_value, register)

        return data

    async def _read_register(self, register: RegisterDef) -> list[int]:
        count = 2 if register.data_type == "uint32" else register.count

        if register.input_type == "holding":
            result = await self.client.read_holding_registers(
                address=register.address, count=count, slave=self._unit_id
            )
        else:
            result = await self.client.read_input_registers(
                address=register.address, count=count, slave=self._unit_id
            )

        if result.isError():
            raise UpdateFailed(f"Read error at register {register.address}: {result}")

        return result.registers

    def _decode_value(self, registers: list[int], register: RegisterDef) -> Any:
        if register.data_type == "uint32":
            if len(registers) < 2:
                return None
            value = (registers[0] << 16) + registers[1]
        elif register.data_type == "string":
            chars = []
            for item in registers:
                chars.append((item >> 8) & 0xFF)
                chars.append(item & 0xFF)
            value = bytes(chars).decode("utf-8", errors="ignore").strip("\x00 ")
        else:
            value = registers[0] if registers else None

        if value is None:
            return None

        return value * register.scale

    async def async_write_holding_register(self, address: int, value: int) -> None:
        """Write a holding register."""
        if not self.client.connected:
            connected = await self.client.connect()
            if not connected:
                raise UpdateFailed("Could not connect to Webasto Unite")

        result = await self.client.write_register(address=address, value=value, slave=self._unit_id)
        if result.isError():
            raise UpdateFailed(f"Write error at register {address}: {result}")

        await self.async_request_refresh()


CHARGE_POINT_STATE = {
    0: "Available",
    1: "Preparing",
    2: "Charging",
    3: "SuspendedEVSE",
    4: "SuspendedEV",
    5: "Finishing",
    6: "Reserved",
    7: "Unavailable",
    8: "Faulted",
}

SENSOR_UNITS = {
    "current_l1": UnitOfElectricCurrent.AMPERE,
    "current_l2": UnitOfElectricCurrent.AMPERE,
    "current_l3": UnitOfElectricCurrent.AMPERE,
    "voltage_l1": UnitOfElectricPotential.VOLT,
    "voltage_l2": UnitOfElectricPotential.VOLT,
    "voltage_l3": UnitOfElectricPotential.VOLT,
    "active_power_total": UnitOfPower.WATT,
    "session_max_current": UnitOfElectricCurrent.AMPERE,
    "evse_min_current": UnitOfElectricCurrent.AMPERE,
    "evse_max_current": UnitOfElectricCurrent.AMPERE,
    "cable_max_current": UnitOfElectricCurrent.AMPERE,
    "failsafe_current": UnitOfElectricCurrent.AMPERE,
    "charging_current_limit": UnitOfElectricCurrent.AMPERE,
}