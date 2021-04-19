"""
Support to interface with LGE ThinQ Devices.
"""

__version__ = "1.1.0"
PROJECT_URL = "https://github.com/marciogranzotto/hass-smartthinq/"
ISSUE_URL = "{}issues".format(PROJECT_URL)

DOMAIN = "thinq_v2"

CONF_LANGUAGE = "language"
CONF_OAUTH_URL = "outh_url"
CONF_OAUTH_USER_NUM = "outh_user_num"
CONF_WIDEQ_STATE = "wideq_state"

CLIENT = "client"
LGE_DEVICES = "lge_devices"
MANUFACTURER = "LG"

SMARTTHINQ_COMPONENTS = [
    "sensor",
    "climate",
]

STARTUP = """
-------------------------------------------------------------------
{}
Version: {}
This is a custom component
If you have any issues with this you need to open an issue here:
{}
-------------------------------------------------------------------
""".format(
    DOMAIN, __version__, ISSUE_URL
)
