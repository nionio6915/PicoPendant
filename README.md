# PicoPendant
A small CNC Pendant based off the Raspberry Pi Pico W and the Waveshare Pico-ResTouch-LCD-3.5

## Folders
* CircuitBoard<br>This contains the circuit board (display hat) files and readme. The circuit board has two LiPo connectors (small and regular), a LiPo charger, three encoder inputs, three A/D dividers for ladder switches and one switch input.
* Enclosure<br>This contains a Fusion360 workspace for 3d printing an enclosure and spacers. The spacers are used to support the display hat over the Waveshare LCD. Since the hole locations are not exact and Jlcpcb seems unable to put holes in the right place anyway, the spacers are slightly offset.
* PythonSrc<br>The MicroPython source code

## GUI
The current hacky gui is a single screen named 'Jog'. To run the jog screen requires the following MicroPython

	from screens.jog import RunJogger
	RunJogger()

The current GUI supports two rotary encoders and one ladder switch.

The leftmost encoder does the jogging. Click the switch to move between metric and inches and also to show/hide machine coordinates, so four positions.

The middle encoder is multi-use but primarily sets the jog amount per click. When the button is clicked the jog amount becomes enabled/disabled and an asterisk appears - this is a safety measure.

The right switch sets the axis being jogged. 

To switch devices, tap the touchscreen and the middle encoder mode changes to device select. Tap again to have the middle encoder change screen brightness. Tap one more time to return to jog amount selection.

To exit cleanly from RunJogger press both rotary encoder buttons at the same time.

<span style="color:orange">There are 2 'safety' things to ensure the jogger isn't fussing your machine during jobs.</span>
* it only sends wifi requests when the encoder mode is 'adjust tic size' (enabled or disabled)
* you can use a Null device (0.0.0.0) to disable wifi requests


## Serialization
There is code to serialize/load the current settings. The load happens at start (main.py) but currently there is no automatic configuration save so that is a manual python call.

	from util import picoPendant
	picoPendant.GlobalPico().Save()

The configuration loader reads config.json and updates any fields found in config.json that exist in GlobalPico()).

## SBC Support
The SBC version of the Duet3d controller takes quite a different WiFi syntax and is not yet supported.
