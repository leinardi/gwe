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
import re
from typing import Any, Dict

from gi.repository import Gtk
from injector import singleton, inject

from gwe.conf import SETTINGS_DEFAULTS
from gwe.interactor import SettingsInteractor
from gwe.util.deployment import is_flatpak
from gwe.util.desktop_entry import set_autostart_entry, AUTOSTART_FILE_PATH

LOG = logging.getLogger(__name__)


class PreferencesViewInterface:
    def show(self) -> None:
        raise NotImplementedError()

    def hide(self) -> None:
        raise NotImplementedError()

    def refresh_settings(self, settings: Dict[str, Any]) -> None:
        raise NotImplementedError()


@singleton
class PreferencesPresenter:
    @inject
    def __init__(self,
                 settings_interactor: SettingsInteractor,
                 ) -> None:
        LOG.debug("init PreferencesPresenter ")
        self.view: PreferencesViewInterface = PreferencesViewInterface()
        self._settings_interactor = settings_interactor

    def show(self) -> None:
        self._init_settings()
        self.view.show()

    def _init_settings(self) -> None:
        settings: Dict[str, Any] = {}
        for key, default_value in SETTINGS_DEFAULTS.items():
            if isinstance(default_value, bool):
                if key == 'settings_launch_on_login' and not AUTOSTART_FILE_PATH.is_file():
                    self._settings_interactor.set_bool(key, False)
                settings[key] = self._settings_interactor.get_bool(key)
            elif isinstance(default_value, int):
                settings[key] = self._settings_interactor.get_int(key)
        self.view.refresh_settings(settings)

    def on_setting_changed(self, widget: Any, *args: Any) -> None:
        if isinstance(widget, Gtk.Switch):
            value = args[0]
            key = re.sub('_switch$', '', widget.get_name())
            self._settings_interactor.set_bool(key, value)
            if key == 'settings_launch_on_login' and not is_flatpak():
                set_autostart_entry(value)
        elif isinstance(widget, Gtk.SpinButton):
            key = re.sub('_spinbutton$', '', widget.get_name())
            value = widget.get_value_as_int()
            self._settings_interactor.set_int(key, value)
