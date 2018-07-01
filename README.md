# hass_nipca

Discover and set up [NIPCA]-compatible cameras.

1. Copy contents to `custom_components` to your `~/.homeassistant/`
2. Add `nipca:` section to the `configuration.yaml`

  nipca:
    username: <optional username>
    password: <optional password>


## Supported devices

* D-Link DCS-930LB1 `version=2.15` `build=6`

## Supported features

* UPNP discovery
* Auth
* Stream and attributes (name, motion detection status) discovery
* Motion and sound detection

[NIPCA]: http://gurau-audibert.hd.free.fr/josdblog/wp-content/uploads/2013/09/CGI_2121.pdf
