DOMAIN = "eplucon"
MANUFACTURER = "Eplucon"
PLATFORMS = ["sensor", "binary_sensor"]
EPLUCON_PORTAL_URL = "https://portaal.eplucon.nl/"
SUPPORTED_TYPES = ["heat_pump", "zones_controller"]

CONF_ENABLE_BRINE_VALIDITY_STATS = "enable_brine_validity_stats"
CONF_BRINE_PUMP_THRESHOLD = "brine_pump_threshold"
CONF_BRINE_VALID_MINUTES = "brine_valid_minutes"
CONF_BRINE_SAMPLE_INTERVAL_MINUTES = "brine_sample_interval_minutes"

DEFAULT_ENABLE_BRINE_VALIDITY_STATS = False
DEFAULT_BRINE_PUMP_THRESHOLD = 5.0
DEFAULT_BRINE_VALID_MINUTES = 15
DEFAULT_BRINE_SAMPLE_INTERVAL_MINUTES = 5

BRINE_STATS_STORAGE_VERSION = 1
