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
from typing import Dict, Any

from gi.repository import Gtk
from injector import singleton, inject

from gwe.di import PreferencesBuilder
from gwe.presenter.preferences_presenter import PreferencesViewInterface, PreferencesPresenter
from gwe.util.deployment import is_flatpak
from gwe.util.view import hide_on_delete

_LOG = logging.getLogger(__name__)


@singleton
class PreferencesView(PreferencesViewInterface):
    @inject
    def __init__(self,
                 presenter: PreferencesPresenter,
                 builder: PreferencesBuilder,
                 ) -> None:
        _LOG.debug('init PreferencesView')
        self._presenter: PreferencesPresenter = presenter
        self._presenter.view = self
        self._builder: Gtk.Builder = builder
        self._builder.connect_signals(self._presenter)
        self._init_widgets()

    def _init_widgets(self) -> None:
        self._dialog: Gtk.Dialog = self._builder.get_object('dialog')
        self._dialog.connect("delete-event", hide_on_delete)
        if is_flatpak():
            self._builder.get_object('settings_launch_on_login_grid').set_sensitive(False)
            self._builder.get_object('settings_launch_on_login_description_label')\
                .set_text("Not supported by Flatpak (see https://github.com/flatpak/flatpak/issues/118)")

    def set_transient_for(self, window: Gtk.Window) -> None:
        self._dialog.set_transient_for(window)

    def show(self) -> None:
        self._dialog.show_all()

    def hide(self) -> None:
        self._dialog.hide()

    def refresh_settings(self, settings: Dict[str, Any]) -> None:
        for key, value in settings.items():
            if isinstance(value, bool):
                switch: Gtk.Switch = self._builder.get_object(key + '_switch')
                switch.set_active(value)
            elif isinstance(value, int):
                spinbutton: Gtk.SpinButton = self._builder.get_object(key + '_spinbutton')
                spinbutton.set_value(value)
