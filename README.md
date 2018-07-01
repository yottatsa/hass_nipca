# hass_nipca

Discover and set up [NIPCA]-compatible cameras.

1. Copy contents to `custom_components` to your `~/.homeassistant/`
2. Add `nipca:` section to the `configuration.yaml`

  nipca:
    username: <optional username>
    password: <optional password>


## Supported devices

* D-Link DCS-930LB1 `version=2.15` `build=6` *tested*
* TRENDnet TV-IP672W, TV-IP672WI The Megapixel Wireless N (Day/Night) PTZ Internet Camera *[claimed1]*
* D-Link DCS-6513 *[claimed2]* and lot mote *[claimed3]*

## Supported features

* UPNP discovery
* Auth
* Stream and attributes (name, motion detection status) discovery
* Motion and sound detection

[NIPCA]: http://gurau-audibert.hd.free.fr/josdblog/wp-content/uploads/2013/09/CGI_2121.pdf
[claimed1]: http://content.etilize.com/user-manual/1021943810.pdf
[claimed2]: https://cpcam.jp/security/product/ip/nuuo_camera-list/nsv2u_list.pdf
[claimed3]: http://manual-guide.com/manu/26086/index.html
