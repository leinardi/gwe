# This file is part of gwe.
#
# Copyright (c) 2018 Roberto Leinardi
#
# gsi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gsi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gsi.  If not, see <http://www.gnu.org/licenses/>.
import logging
from typing import Optional, Any

from gi.repository import Gtk
from injector import singleton, inject

from gwe.conf import MIN_TEMP, FAN_MIN_DUTY
from gwe.model import FanProfile, SpeedStep
from gwe.util.view import hide_on_delete

LOG = logging.getLogger(__name__)


class EditFanProfileViewInterface:
    def show(self, profile: FanProfile) -> None:
        raise NotImplementedError()

    def hide(self) -> None:
        raise NotImplementedError()

    def get_profile_name(self) -> str:
        raise NotImplementedError()

    def get_temperature(self) -> int:
        raise NotImplementedError()

    def get_duty(self) -> int:
        raise NotImplementedError()

    def has_a_step_selected(self) -> bool:
        raise NotImplementedError()

    def refresh_controls(self, step: Optional[SpeedStep] = None, unselect_list: bool = False) -> None:
        raise NotImplementedError()

    def refresh_liststore(self, profile: FanProfile) -> None:
        raise NotImplementedError()


@singleton
class EditFanProfilePresenter:
    @inject
    def __init__(self) -> None:
        LOG.debug("init EditFanProfilePresenter ")
        self.view: EditFanProfileViewInterface = EditFanProfileViewInterface()
        self._profile = FanProfile()
        self._selected_step: Optional[SpeedStep] = None

    def show_add(self) -> None:
        profile = FanProfile()
        profile.name = 'New profile'
        profile.save()
        self.show_edit(profile)

    def show_edit(self, profile: FanProfile) -> None:
        self._profile = profile
        self.view.show(profile)

    def on_dialog_delete_event(self, widget: Gtk.Widget, *_: Any) -> Any:
        if self._profile is not None:
            name = self.view.get_profile_name()
            if name != self._profile.name:
                self._profile.name = name
                self._profile.save()
        return hide_on_delete(widget)

    def refresh_controls(self, step: Optional[SpeedStep] = None, deselect_list: bool = False) -> None:
        self._selected_step = step
        self.view.refresh_controls(step, deselect_list)

    def on_step_selected(self, tree_selection: Gtk.TreeSelection) -> None:
        LOG.debug("selected")
        list_store, tree_iter = tree_selection.get_selected()
        step = None if tree_iter is None else SpeedStep.get_or_none(id=list_store.get_value(tree_iter, 0))
        self.refresh_controls(step)

    def on_add_step_clicked(self, *_: Any) -> None:
        step = SpeedStep()
        step.profile = self._profile
        last_steps = (SpeedStep
                      .select()
                      .where(SpeedStep.profile == step.profile)
                      .order_by(SpeedStep.temperature.desc())
                      .limit(1))
        if not last_steps:
            step.temperature = MIN_TEMP
            step.duty = FAN_MIN_DUTY
        else:
            step.temperature = last_steps[0].temperature + 1
            step.duty = last_steps[0].duty

        self.refresh_controls(step, True)

    def on_add_profile_clicked(self, *_: Any) -> None:
        self._profile.delete_instance(recursive=True)
        self.view.hide()

    def on_delete_profile_clicked(self, *_: Any) -> None:
        self._profile.delete_instance(recursive=True)
        self.view.hide()

    def on_delete_step_clicked(self, *_: Any) -> None:
        self._selected_step.delete_instance()
        self.view.refresh_liststore(self._profile)

    def on_save_step_clicked(self, *_: Any) -> None:
        self._selected_step.temperature = self.view.get_temperature()
        self._selected_step.duty = self.view.get_duty()
        self._selected_step.save()
        self.view.refresh_liststore(self._profile)
        if not self.view.has_a_step_selected():
            self.refresh_controls()
