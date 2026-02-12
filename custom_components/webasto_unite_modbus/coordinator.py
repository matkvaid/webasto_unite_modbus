"""Data coordinator for Webasto Unite Modbus."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import inspect
import logging
from typing import Any

from pymodbus.client import AsyncModbusTcpClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfEnergy,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, CONF_UNIT_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Keep-alive interval in seconds
KEEP_ALIVE_INTERVAL = 5
# Keep-alive register address
KEEP_ALIVE_REGISTER = 6000


@dataclass(frozen=True)
class RegisterDef:
    """Register descriptor."""

    key: str
    address: int
    input_type: str = "input"
    data_type: str = "uint16"
    count: int = 1
    scale: float = 1.0


# Complete register map based on Webasto Unite Modbus specification
REGISTER_MAP: tuple[RegisterDef, ...] = (
    # Identification strings
    RegisterDef("serial_number", 100, data_type="string", count=25),
    RegisterDef("charge_point_id", 130, data_type="string", count=50),
    RegisterDef("brand", 190, data_type="string", count=10),
    RegisterDef("model", 210, data_type="string", count=5),
    RegisterDef("firmware_version", 230, data_type="string", count=50),
    # Date and time (YYMMDD and HHMMSS)
    RegisterDef("date", 290, data_type="uint32"),
    RegisterDef("time", 294, data_type="uint32"),
    # Rated power and phases
    RegisterDef("charge_point_power", 400, data_type="uint32"),
    RegisterDef("number_of_phases", 404),
    # Charger states
    RegisterDef("charge_point_state", 1000),
    RegisterDef("charging_state", 1001),
    RegisterDef("equipment_state", 1002),
    RegisterDef("cable_state", 1004),
    RegisterDef("fault_code", 1006, data_type="uint16"),
    # Electrical measurements
    RegisterDef("current_l1", 1008, scale=0.001),
    RegisterDef("current_l2", 1010, scale=0.001),
    RegisterDef("current_l3", 1012, scale=0.001),
    RegisterDef("voltage_l1", 1014),
    RegisterDef("voltage_l2", 1016),
    RegisterDef("voltage_l3", 1018),
    RegisterDef("active_power_total", 1020, data_type="uint32"),
    RegisterDef("active_power_l1", 1024, data_type="uint32"),
    RegisterDef("active_power_l2", 1028, data_type="uint32"),
    RegisterDef("active_power_l3", 1032, data_type="uint32"),
    RegisterDef("meter_reading", 1036, data_type="uint32", scale=0.1),
    # Current limits and capabilities
    RegisterDef("session_max_current", 1100),
    RegisterDef("evse_min_current", 1102),
    RegisterDef("evse_max_current", 1104),
    RegisterDef("cable_max_current", 1106),
    # Session statistics
    RegisterDef("charged_energy", 1502, data_type="uint32", scale=0.001),
    RegisterDef("session_start_time", 1504, data_type="uint32"),
    RegisterDef("session_duration", 1508, data_type="uint32"),
    RegisterDef("session_end_time", 1512, data_type="uint32"),
    # Failsafe and dynamic control registers
    RegisterDef("failsafe_current", 2000, input_type="holding"),
    RegisterDef("failsafe_timeout", 2002, input_type="holding"),
    RegisterDef("charging_current_limit", 5004, input_type="holding"),
    RegisterDef("alive_register", 6000, input_type="holding"),
)

# State mapping for the charge point state
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

# Unit mapping used when no native_unit_of_measurement is defined in the entity description
SENSOR_UNITS = {
    "current_l1": UnitOfElectricCurrent.AMPERE,
    "current_l2": UnitOfElectricCurrent.AMPERE,
    "current_l3": UnitOfElectricCurrent.AMPERE,
    "voltage_l1": UnitOfElectricPotential.VOLT,
    "voltage_l2": UnitOfElectricPotential.VOLT,
    "voltage_l3": UnitOfElectricPotential.VOLT,
    "active_power_total": UnitOfPower.WATT,
    "active_power_l1": UnitOfPower.WATT,
    "active_power_l2": UnitOfPower.WATT,
    "active_power_l3": UnitOfPower.WATT,
    "charge_point_power": UnitOfPower.WATT,
    "session_max_current": UnitOfElectricCurrent.AMPERE,
    "evse_min_current": UnitOfElectricCurrent.AMPERE,
    "evse_max_current": UnitOfElectricCurrent.AMPERE,
    "cable_max_current": UnitOfElectricCurrent.AMPERE,
    "failsafe_current": UnitOfElectricCurrent.AMPERE,
    "charging_current_limit": UnitOfElectricCurrent.AMPERE,
    # Energy and other units
    "meter_reading": UnitOfEnergy.KILO_WATT_HOUR,
    "charged_energy": UnitOfEnergy.KILO_WATT_HOUR,
    "session_duration": UnitOfTime.SECONDS,
}


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
        self._keep_alive_task: asyncio.Task | None = None
        
        # Determine Modbus keyword at initialization for thread safety
        self._modbus_unit_keyword = self._detect_modbus_unit_keyword()

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=entry.data[CONF_SCAN_INTERVAL]),
        )

    def _detect_modbus_unit_keyword(self) -> str | None:
        """Detect which keyword argument the Modbus client uses for unit ID.
        
        Returns the keyword to use, or None if positional argument should be used.
        """
        read_method = self.client.read_holding_registers
        sig = inspect.signature(read_method)
        params = sig.parameters.keys()
        
        if "device_id" in params:
            return "device_id"
        elif "unit" in params:
            return "unit"
        elif "slave" in params:
            return "slave"
        else:
            return None  # Use positional

    async def async_start_keep_alive(self) -> None:
        """Start the keep-alive background task."""
        if self._keep_alive_task is None or self._keep_alive_task.done():
            self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
            _LOGGER.debug("Keep-alive task started")

    async def _keep_alive_loop(self) -> None:
        """Background task to write keep-alive register every 5 seconds."""
        while True:
            try:
                await asyncio.sleep(KEEP_ALIVE_INTERVAL)
                if self.client.connected:
                    kwargs, positional_unit = self._get_modbus_call_kwargs(
                        address=KEEP_ALIVE_REGISTER,
                        value=1,
                    )
                    if positional_unit is not None:
                        result = await self.client.write_register(positional_unit, **kwargs)
                    else:
                        result = await self.client.write_register(**kwargs)
                    if result.isError():
                        _LOGGER.warning(
                            "Keep-alive write error at register %s: %s",
                            KEEP_ALIVE_REGISTER,
                            result,
                        )
                    else:
                        _LOGGER.debug("Keep-alive written to register %s", KEEP_ALIVE_REGISTER)
            except asyncio.CancelledError:
                _LOGGER.debug("Keep-alive task cancelled")
                break
            except Exception as err:
                _LOGGER.error("Keep-alive task error: %s", err)

    async def async_shutdown(self) -> None:
        """Close Modbus client and stop keep-alive task."""
        if self._keep_alive_task and not self._keep_alive_task.done():
            self._keep_alive_task.cancel()
            try:
                await self._keep_alive_task
            except asyncio.CancelledError:
                pass
        self.client.close()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest data from charger."""
        if not self.client.connected:
            connected = await self.client.connect()
            if not connected:
                raise UpdateFailed("Could not connect to Webasto Unite")
            # Start keep-alive task on successful connection
            await self.async_start_keep_alive()

        data: dict[str, Any] = {
            "last_update": dt_util.utcnow().isoformat(),
        }

        for register in REGISTER_MAP:
            raw_value = await self._read_register(register)
            data[register.key] = self._decode_value(raw_value, register)

        return data

    def _get_modbus_call_kwargs(self, **kwargs) -> tuple[dict[str, Any], int | None]:
        """Prepare kwargs for Modbus calls with robust keyword handling.
        
        Tries device_id (newer pymodbus 3.x), then unit, then slave for unit ID parameter.
        Returns a tuple of (dict with appropriate keyword, optional positional unit_id).
        """
        # Store unit_id separately
        unit_id = kwargs.pop("unit_id", self._unit_id)
        
        result_kwargs = kwargs.copy()
        if self._modbus_unit_keyword:
            result_kwargs[self._modbus_unit_keyword] = unit_id
            return result_kwargs, None
        else:
            return result_kwargs, unit_id

    async def _read_register(self, register: RegisterDef) -> list[int]:
        """Read a register from the device."""
        count = register.count
        # Use two registers for 32-bit values
        if register.data_type == "uint32":
            count = 2

        # Prepare kwargs with robust Modbus keyword handling
        kwargs, positional_unit = self._get_modbus_call_kwargs(
            address=register.address, count=count
        )
        
        if register.input_type == "holding":
            if positional_unit is not None:
                result = await self.client.read_holding_registers(positional_unit, **kwargs)
            else:
                result = await self.client.read_holding_registers(**kwargs)
        else:
            if positional_unit is not None:
                result = await self.client.read_input_registers(positional_unit, **kwargs)
            else:
                result = await self.client.read_input_registers(**kwargs)

        if result.isError():
            raise UpdateFailed(f"Read error at register {register.address}: {result}")

        return result.registers

    def _decode_value(self, registers: list[int], register: RegisterDef) -> Any:
        """Decode raw register data into a scaled value."""
        if register.data_type == "uint32":
            if len(registers) < 2:
                return None
            value = (registers[0] << 16) + registers[1]
        elif register.data_type == "string":
            chars: list[int] = []
            for item in registers:
                chars.append((item >> 8) & 0xFF)
                chars.append(item & 0xFF)
            value = bytes(chars).decode("utf-8", errors="ignore").strip("\x00 ")
            # Return string directly without scaling
            return value
        else:
            value = registers[0] if registers else None

        if value is None:
            return None

        # Apply scaling only to numeric values
        return value * register.scale

    async def async_write_holding_register(self, address: int, value: int) -> None:
        """Write a holding register."""
        if not self.client.connected:
            connected = await self.client.connect()
            if not connected:
                raise UpdateFailed("Could not connect to Webasto Unite")

        kwargs, positional_unit = self._get_modbus_call_kwargs(
            address=address, value=value
        )
        if positional_unit is not None:
            result = await self.client.write_register(positional_unit, **kwargs)
        else:
            result = await self.client.write_register(**kwargs)
        if result.isError():
            raise UpdateFailed(f"Write error at register {address}: {result}")

        await self.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Webasto Unite charger."""
        # Get device identifiers from coordinator data
        serial_number = self.data.get("serial_number")
        if not serial_number:
            # Use entry_id as fallback to ensure unique identifier
            serial_number = self.entry.entry_id
        
        model = self.data.get("model", "Unite")
        brand = self.data.get("brand", "Webasto")
        firmware_version = self.data.get("firmware_version")
        
        # Build device info with conditional sw_version
        device_info_dict = {
            "identifiers": {(DOMAIN, serial_number)},
            "name": f"{brand} {model}",
            "manufacturer": brand,
            "model": model,
        }
        
        if firmware_version:
            device_info_dict["sw_version"] = firmware_version
        
        return DeviceInfo(**device_info_dict)
