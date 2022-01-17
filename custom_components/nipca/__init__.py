import logging

import aiohttp
import requests
import voluptuous as vol
import xmltodict
from aiohttp import ClientError
from aiohttp import ClientTimeout
from async_upnp_client.profiles.profile import UpnpProfileDevice
from homeassistant.components.mjpeg.camera import CONF_MJPEG_URL
from homeassistant.components.mjpeg.camera import CONF_STILL_IMAGE_URL
from homeassistant.const import CONF_AUTHENTICATION
from homeassistant.const import CONF_NAME
from homeassistant.const import CONF_PASSWORD
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.const import CONF_USERNAME
from homeassistant.const import HTTP_BASIC_AUTHENTICATION
from homeassistant.const import HTTP_DIGEST_AUTHENTICATION
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from requests.auth import HTTPBasicAuth
from requests.auth import HTTPDigestAuth

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nipca"
DATA_NIPCA = "nipca.{}"

SCAN_INTERVAL = 10
ASYNC_TIMEOUT = 10

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_AUTHENTICATION, default=HTTP_BASIC_AUTHENTICATION): vol.In([HTTP_BASIC_AUTHENTICATION, HTTP_DIGEST_AUTHENTICATION]),
                vol.Optional(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_USERNAME): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.positive_int,
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


class DLinkUPNPProfile(UpnpProfileDevice):
    DEVICE_TYPES = [
        "urn:schemas-upnp-org:device:Basic:1",
    ]


async def async_setup(hass, config):
    """Register a port mapping for Home Assistant via UPnP."""
    config = config[DOMAIN]

    resps = await DLinkUPNPProfile.async_discover()
    for resp in resps:
        try:
            websession = hass.helpers.aiohttp_client.async_get_clientsession()
            response = await websession.get(url=resp["LOCATION"], timeout=ClientTimeout(total=ASYNC_TIMEOUT))

            camera = xmltodict.parse(await response.text())

            camera_info = camera["root"]["device"]
            url = camera_info.get("presentationURL")

            device = await hass.async_add_executor_job(NipcaCameraDevice.from_url, hass, config, url)

            hass.async_add_job(discovery.async_load_platform(hass, "camera", DOMAIN, device.camera_device_info, config))

            hass.async_add_job(discovery.async_load_platform(hass, "binary_sensor", DOMAIN, device.motion_device_info, config))
        except requests.exceptions.MissingSchema as error:
            _LOGGER.error(error)
    return True


class NipcaCameraDevice:
    """Get the latest sensor data."""

    COMMON_INFO = "{}/common/info.cgi"
    STREAM_INFO = "{}/config/stream_info.cgi"
    MOTION_INFO = [
        "{}/config/motion.cgi",
        "{}/motion.cgi",  # Some D-Links has only this one working
    ]
    STILL_IMAGE = "{}/image/jpeg.cgi"
    NOTIFY_STREAM = "{}/config/notify_stream.cgi"

    _timeout = ASYNC_TIMEOUT

    @classmethod
    def from_device_info(cls, hass, conf, device_info):
        url = device_info.get("presentationURL")
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
        self.motion_info_url = None
        self.client = None
        self.coordinator = None

        self._authentication = self.conf.get(CONF_AUTHENTICATION)
        self._username = self.conf.get(CONF_USERNAME)
        self._password = self.conf.get(CONF_PASSWORD)

        if self._username and self._password:
            if self._authentication == HTTP_DIGEST_AUTHENTICATION:
                self.http_auth = HTTPDigestAuth(self._username, self._password)
                self.aiohttp_auth = aiohttp.DigestAuth(self._username, password=self._password)
            else:
                self.http_auth = HTTPBasicAuth(self._username, self._password)
                self.aiohttp_auth = aiohttp.BasicAuth(self._username, password=self._password)
        else:
            self.http_auth = None
            self.aiohttp_auth = None

        self._events = {}
        self._attributes = {}

    @property
    def name(self):
        return self._attributes["name"]

    @property
    def mjpeg_url(self):
        return self.url + self._attributes["vprofileurl1"]

    @property
    def still_image_url(self):
        return self._build_url(self.STILL_IMAGE)

    @property
    def notify_stream_url(self):
        return self._build_url(self.NOTIFY_STREAM)

    @property
    def motion_detection_enabled(self):
        """Return the camera motion detection status."""
        if self._attributes.get("enable") == "yes":
            return True
        if self._attributes.get("motiondetectionenable") == "1":
            return True
        return False

    @property
    def camera_device_info(self):
        device_info = self.conf.copy()
        device_info.update(
            {
                "platform": DOMAIN,
                "url": self.url,
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
                "platform": DOMAIN,
                "url": self.url,
                CONF_NAME: f"{self.name} Motion Sensor",
            }
        )
        return device_info

    def update_info(self):
        self._attributes.update(self._nipca(self.COMMON_INFO))
        self._attributes.update(self._nipca(self.STREAM_INFO))
        if not self.motion_info_url:
            for url in self.MOTION_INFO:
                attrs = self._nipca(url)
                if attrs:
                    self._attributes.update(attrs)
                    self.motion_info_url = url
                    break
            else:
                self.motion_info_url = "disabled"
        elif self.motion_info_url != "disabled":
            self._attributes.update(self._nipca(self.motion_info_url))

    def _nipca(self, suffix):
        url = self._build_url(suffix)
        result = {}
        try:
            if self.http_auth:
                req = requests.get(url, auth=self.http_auth, timeout=self._timeout)
            else:
                req = requests.get(url, timeout=self._timeout)
        except ConnectionError as err:
            _LOGGER.error("Nipca ConnectionError: %s", err)

        for l in req.iter_lines():
            if l:
                if "=" in l.decode().strip():
                    _LOGGER.debug(l.decode().strip())
                    k, v = l.decode().strip().split("=", 1)
                    result[k.lower()] = v
                else:
                    _LOGGER.debug("Nipca can't read line in " + url)
        return result

    def _build_url(self, suffix):
        return suffix.format(self.url)

    def manual_update_sensors(self, data):
        for key in data.keys():
            self._events[key] = data[key]

        self.coordinator.data = self._events

        for update_callback in self.coordinator._listeners:
            update_callback()

    async def update_motion_sensors(self):
        if self.motion_detection_enabled and not self.client:
            self.client = self._notify_listener()

        if self.client:
            try:
                await self.client.__anext__()

            except TypeError as err:
                _LOGGER.warning("Nipca TypeError: %s", err)

            except TimeoutError:
                _LOGGER.error("Nipca TimeoutError: Timeout getting status info")
                self.client = None

            except ClientError as err:
                _LOGGER.error("Nipca ClientError: %s", err)
                self.client = None

            except RuntimeError as err:
                _LOGGER.warning("Nipca RuntimeError: %s", err)

            except StopAsyncIteration:
                _LOGGER.warning("Nipca StopAsyncIteration: Possibly camera error")
                self.client = None

        return self._events

    async def _notify_listener(self):
        websession = self.hass.helpers.aiohttp_client.async_get_clientsession()
        response = await websession.get(url=self.notify_stream_url, auth=self.aiohttp_auth, timeout=ClientTimeout(total=self._timeout))

        cycles = 30 / self.coordinator.update_interval.total_seconds()
        cleaned_buffer_count = 0
        while cleaned_buffer_count < cycles:
            if len(response.content._buffer) == 0:
                cleaned_buffer_count += 1
            else:
                cleaned_buffer_count = 0

            while len(response.content._buffer) > 0:
                line = await response.content.readline()
                line = line.decode().strip()
                if line:
                    _LOGGER.debug("Nipca status: %s", line)
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if v in ("yes", "no"):
                            self.manual_update_sensors({k: v})
                        else:
                            self._events[k] = v
            yield
