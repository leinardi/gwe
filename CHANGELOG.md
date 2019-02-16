Version 0.12.0
==============
Released: 2019-02-16

 * Using NV-CONTROL instead of NVML, when possible, to provide better
   compatibility with older cards
 * Fix #11: Power limit Apply should check exit code
 * Fix #9: The Close button in the About dialog box does not work on KDE

Version 0.11.0
==============
Released: 2019-02-10

 * Added overclock profiles
 * Fixed GPU offset overclock not working for some cards
 * Showing notification via libnotify if an update is available
 * Added PCIe current generation info

Version 0.10.4
==============
Released: 2019-02-09

 * Workaround for #36: graph text color from GTK theme

Version 0.10.3
==============
Released: 2019-02-09

 * Applied fix for #26 also to set overclock and fan speed

Version 0.10.2
==============
Released: 2019-02-09

 * Fixed #26: Added command line option to specify NV-CONTROL display
 * Fixed #28: NVMLError_InvalidArgument with more than 1 GPU
 * Fixed check for Coolbit 4 not working
 * Launcher name changed to GreenWithEnvy
 * Removed workaround for memory leak caused by python-xlib
   (https://github.com/python-xlib/python-xlib/issues/136)

Version 0.10.1
==============
Released: 2019-02-03

 * Updated new version check to use Flathub instead of PyPI
 * Workaround for memory leak caused by python-xlib
   (https://github.com/python-xlib/python-xlib/issues/136)

Version 0.9.0
=============
Released: 2019-02-02

 * Fixed #16: [X-Protocol] Unable to set values
 * Fixed #15: [X-Protocol] struct.error: unpack requires a buffer of xxx bytes
   while reading
 * Fixed crash when Encoder/Decoder usage is not available

Version 0.8.0
=============
Released: 2019-01-30

 * App available on Flathub! https://flathub.org/apps/details/com.leinardi.gwe
 * Fixed crash when power data is not available

Version 0.7.0
=============
Released: 2019-01-13

 * **Huge** improvement in resource utilization thanks to the switch from CLI
   tools to libs to read the data
 * Historical data dialog! (Requires GNOME 3.30+. New dependency necessary,
   check the Distribution dependencies section of the readme)
 * Highlighting currently applied profile
 * Distributing the app via Flatpak (not published on Flathub yet)
 * Dropped support for PyPI

Version 0.5.1
=============
Released: 2019-01-03

 * Min duty changed from 25 to 0
 * Slightly bigger app indicator icon

Version 0.5.0
=============
Released: 2019-01-03

 * Implemented Fan curve profile!
 * Added GPU temperature to app indicator
 * Changed app indicator icon (again)
 * Other minor UI improvements

Version 0.3.2
=============
Released: 2019-01-01

 * Fixed overclock slider value not correctly restored on startup

Version 0.3.1
=============
Released: 2019-01-01

 * Removed unnecessary dependency from py3nvml

Version 0.3.0
=============
Released: 2019-01-01

 * Enabled version check on startup
 * Added ability to overclock GPU and Memory (requires coolbits to be set!)
 * Added ability to change Power Limit
 * Changed app indicator icon
 * Other minor UI improvements

Version 0.1.0
=============
Released: 2018-12-31

 * Initial release
