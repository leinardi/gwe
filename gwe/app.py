# This file is part of gwe.
#
# Copyright (c) 2018 Roberto Leinardi
#
# gwe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gwe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gwe.  If not, see <http://www.gnu.org/licenses/>.

import logging
from time import sleep
from enum import Enum
from gettext import gettext as _
from typing import Any, Optional, List

from gi.repository import Gtk, Gio, GLib
from injector import inject, singleton

from gwe.conf import APP_NAME, APP_ID, APP_VERSION, APP_ICON_NAME
from gwe.di import MainBuilder
from gwe.model import load_fan_db_default_data, load_overclock_db_default_data
from gwe.model.fan_profile import FanProfile
from gwe.model.overclock_profile import OverclockProfile
from gwe.presenter.main_presenter import MainPresenter
from gwe.repository.nvidia_repository import NvidiaRepository
from gwe.util.deployment import is_flatpak
from gwe.util.desktop_entry import set_autostart_entry, add_application_entry
from gwe.util.log import LOG_DEBUG_FORMAT
from gwe.util.view import build_glib_option
from gwe.view.main_view import MainView

_LOG = logging.getLogger(__name__)


@singleton
class Application(Gtk.Application):
    @inject
    def __init__(self,
                 view: MainView,
                 presenter: MainPresenter,
                 builder: MainBuilder,
                 nvidia_repository: NvidiaRepository,
                 *args: Any,
                 **kwargs: Any) -> None:
        _LOG.debug("init Application")
        GLib.set_application_name(_(APP_NAME))
        super().__init__(*args, application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                         **kwargs)
        if FanProfile.select().count() == 0:
            load_fan_db_default_data()
        if OverclockProfile.select().count() == 0:
            load_overclock_db_default_data()

        self.add_main_option_entries(self._get_main_option_entries())
        self._view = view
        self._presenter = presenter
        self._nvidia_repository = nvidia_repository
        self._window: Optional[Gtk.ApplicationWindow] = None
        self._builder: Gtk.Builder = builder
        self._start_hidden: bool = False

    def do_activate(self) -> None:
        if not self._window:
            self._builder.connect_signals(self._presenter)
            self._window: Gtk.ApplicationWindow = self._builder.get_object("application_window")
            self._window.set_icon_name(APP_ICON_NAME)
            self._window.set_application(self)
            self._window.show_all()
            self._view.show()
        self._window.present()
        if self._start_hidden:
            self._window.hide()
            self._start_hidden = False

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:

        start_app = True
        options = command_line.get_options_dict()
        # convert GVariantDict -> GVariant -> dict
        options = options.end().unpack()

        exit_value = 0
        if _Options.DEBUG.value in options:
            logging.getLogger().setLevel(logging.DEBUG)
            for handler in logging.getLogger().handlers:
                handler.formatter = logging.Formatter(LOG_DEBUG_FORMAT)
            _LOG.debug(f"Option {_Options.DEBUG.value} selected")

        if _Options.VERSION.value in options:
            _LOG.debug(f"Option {_Options.VERSION.value} selected")
            print(APP_VERSION)
            start_app = False

        if _Options.HIDE_WINDOW.value in options:
            _LOG.debug(f"Option {_Options.HIDE_WINDOW.value} selected")
            self._start_hidden = True

        if _Options.AUTOSTART_ON.value in options:
            _LOG.debug(f"Option {_Options.AUTOSTART_ON.value} selected")
            set_autostart_entry(True)
            start_app = False

        if _Options.AUTOSTART_OFF.value in options:
            _LOG.debug(f"Option {_Options.AUTOSTART_OFF.value} selected")
            set_autostart_entry(False)
            start_app = False

        if _Options.CTRL_DISPLAY.value in options:
            param = options[_Options.CTRL_DISPLAY.value]
            _LOG.debug(f"Option {_Options.CTRL_DISPLAY.value} selected: {param}")
            self._nvidia_repository.set_ctrl_display(param)

        if _Options.DELAY.value in options:
            sleep(3)

        if start_app:
            self.activate()
        return exit_value

    @staticmethod
    def _get_main_option_entries() -> List[GLib.OptionEntry]:
        options = [
            build_glib_option(_Options.DEBUG.value,
                              description="Show debug messages"),
            build_glib_option(_Options.VERSION.value,
                              short_name='v',
                              description="Show the App version"),
            build_glib_option(_Options.HIDE_WINDOW.value,
                              description="Start with the main window hidden"),
            build_glib_option(_Options.DELAY.value,
                              description="Set a small delay on start"),
            build_glib_option(_Options.CTRL_DISPLAY.value,
                              arg=GLib.OptionArg.STRING,
                              description="Specify the NV-CONTROL display (if you use Bumblebee, set this to \":8\" "
                                          "and start GWE with optirun)"),
        ]
        if not is_flatpak():
            options.append(build_glib_option(_Options.AUTOSTART_ON.value,
                                             description="Enable automatic start of the App on login"))
            options.append(build_glib_option(_Options.AUTOSTART_OFF.value,
                                             description="Disable automatic start of the App on login"))
        return options


class _Options(Enum):
    DEBUG = 'debug'
    VERSION = 'version'
    HIDE_WINDOW = 'hide-window'
    CTRL_DISPLAY = 'ctrl-display'
    AUTOSTART_ON = 'autostart-on'
    AUTOSTART_OFF = 'autostart-off'
    DELAY = 'delay'
