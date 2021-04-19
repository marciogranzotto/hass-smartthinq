"""Config flow for Thinq v2."""
import logging
import re

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_REGION, CONF_TOKEN
from homeassistant.core import callback
from pycountry import countries as py_countries
from pycountry import languages as py_languages

from . import LGEAuthentication
from .const import CONF_LANGUAGE, CONF_OAUTH_URL, CONF_OAUTH_USER_NUM, DOMAIN

CONF_LOGIN = "login_url"
CONF_URL = "callback_url"

RESULT_SUCCESS = 0
RESULT_FAIL = 1
RESULT_NO_DEV = 2

_LOGGER = logging.getLogger(__name__)


def _countries_list():
    """Returns a list of countries, suitable for use in a multiple choice field."""
    countries = {}
    for country in sorted(py_countries, key=lambda x: x.name):
        countries[country.alpha_2] = f"{country.name} - {country.alpha_2}"
    return countries


def _languages_list():
    """Returns a list of languages, suitable for use in a multiple choice field."""
    languages = {}
    for language in sorted(py_languages, key=lambda x: x.name):
        if hasattr(language, "alpha_2"):
            languages[language.alpha_2] = f"{language.name} - {language.alpha_2}"
    return languages


INIT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REGION): vol.In(_countries_list()),
        vol.Required(CONF_LANGUAGE): vol.In(_languages_list()),
    }
)


class SmartThinQFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle SmartThinQ v2 config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize flow."""
        self._region = None
        self._language = None
        self._token = None
        self._oauth_url = None
        self._oauth_user_num = None
        self._auth = None

        self._loginurl = None

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user interface"""

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if not user_input:
            return self._show_form()

        region = user_input[CONF_REGION]
        language = user_input[CONF_LANGUAGE]

        region_regex = re.compile(r"^[A-Z]{2,3}$")
        if not region_regex.match(region):
            return self._show_form(errors={"base": "invalid_region"})

        if len(language) == 2:
            language_regex = re.compile(r"^[a-z]{2,3}$")
        else:
            language_regex = re.compile(r"^[a-z]{2,3}-[A-Z]{2,3}$")
        if not language_regex.match(language):
            return self._show_form(errors={"base": "invalid_language"})

        self._region = region
        self._language = language
        if len(language) == 2:
            self._language += "-" + region

        lgauth = LGEAuthentication(self._region, self._language)
        self._loginurl = await self.hass.async_add_executor_job(lgauth.getLoginUrl)
        if not self._loginurl:
            return self._show_form(errors={"base": "error_url"})
        return self._show_form(errors=None, step_id="url")

    async def async_step_url(self, user_input=None):
        """Parse the response url for oauth data and submit for save."""

        lgauth = LGEAuthentication(self._region, self._language)
        url = user_input[CONF_URL]
        self._auth = await self.hass.async_add_executor_job(lgauth.getOAuthFromUrl, url)
        if not self._auth:
            return self._show_form(errors={"base": "invalid_url"}, step_id="url")

        self._token = self._auth.refresh_token
        self._oauth_url = self._auth.oauth_root
        self._oauth_user_num = self._auth.user_number

        result = await self._check_connection()
        if result != RESULT_SUCCESS:
            return self._manage_error(result)
        return self._save_config_entry()

    async def async_step_token(self, user_input=None):
        """Show result token and submit for save."""
        self._token = user_input[CONF_TOKEN]
        result = await self._check_connection()
        if result != RESULT_SUCCESS:
            return self._manage_error(result)
        return self._save_config_entry()

    async def _check_connection(self):
        """Test the connection to ThinQ."""

        lgauth = LGEAuthentication(self._region, self._language)
        try:
            client = await self.hass.async_add_executor_job(
                lgauth.createClientWithAuth, self._auth
            )
        except Exception as ex:
            _LOGGER.error("Error connecting to ThinQ: %s", ex)
            return RESULT_FAIL

        devices = await self.hass.async_add_executor_job(client.session.get_devices)
        if not devices:
            return RESULT_NO_DEV

        return RESULT_SUCCESS

    @callback
    def _manage_error(self, error_code):
        """Manage the error result."""
        if error_code == RESULT_FAIL:
            _LOGGER.error("LGE ThinQ: Invalid Login info!")
            return self._show_form({"base": "invalid_credentials"})

        if error_code == RESULT_NO_DEV:
            _LOGGER.error("No SmartThinQ devices found. Component setup aborted.")
            return self.async_abort(reason="no_smartthinq_devices")

    @callback
    def _save_config_entry(self):
        """Save the entry."""

        data = {
            CONF_TOKEN: self._token,
            CONF_REGION: self._region,
            CONF_LANGUAGE: self._language,
        }
        data.update(
            {
                CONF_OAUTH_URL: self._oauth_url,
                CONF_OAUTH_USER_NUM: self._oauth_user_num,
            }
        )

        return self.async_create_entry(
            title="LGE Devices",
            data=data,
        )

    @callback
    def _show_form(self, errors=None, step_id="user"):
        """Show the form to the user."""
        schema = None
        if step_id == "user":
            schema = INIT_SCHEMA
        elif step_id == "url":
            schema = vol.Schema(
                {
                    vol.Required(CONF_LOGIN, default=self._loginurl): str,
                    vol.Required(CONF_URL): str,
                }
            )
        elif step_id == "token":
            schema = vol.Schema({vol.Required(CONF_TOKEN, default=self._token): str})

        return self.async_show_form(
            step_id=step_id,
            data_schema=schema,
            errors=errors if errors else {},
        )

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        if self._async_current_entries():
            _LOGGER.debug("SmartThinQ configuration already present / imported.")
            return self.async_abort(reason="single_instance_allowed")

        _LOGGER.warning(
            "Integration configuration using configuration.yaml is not supported."
            " Please configure integration from HA user interface"
        )
        return self.async_abort(reason="single_instance_allowed")
