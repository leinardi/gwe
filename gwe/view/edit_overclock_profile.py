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

from gi.repository import Gtk
from injector import singleton, inject

from gwe.di import EditOverclockProfileBuilder
from gwe.model import OverclockProfile, Overclock
from gwe.presenter.edit_overclock_profile import EditOverclockProfileViewInterface, EditOverclockProfilePresenter

LOG = logging.getLogger(__name__)


@singleton
class EditOverclockProfileView(EditOverclockProfileViewInterface):
    @inject
    def __init__(self,
                 presenter: EditOverclockProfilePresenter,
                 builder: EditOverclockProfileBuilder,
                 ) -> None:
        LOG.debug('init EditOverclockProfileView')
        self._presenter: EditOverclockProfilePresenter = presenter
        self._presenter.view = self
        self._builder: Gtk.Builder = builder
        self._builder.connect_signals(self._presenter)
        self._init_widgets()

    def _init_widgets(self) -> None:
        self._dialog: Gtk.Dialog = self._builder.get_object('dialog')
        self._delete_profile_button: Gtk.Button = self._builder.get_object('delete_profile_button')
        self._profile_name_entry: Gtk.Entry = self._builder.get_object('profile_name_entry')
        self._apply_offsets_button: Gtk.Button = self._builder.get_object('apply_offsets_button')
        self._save_offsets_button: Gtk.Button = self._builder.get_object('save_offsets_button')
        self._gpu_offset_scale: Gtk.Scale = self._builder.get_object('gpu_offset_scale')
        self._memory_offset_scale: Gtk.Scale = self._builder.get_object('memory_offset_scale')
        self._gpu_offset_adjustment: Gtk.Adjustment = self._builder.get_object(
            'gpu_offset_adjustment')
        self._memory_offset_adjustment: Gtk.Adjustment = self._builder.get_object(
            'memory_offset_adjustment')

    def set_transient_for(self, window: Gtk.Window) -> None:
        self._dialog.set_transient_for(window)

    def show(self, profile: OverclockProfile, overclock: Overclock) -> None:
        self._update_ui(profile, overclock)
        self._dialog.show_all()

    def hide(self) -> None:
        self._dialog.hide()

    def get_profile_name(self) -> str:
        return str(self._profile_name_entry.get_text())

    def get_gpu_offset(self) -> int:
        return int(self._gpu_offset_adjustment.get_value())

    def get_memory_offset(self) -> int:
        return int(self._memory_offset_adjustment.get_value())

    def _update_ui(self, profile: OverclockProfile, overclock: Overclock) -> None:
        self._profile_name_entry.set_text(profile.name)
        self._profile_name_entry.set_text(profile.name)
        self._gpu_offset_adjustment.set_lower(overclock.gpu_range[0])
        self._gpu_offset_adjustment.set_upper(overclock.gpu_range[1])
        self._memory_offset_adjustment.set_lower(overclock.memory_range[0])
        self._memory_offset_adjustment.set_upper(overclock.memory_range[1])
        self._gpu_offset_adjustment.set_value(profile.gpu)
        self._memory_offset_adjustment.set_value(profile.memory)
        self._gpu_offset_scale.clear_marks()
        self._gpu_offset_scale.add_mark(0, Gtk.PositionType.BOTTOM, str(0))
        self._memory_offset_scale.clear_marks()
        self._memory_offset_scale.add_mark(0, Gtk.PositionType.BOTTOM, str(0))
