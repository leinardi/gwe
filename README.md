# GreenWithEnvy (GWE)
GWE is a GTK system utility designed to provide information, control the fans and overclock your NVIDIA video card
and graphics processor.

# 🔴 🔴 Looking for new maintainer(s)! 🔴 🔴
Most probably my next GPU will be an AMD and, if that happens, I won't be able to provide adequate support for this project anymore. For this reason I'm looking for new maintainer(s).
If you are interested and have adequate knowledge of Python, please get in touch replying to this issue:
https://gitlab.com/leinardi/gwe/-/issues/195

## 💡 Features
<img src="/data/icons/hicolor/48x48@2x/apps/com.leinardi.gwe.png" width="96" align="right" hspace="0" />

* Show general GPU stats (model name, driver version, gpu/memory/power usage, clocks, temps, etc)
* GPU and Memory overclock offset profiles
* Custom Fan curve profiles
* Change power limit
* Historical data graphs

<img src="/art/screenshot-1.png" width="800" align="middle"/>

## 📦 How to get GWE
If you don't like to reading manuals and/or you don't know what the Nvidia CoolBits are,
you can watch the following How To made by [Intelligent Gaming](https://www.youtube.com/channel/UCH4d4o0Otxa7BNYs5Z5UEjg):

[![How To Overclock And Control Fans On An nVidia Graphic Card In Linux - Green With Envy / GWE](https://img.youtube.com/vi/HAKe9ladLvc/0.jpg)](https://www.youtube.com/watch?v=HAKe9ladLvc)

### Install from Flathub
This is the preferred way to get GWE on any major distribution (Arch, Fedora, Linux Mint, openSUSE, Ubuntu, etc).

If you don't have Flatpak installed you can find step by step instructions [here](https://flatpak.org/setup/).

Make sure to have the Flathub remote added to the current user:

```bash
flatpak --user remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```

#### Install
```bash
flatpak --user install flathub com.leinardi.gwe
flatpak update # needed to be sure to have the latest org.freedesktop.Platform.GL.nvidia
```

#### Run
```bash
flatpak run com.leinardi.gwe
```
#### ⚠ Flatpak limitations
##### Beta Drivers
Currently [Flatpak does not support Nvidia Beta drivers](https://github.com/flathub/org.freedesktop.Platform.GL.nvidia/issues/1)
like 396.54.09 or 415.22.05.

##### Bumblebee and Optimus
Currently [Flatpak does not support Bumblebee](https://github.com/flatpak/flatpak/issues/869). If you want to use GWE with Bumblebee
you need to install it from the source code.

### Distro specific packages
#### Arch Linux
Install the `gwe` package from the AUR using your favourite helper, for example `yay -S gwe`.

#### Fedora
GWE avaliable in official Fedora [repos](https://src.fedoraproject.org/rpms/gwe) for F31+: `sudo dnf install gwe`

For older Fedora releases you can use [COPR package](https://copr.fedorainfracloud.org/coprs/atim/gwe/): `sudo dnf copr enable atim/gwe -y && sudo dnf install gwe`

### Install from source code
#### Build time dependencies
| Distro                | pkg-config         | Python 3.6+   | gobject-introspection       | meson | ninja-build | appstream-util |
| --------------------- | ------------------ | ------------- | --------------------------- | ----- | ----------- | -------------- |
| Arch Linux            | pkg-config         | python        | gobject-introspection       | meson | ninja       | appstream-glib |
| Fedora                | pkgconf-pkg-config | python3-devel | gobject-introspection-devel | meson | ninja-build | appstream-util |
| OpenSUSE              | pkgconf-pkg-config | python3-devel | gobject-introspection-devel | meson | ninja-build | appstream-glib |
| Ubuntu                | pkg-config         | python3-dev   | libgirepository1.0-dev      | meson | ninja-build | appstream-util |


#### Run time dependencies
| Distro                | Python 3.6+ | pip         | gobject-introspection       | libappindicator          | gnome-shell-extension-appindicator | libdazzle |
| --------------------- | ----------- | ----------- | --------------------------- | ------------------------ | ---------------------------------- | --------- |
| Arch Linux            | python      | python-pip  | gobject-introspection       | libappindicator3         | gnome-shell-extension-appindicator | libdazzle |
| Fedora                | python3     | python3-pip | gobject-introspection-devel | libappindicator-gtk3     | gnome-shell-extension-appindicator | libdazzle |
| OpenSUSE              | python3     | python3-pip | gobject-introspection       | libappindicator3-1       | gnome-shell-extension-appindicator | typelib-1_0-libdazzle-1_0 |
| Ubuntu                | python3     | python3-pip | libgirepository1.0-dev      | gir1.2-appindicator3-0.1 | gnome-shell-extension-appindicator | libdazzle-1.0-dev |

plus all the Python dependencies listed in [requirements.txt](requirements.txt)

#### Clone project and install
If you have not installed GWE yet:
```bash
git clone --recurse-submodules -j4 https://gitlab.com/leinardi/gwe.git
cd gwe
git checkout release
sudo -H pip3 install -r requirements.txt
meson . build --prefix /usr
ninja -v -C build
sudo ninja -v -C build install
```

#### Update old installation
If you installed GWE from source code previously and you want to update it:
```bash
cd gwe
git fetch
git checkout release
git reset --hard origin/release
git submodule init
git submodule update
sudo -H pip3 install -r requirements.txt
meson . build --prefix /usr
ninja -v -C build
sudo ninja -v -C build install
```

#### Run
Once installed, to start it you can simply execute on a terminal:
```bash
gwe
```

#### ⚠ Bumblebee and Optimus
If you want to use GWE with Bumblebee you need to start it with `optirun` and set the `--ctrl-display` parameter to `:8`:

```bash
optirun gwe --ctrl-display ":8"
```

## ℹ️ TODO

- [x] Show general GPU info
- [x] Show power info
- [x] Show clocks info
- [x] Show GPU temp in both app and app indicator
- [x] Show fan info
- [x] Allow to hide main app window
- [x] Add command line option to start the app hidden
- [x] Add Refresh timeout to settings
- [x] Add command line option to add desktop entry
- [x] About dialog
- [x] Distributing with PyPI
- [x] Show chart of selected fan profile
- [x] Allow to select and apply a fan profile
- [x] Add/Delete/Edit multi speed fan profiles (fan curve)
- [x] Add option to restore last applied fan profile on app startup
- [x] Find better icons for app indicator
- [x] Try to lower resource consumption (mostly caused by `nvidia-settings` invocations)
- [x] Show historical data of most important values in a separate dialog (requires GTK 3.24/GNOME 3.30)
- [x] Add overclock profiles
- [x] Add option to restore last applied overclock profile on app startup
- [ ] Disable unsupported preferences
- [x] Distributing with Flatpak
- [x] Publishing on Flathub
- [ ] Distributing with Snap
- [x] Check if NV-CONTROL is available and tell the user if is not
- [ ] Add support for multi-GPU
- [ ] Allow to select profiles from app indicator
- [ ] Add support for i18n (internationalization and localization)

<!--
## Application entry
To add a desktop entry for the application run the following command (not supported by Flatpak):
```bash
gwe --application-entry
```
If you don't want to create this custom rule you can run gwe as root
(using sudo) but we advise against this solution.
-->
## ⌨️ Command line options

  | Parameter                 | Description                               | Source | Flatpak |
  |---------------------------|-------------------------------------------|:------:|:-------:|
  |-v, --version              |Show the app version                       |    x   |    x    |
  |--debug                    |Show debug messages                        |    x   |    x    |
  |--hide-window              |Start with the main window hidden          |    x   |    x    |
  |--ctrl-display DISPLAY     |Specify the NV-CONTROL display             |    x   |    x    |
  |--autostart-on             |Enable automatic start of the app on login |    x   |         |
  |--autostart-off            |Disable automatic start of the app on login|    x   |         |

## 🖥️ Build, install and run with Flatpak
If you don't have Flatpak installed you can find step by step instructions [here](https://flatpak.org/setup/).

Make sure to have the Flathub remote added to the current user:

```bash
flatpak --user remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```

### Clone the repo
```bash
git clone --recurse-submodules -j4 https://gitlab.com/leinardi/gwe.git
```
It is possible to build the local source or the remote one (the same that Flathub uses)
### Local repository
```bash
./build.sh --flatpak-local --flatpak-install
```
### Remote repository
```bash
./build.sh --flatpak-remote --flatpak-install
```
### Run
```bash
flatpak run com.leinardi.gwe --debug
```

## ❓ FAQ
### I see some message about CoolBits in the Overclock/Fan profile section, what's that?
Coolbits was a Windows registry hack for Nvidia graphics cards Windows drivers, that allows
tweaking features via the Nvidia driver control panel.
Something similar is available also on Linux and is the only way to enable Overclock and manual Fan control.
To know more about Coolbits and how to enable them click
[here](https://wiki.archlinux.org/index.php/NVIDIA/Tips_and_tricks#Enabling_overclocking)
(to enable both OC and Fan control you need to set it to `12`).

### Can I make the power limit survive a reboot?
GWE cannot set the power limit automatically because, to change this value, root permission is required.  
If your distribution is using systemd, you can easily set the power limit on boot creating a custom service.

Simply create a new file `/etc/systemd/system/nvidia-tdp.timer` and paste the following text inside:
```
[Unit]
Description=Set NVIDIA power limit on boot

[Timer]
OnBootSec=5

[Install]
WantedBy=timers.target
```

Then create another file `/etc/systemd/system/nvidia-tdp.service` and paste the following text inside (replace `XXX` with the power limit value you want to set):
```
[Unit]
Description=Set NVIDIA power limit

[Service]
Type=oneshot
ExecStartPre=/usr/bin/nvidia-smi -pm 1
ExecStart=/usr/bin/nvidia-smi -pl XXX
```

Finally, run the following command:
```
sudo systemctl enable nvidia-tdp.timer
```

### The Flatpak version of GWE is not using my theme, how can I fix it?
To fix this issue install a Gtk theme from Flathub. This way, Flatpak applications will automatically pick the
installed Gtk theme and use that instead of Adwaita.

Use this command to get a list of all the available Gtk themes on Flathub:
```bash
flatpak --user remote-ls flathub | grep org.gtk.Gtk3theme
```
And then just install your preferred theme. For example, to install Yaru:
```
flatpak install flathub org.gtk.Gtk3theme.Yaru
```

### I have installed the app using Flatpak, but all the GWE fields are empty
This issue can be usually solved by closing GWE, executing `flatpak update` and starting GWE again.
This is necessary to be sure to have the latest [org.freedesktop.Platform.GL.nvidia](https://github.com/flathub/org.freedesktop.Platform.GL.nvidia).
If, after the update, all the fields are still empty, feel free to open a new issue on the project tracker.

### Why the memory overclock offsets effectively applied does not match the one set in the Nvidia Settings app?
Because Memory Transfer Rate, what Nvidia Settings reports and changes,
is different from the effective Memory Clock, what is actually being
displayed by GWE. It is also what other Windows applications like MSI Afterburner show.
The Memory Transfer Rate is simply double the Memory Clock.

### Where are the settings and profiles stored on the filesystem?
| Installation type |                     Location                     |
|-------------------|:------------------------------------------------:|
| Flatpak           |        `$HOME/.var/app/com.leinardi.gwe/`        |
| Source code       | `$XDG_CONFIG_HOME` (usually `$HOME/.config/gwe`) |

### GreenWithEnvy, why using such name?
The name comes from the slogan of the GeForce 8 series, that was "Green with envy".
Nvidia is meant to be pronounced "invidia", which means envy in Latin (and Italian). And their logo is green so, GreenWithEnvy

## 💚 How to help the project
### Help is needed for the following topics
 - Snap (see [#18](https://gitlab.com/leinardi/gwe/issues/18))
 - Getting current GTK theme text color (see [#36](https://gitlab.com/leinardi/gwe/issues/36))
 - Making Bumblebee work with Flatpak (see [#35](https://gitlab.com/leinardi/gwe/issues/35))

### Discord server
If you want to help testing or developing it would be easier to get in touch using the discord server of the project: https://discord.gg/xBybdRt
Just write a message on the general channel saying how you want to help (test, dev, etc) and quoting @leinardi. If you don't use discor but still want to help just open a new issue here.


### Can I support this project some other way?

Something simple that everyone can do is to star it on both [GitLab](https://gitlab.com/leinardi/gwe) and [GitHub](https://github.com/leinardi/gwe).
Feedback is always welcome: if you found a bug or would like to suggest a feature,
feel free to open an issue on the [issue tracker](https://gitlab.com/leinardi/gwe/issues).

## ⚠ Dropped PyPI support
Development builds were previously distributed using PyPI. This way of distributing the software is simple
but requires the user to manually install all the non Python dependencies like cairo, glib, appindicator3, etc.
The current implementation of the historical data uses a new library, Dazzle, that requires Gnome 3.30 which is
available, using Python Object introspection, only starting from Ubuntu 18.10 making the latest Ubuntu LTS, 18.04,
unsupported.
A solution for all this problems is distributing the app via Flatpak, since with it all the dependencies
will be bundled and provided automatically, making possible to use Gnome 3.30 features also on distributions
using an older version of Gnome.

**No new build will be published on PyPI**.

### Uninstall pip version
If you have already installed GWE via `pip`, please make sure to uninstall it completely before moving to a newer version:

```bash
pip3 uninstall gwe
rm -rf ~/.config/gwe
```

## ℹ️ Acknowledgements
Thanks to:

 - GabMus and TingPing for the huge help with Flatpak
 - @999eagle for maintaining the [AUR package](https://aur.archlinux.org/packages/gwe/)
 - @tim74 for maintaining the [COPR package](https://copr.fedorainfracloud.org/coprs/atim/gwe/)
 - Lighty for moderating the [Discord](https://discord.gg/YjPdNff) server
 - fbcotter for the [py3nvml](https://github.com/fbcotter/py3nvml/) library
 - all the devs of the [python-xlib](https://github.com/python-xlib/python-xlib/) library
 - tiheum for the [Faenza](https://www.deviantart.com/tiheum/art/Faenza-Icons-173323228) icons set, from which I took the current GWE launcher icon
 - all the people that helped testing and reported bugs

## 📰 Media coverage
 - [OMG! Ubuntu](https://www.omgubuntu.co.uk/2019/02/easily-overclock-nvidia-gpu-on-linux-with-this-new-app) 🇬🇧
 - [GamingOnLinux](https://www.gamingonlinux.com/articles/greenwithenvy-an-impressive-tool-for-overclocking-nvidia-gpus.13521) 🇬🇧
 - [Phoronix](https://www.phoronix.com/scan.php?page=news_item&px=GreenWithEnvy-0.11-Released) 🇬🇧
 - [ComputerBase](https://www.computerbase.de/2019-02/green-envy-uebertakten-nvidia-grafikkarten-linux/) 🇩🇪
 - [lffl](https://www.lffl.org/2019/02/overclock-scheda-nvidia-linux.html) 🇮🇹
 - [osside blog](https://www.osside.net/2019/02/greenwithenvy-gwe-linux-easy-nvidia-status-overclock/) 🇮🇹
 - [Diolinux](https://www.diolinux.com.br/2019/02/greenwithenvy-uma-nova-forma-de-voce-gerenciar-gpu-nvidia.html?m=1) 🇧🇷
 - [Blog do Edivaldo](https://www.edivaldobrito.com.br/overclock-em-gpus-nvidia-no-linux/) 🇧🇷
 - [Linux Adictos](https://www.linuxadictos.com/greenwithenvy-programa-para-overclocking-en-gpus-nvidia.html) 🇪🇸


## 📝 License
```
This file is part of gwe.

Copyright (c) 2019 Roberto Leinardi

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
