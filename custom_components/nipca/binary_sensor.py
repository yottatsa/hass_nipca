import asyncio
import logging
import voluptuous as vol

from datetime import timedelta

import homeassistant.helpers.config_validation as cv
from homeassistant.const import STATE_ON
from homeassistant.components.sensor import PLATFORM_SCHEMA

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.entity import async_generate_entity_id

from homeassistant.components.binary_sensor import ENTITY_ID_FORMAT

try:
    from homeassistant.components.binary_sensor import BinarySensorEntity
except:
    from homeassistant.components.binary_sensor import BinarySensorDevice as BinarySensorEntity

from homeassistant.const import (
    CONF_HOST, CONF_NAME, CONF_UNIT_OF_MEASUREMENT, STATE_UNKNOWN,
    CONF_USERNAME, CONF_PASSWORD, CONF_AUTHENTICATION, CONF_SCAN_INTERVAL,
    HTTP_BASIC_AUTHENTICATION, HTTP_DIGEST_AUTHENTICATION, CONF_URL)
from ..nipca import NipcaCameraDevice

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = 10

DEFAULT_NAME = 'NIPCA Camera'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_AUTHENTICATION, default=HTTP_BASIC_AUTHENTICATION):
        vol.In([HTTP_BASIC_AUTHENTICATION, HTTP_DIGEST_AUTHENTICATION]),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_USERNAME): cv.string,
    vol.Required(CONF_URL): cv.url,
    vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.positive_int,
}, extra=vol.ALLOW_EXTRA)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up a NIPCA Camera Sensors."""
    if discovery_info:
        config = PLATFORM_SCHEMA(discovery_info)
    url = config.get(CONF_URL)
    device = await hass.async_add_executor_job(
        NipcaCameraDevice.from_url,hass, config, url)
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="motion_sensor",
        update_method=device.update_motion_sensors,
        update_interval=timedelta(seconds=config.get(CONF_SCAN_INTERVAL)),
    )

    device.coordinator = coordinator

    await coordinator.async_refresh()

    sensors = ["md1"]

    if "mic" in device._attributes and device._attributes["mic"]=="yes":
        sensors.append("audio_detected")
        
    if "pir" in device._attributes and device._attributes["pir"]=="yes":
        sensors.append("pir")
        
    if "led" in device._attributes and device._attributes["led"]=="yes":
        sensors.append("led")
        
    if "ir" in device._attributes and device._attributes["ir"]=="yes":
        sensors.append("irled")
        
    if "inputs" in device._attributes:
        num_inputs = int(device._attributes["inputs"])
        if num_inputs > 0:
            for input in range(1,num_inputs+1):
                sensors.append(f"input{input}")
        
    if "outputs" in device._attributes:
        num_outputs = int(device._attributes["outputs"])
        if num_outputs > 0:
            for output in range(1,num_outputs+1):
                sensors.append(f"output{output}")

    async_add_entities(
        NipcaMotionSensor(
            hass, device, coordinator, name
            ) for name in sensors
        )


class NipcaMotionSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Camera Motion Sensor."""

    DEVICE_CLASS = 'motion'

    def __init__(self, hass, device, coordinator, name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._hass = hass
        self._device = device
        self._name = name
        self._coordinator = coordinator
        
        self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, 
            '_'.join(
                [self._device._attributes['macaddr'].replace('.','_'), 
                self._name, 
                'sensor']
                ), 
            hass=hass
            )

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return '_'.join(
            [self._device._attributes['macaddr'].replace('.','_'), 
            self._name, 
            'sensor']
            )

    @property
    def name(self):
        """Return the name of the sensor."""
        return ' '.join([self._device._attributes['name'], self._name, 'sensor'])

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        if self._name in self._coordinator.data:
            return self._coordinator.data[self._name] == STATE_ON
        else:
            return STATE_UNKNOWN

    @property
    def state(self):
        """Return the state of the binary sensor."""
        if ( self._device.motion_detection_enabled and
            self._name in self._coordinator.data ):
            return self._coordinator.data[self._name]
        else:
            return STATE_UNKNOWN

    @property
    def device_state_attributes(self):
        """Return the attributes of the binary sensor."""
        attr = self._device._events.copy()
        return {k:v for k,v in attr.items() if k.startswith(self._name[:2])}

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self.DEVICE_CLASS
        
