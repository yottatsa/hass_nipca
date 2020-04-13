"""
Will open a port in your router for Home Assistant and provide statistics.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/upnp/
"""
from ipaddress import ip_address
import logging
import asyncio

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

import voluptuous as vol

from homeassistant.const import (
    CONF_NAME, CONF_USERNAME, CONF_PASSWORD, CONF_AUTHENTICATION,
    HTTP_BASIC_AUTHENTICATION, HTTP_DIGEST_AUTHENTICATION)
from homeassistant.components.mjpeg.camera import (CONF_MJPEG_URL, CONF_STILL_IMAGE_URL)
from homeassistant.const import (EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.util import get_local_ip


DEPENDENCIES = ['upnp', 'api']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'nipca'
DATA_NIPCA = 'nipca.{}'

BASIC_DEVICE = 'urn:schemas-upnp-org:device:Basic:1.0'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_AUTHENTICATION, default=HTTP_BASIC_AUTHENTICATION):
            vol.In([HTTP_BASIC_AUTHENTICATION, HTTP_DIGEST_AUTHENTICATION]),
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_USERNAME): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    """Register a port mapping for Home Assistant via UPnP."""
    config = config[DOMAIN]

    import pyupnp_async
    from pyupnp_async.error import UpnpSoapError

    resps = await pyupnp_async.msearch(search_target=BASIC_DEVICE)
    for resp in resps:
        try:
            device = await resp.get_device()
            device_info = device['root']['device']
            device = NipcaCameraDevice.from_device_info(
                hass, config, device_info
            )
            hass.async_add_job(
                discovery.async_load_platform(
                    hass, 'camera', DOMAIN, device.camera_device_info, config
                )
            )
            hass.async_add_job(
                discovery.async_load_platform(
                    hass, 'sensor', DOMAIN, device.motion_device_info, config
                )
            )
        except UpnpSoapError as error:
            _LOGGER.error(error)
        except requests.exceptions.MissingSchema as error:
            _LOGGER.error(error)
    return True


class NipcaCameraDevice(object):
    """Get the latest sensor data."""
    COMMON_INFO = '{}/common/info.cgi'
    STREAM_INFO = '{}/config/stream_info.cgi'
    MOTION_INFO = '{}/config/motion.cgi'  # D-Link has only this one working
    STILL_IMAGE = '{}/image/jpeg.cgi'
    NOTIFY_STREAM = '{}/config/notify_stream.cgi'

    @classmethod
    def from_device_info(cls, hass, conf, device_info):
        url = device_info.get('presentationURL')
        return cls.from_url(hass, conf, url)

    @classmethod
    def from_url(cls, hass, conf, url):
        data_name = DATA_NIPCA.format(url)
        device = hass.data.get(data_name)
        if not device:
            device = cls(hass, conf, url)
            device.update_info()
            hass.data[data_name] = device
        return device

    def __init__(self, hass, conf, url):
        """Init Nest Devices."""
        self.hass = hass
        self.conf = conf
        self.url = url

        self._authentication = self.conf.get(CONF_AUTHENTICATION)
        self._username = self.conf.get(CONF_USERNAME)
        self._password = self.conf.get(CONF_PASSWORD)
        if self._username and self._password:
            if self._authentication == HTTP_DIGEST_AUTHENTICATION:
                self._auth = HTTPDigestAuth(self._username, self._password)
            else:
                self._auth = HTTPBasicAuth(self._username, self._password)
        else:
            self._auth = None

        self._attributes = {}

    @property
    def name(self):
        return self._attributes['name']

    @property
    def mjpeg_url(self):
        return self.url + self._attributes['vprofileurl1']

    @property
    def still_image_url(self):
        return self._build_url(self.STILL_IMAGE)

    @property
    def notify_stream_url(self):
        return self._build_url(self.NOTIFY_STREAM)

    @property
    def motion_detection_enabled(self):
        """Return the camera motion detection status."""
        return self._attributes.get('enable') == 'yes'
        #return self._attributes.get('motiondetectionenable') == '1'

    @property
    def camera_device_info(self):
        device_info = self.conf.copy()
        device_info.update(
            {
                'platform': DOMAIN,
                'url': self.url,
                CONF_NAME: self.name,
                CONF_MJPEG_URL: self.mjpeg_url,
                CONF_STILL_IMAGE_URL: self.still_image_url,
            }
        )
        return device_info

    @property
    def motion_device_info(self):
        device_info = self.conf.copy()
        device_info.update(
            {
                'platform': DOMAIN,
                'url': self.url,
                CONF_NAME: '{} motion sensor'.format(self.name),
            }
        )
        return device_info

    def update_info(self):
        self._attributes.update(self._nipca(self.COMMON_INFO))
        self._attributes.update(self._nipca(self.STREAM_INFO))
        self._attributes.update(self._nipca(self.MOTION_INFO))

    def _nipca(self, suffix):
        url = self._build_url(suffix)
        try:
            if self._auth:
                _LOGGER.debug("con auth" + url)
                req = requests.get(url, auth=self._auth, timeout=10)
            else:
                _LOGGER.debug("sin auth" + url)
                req = requests.get(url, timeout=10)
            result = {}
        except ConnectionError as error:
            _LOGGER.error("ERROR camera conexion: " + error)
        #except ConnectionError as error:
        #    _LOGGER.error("ERROR camera conexion: " + error)
        for l in req.iter_lines():
            if l:
                if '=' in l.decode().strip():
                    _LOGGER.debug(l.decode().strip())
                    k, v = l.decode().strip().split('=', 1)
                    result[k.lower()] = v
                else:
                    _LOGGER.error("Nipca Can not read line in " + url)
        return result

    def _build_url(self, suffix):
        return suffix.format(self.url)
