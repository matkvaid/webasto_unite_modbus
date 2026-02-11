"""Constants for the Webasto Unite Modbus integration."""

DOMAIN = "webasto_unite_modbus"

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_UNIT_ID = "unit_id"
CONF_SCAN_INTERVAL = "scan_interval"

# Default values
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 255
DEFAULT_SCAN_INTERVAL = 10

# Platforms exposed by the integration
PLATFORMS = ["sensor", "number", "switch"]
