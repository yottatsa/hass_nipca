# hass_nipca

Discover and set up [NIPCA]-compatible cameras.

1. Copy [custom_components/nipca] to your `~/.homeassistant/custom_components`
2. Add `nipca:` section to the `configuration.yaml`

```
nipca:
  username: <optional username>
  password: <optional password>
```

## Supported devices

* D-Link DCS-930LB1 `version=2.15 build=6`, `version=2.17 build=3` *tested*
* TRENDnet TV-IP672W, TV-IP672WI The Megapixel Wireless N (Day/Night) PTZ Internet Camera *[claimed1]*
* D-Link DCS-6513 *[claimed2]* and lot mote *[claimed3]*
* D-Link DCS-P6000LH *[implemented1]* (alternative location for motion config)

## Supported features

* UPNP discovery
* Auth
* Stream and attributes (name, motion detection status) discovery
* Motion and sound detection

## TBD
* Integration flow
* [`dlinkdcs` library](https://github.com/scross01/dlink-dcs-python-lib)

[NIPCA]: http://gurau-audibert.hd.free.fr/josdblog/wp-content/uploads/2013/09/CGI_2121.pdf
[custom_components/nipca]: https://github.com/yottatsa/hass_nipca/tree/master/custom_components/nipca
[claimed1]: http://content.etilize.com/user-manual/1021943810.pdf
[claimed2]: https://cpcam.jp/security/product/ip/nuuo_camera-list/nsv2u_list.pdf
[claimed3]: http://manual-guide.com/manu/26086/index.html
[implemented1]: https://github.com/dave-code-ruiz/nipca/blob/b63da25c9dbe48a0f6ea2dd450822e28cec7d666/README.md
