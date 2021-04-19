Home Assistant: LG SmartThinQ v2 Appliances
=======================================

A [Home Assistant][hass] component for controlling/monitoring LG devices
(currently HVAC & Dishwasher) via their SmartThinQ v2 platform, based on
[WideQ][].  The current version of the component requires Home Assistant 0.96
or later.

## Installation

You can install this component with [HACS][].
Add the "custom repository" `marciogranzotto/hass-smartthinq` as an integration.

[hass]: https://home-assistant.io
[wideq]: https://github.com/marciogranzotto/wideq
[hacs]: https://github.com/hacs/integration

You can also install it manually:

- Clone this repository into your `~/.homeassistant` directory under `custom_components` and name it `thinq_v2`. For example, you might do something like this:

       $ cd ~/.homeassistant
       $ mkdir custom_components
       $ cd custom_components
       $ git clone https://github.com/marciogranzotto/hass-smartthinq.git thinq_v2

## Configuration

After the install:
1. Go to Home Assistant's Configuration > Integrations > Add
2. Choose `LG SmartThinQ v2 Appliances`
3. Choose the Country and Language of your SmartThinq account
4. Open the provided `SmartThinQ login URL` on your browser and login using your account
5. Copy the result URL on the `Redirection URL` field
6. Your devices should now be available in HA!

## Migrating from older version

If you were using this integration on `v1.0.0`, you have to **remove** this entry from `configuration.yaml`:
```
thinq_v2:
    wideq_state: /config/wideq_state.json
```

After that, you will need to go through the Configuration again and readd your devices.

Credits
-------

This is fork is a mix of [Adrian Sampson][adrian]'s work, [Michael Wei][no2chem] wideq with some modifications, and the Config Flow is based on [ollo69 ha-smartthinq-sensors][ha-smartthinq-sensors]. 

[adrian]: http://www.cs.cornell.edu/~asampson/
[no2chem]: https://github.com/no2chem
[ha-smartthinq-sensors]: https://github.com/ollo69/ha-smartthinq-sensors
[mit]: https://opensource.org/licenses/MIT
