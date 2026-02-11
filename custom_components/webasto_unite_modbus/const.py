"""Constants for the Webasto Unite Modbus integration."""

DOMAIN = "webasto_unite_modbus"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_UNIT_ID = "unit_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 255
DEFAULT_SCAN_INTERVAL = 10

PLATFORMS = ["sensor", "number", "switch"]