Version 0.10.0
==============
Released: 2019-02-03

 * Updated new version check to use Flathub instead of PyPI

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
