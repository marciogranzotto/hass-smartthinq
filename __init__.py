"""
Support for LG Smartthinq devices.
"""
import asyncio
import json
import logging
import os
from typing import Dict
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import wideq
from homeassistant import config_entries
from homeassistant.const import CONF_REGION, CONF_TOKEN
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import discovery
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType
from wideq import Client
from wideq.core import (Auth, InvalidCredentialError, NotConnectedError,
                        NotLoggedInError, TokenError)

from .const import (CLIENT, CONF_LANGUAGE, CONF_OAUTH_URL, CONF_OAUTH_USER_NUM,
                    CONF_WIDEQ_STATE, DOMAIN, LGE_DEVICES,
                    SMARTTHINQ_COMPONENTS, STARTUP)

_LOGGER = logging.getLogger(__name__)

KEY_SMARTTHINQ_DEVICES = "smartthinq_devices"
README_URL = "https://github.com/marciogranzotto/hass-smartthinq/blob/master/README.md"


class LGDevice(Entity):
    def __init__(self, client, device):
        self._client = client
        self._device = device

    @property
    def name(self):
        return self._device.name

    @property
    def available(self):
        return True


class LGEAuthentication:
    def __init__(self, region, language):
        self._region = region
        self._language = language

    def _create_client(self):
        client = Client(country=self._region, language=self._language)
        return client

    def getLoginUrl(self) -> str:

        login_url = None
        client = self._create_client()

        try:
            login_url = client.gateway.oauth_url()
        except Exception:
            _LOGGER.exception("Error retrieving login URL from ThinQ")

        return login_url

    def getOAuthInfoFromUrl(self, callback_url) -> Dict[str, str]:
        oauth_info = None
        try:
            client = self._create_client()
            auth = Auth.from_url(client.gateway, callback_url)
            out = {
                "oauth_url": auth.oauth_root,
                "user_number": auth.user_number,
                "access_token": auth.access_token,
                "refresh_token": auth.refresh_token,
            }
            _LOGGER.info(out)
            return out
        except Exception:
            _LOGGER.exception("Error retrieving OAuth info from ThinQ")

        return oauth_info

    def getOAuthFromUrl(self, callback_url) -> Auth:
        try:
            client = self._create_client()
            return Auth.from_url(client.gateway, callback_url)
        except Exception:
            _LOGGER.exception("Error retrieving OAuth info from ThinQ")
            return None

    def createClientWithAuth(self, auth):
        client = self._create_client()
        client._auth = auth
        client.refresh()
        client._devices = client.session.get_devices()
        return client

    def createClientFromToken(self, token, oauth_url=None, oauth_user_num=None):
        client = self._create_client()
        client._auth = Auth(client.gateway, None, token, oauth_user_num, oauth_url)
        client.refresh()
        client._devices = client.session.get_devices()
        return client


async def async_setup(hass, config):
    """
    This method gets called if HomeAssistant has a valid configuration entry within
    configurations.yaml.
    Thus, in this method we simply trigger the creation of a config entry.
    :return:
    """
    conf = config.get(DOMAIN)
    hass.data[DOMAIN] = {}

    if conf is not None:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=conf
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistantType, config_entry):
    """
    This class is called by the HomeAssistant framework when a configuration entry is provided.
    """

    refresh_token = config_entry.data.get(CONF_TOKEN)
    region = config_entry.data.get(CONF_REGION)
    language = config_entry.data.get(CONF_LANGUAGE)
    oauth_url = config_entry.data.get(CONF_OAUTH_URL)
    oauth_user_num = config_entry.data.get(CONF_OAUTH_USER_NUM)

    _LOGGER.info(STARTUP)
    _LOGGER.info(
        "Initializing ThinQ platform with region: %s - language: %s",
        region,
        language,
    )

    hass.data.setdefault(DOMAIN, {})[LGE_DEVICES] = {}

    # if network is not connected we can have some error
    # raising ConfigEntryNotReady platform setup will be retried
    lgeauth = LGEAuthentication(region, language)
    try:
        client = await hass.async_add_executor_job(
            lgeauth.createClientFromToken, refresh_token, oauth_url, oauth_user_num
        )

    except InvalidCredentialError:
        _LOGGER.error("Invalid ThinQ credential error. Component setup aborted")
        return False

    except Exception:
        _LOGGER.warning(
            "Connection not available. ThinQ platform not ready", exc_info=True
        )
        raise ConfigEntryNotReady()

    if not client._devices:
        _LOGGER.error("No ThinQ devices found. Component setup aborted")
        return False

    _LOGGER.info("ThinQ client connected")

    try:
        hass.data[CONF_WIDEQ_STATE] = client.dump()
        await lge_devices_setup(hass, client, config_entry)
    except Exception:
        _LOGGER.warning(
            "Connection not available. ThinQ platform not ready", exc_info=True
        )
        raise ConfigEntryNotReady()

    for platform in SMARTTHINQ_COMPONENTS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    await asyncio.gather(
        *[
            hass.config_entries.async_forward_entry_unload(config_entry, platform)
            for platform in SMARTTHINQ_COMPONENTS
        ]
    )

    hass.data.pop(DOMAIN)

    return True


async def lge_devices_setup(hass, client, config_entry):
    """Query connected devices from LG ThinQ."""
    _LOGGER.info("Starting LGE ThinQ devices...")

    device_count = 0

    if KEY_SMARTTHINQ_DEVICES not in hass.data:
        hass.data[KEY_SMARTTHINQ_DEVICES] = []

    while True:
        try:
            for device in client.devices:
                hass.data[KEY_SMARTTHINQ_DEVICES].append(device.id)

            for component in SMARTTHINQ_COMPONENTS:
                discovery.load_platform(hass, component, DOMAIN, {}, config_entry)
                device_count += 1
            _LOGGER.info("Founds %s LGE device(s)", str(device_count))
            return
        except wideq.NotLoggedInError:
            _LOGGER.info("Session expired.")
            client.refresh()
