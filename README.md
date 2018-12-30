# gwe
TBD


## Distribution dependencies
### (K/X)Ubuntu 18.04 or newer
```bash
sudo apt install gir1.2-gtksource-3.0 gir1.2-appindicator3-0.1 python3-gi-cairo python3-pip
```
### Fedora 28+
Install [(K)StatusNotifierItem/AppIndicator Support](https://extensions.gnome.org/extension/615/appindicator-support/)

### Arch Linux (Gnome)
```bash
sudo pacman -Syu python-pip libappindicator-gtk3
```

## Install using PIP
```bash
pip3 install gwe
```
Add the the executable path `~/.local/bin` to your PATH variable if missing.

## Update using PIP
```bash
pip3 install -U gwe
```

## Running the app
To start the app you have to run the command `gwe` in a terminal. 

### Application entry
To add a desktop entry for the application run the following command:
```bash
gwe --application-entry 
```
If you don't want to create this custom rule you can run gwe as root 
(using sudo) but we advise against this solution.

## Command line options

  | Parameter                 | Description|
  |---------------------------|------------|
  |-v, --version              |Show the app version|
  |--debug                    |Show debug messages|
  |--hide-window              |Start with the main window hidden|
  |--application-entry        |Add a desktop entry for the application|
  |--autostart-on             |Enable automatic start of the app on login|
  |--autostart-off            |Disable automatic start of the app on login|


## Python dependencies
## How to run the repository sources

```
sudo apt install python3-pip
git clone https://gitlab.com/leinardi/gwe.git
pip3 install injector
pip3 install matplotlib
pip3 install peewee
pip3 install pygobject
pip3 install pyxdg
pip3 install requests
pip3 install rx
ca gwe
./run
```

## How can I support this project?

The best way to support this plugin is to star it on both [GitLab](https://gitlab.com/leinardi/gwe) and [GitHub](https://github.com/leinardi/gwe).
Feedback is always welcome: if you found a bug or would like to suggest a feature,
feel free to open an issue on the [issue tracker](https://gitlab.com/leinardi/gwe/issues).

## Lincense
```
This file is part of gwe.

Copyright (c) 2018 Roberto Leinardi

gwe is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

gwe is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with gwe.  If not, see <http://www.gnu.org/licenses/>.
```