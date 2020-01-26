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
from collections import OrderedDict
from typing import Optional, Dict

from gi.repository import Gtk
from injector import singleton, inject
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
from matplotlib.figure import Figure

from gwe.conf import MIN_TEMP, FAN_MIN_DUTY, MAX_TEMP, FAN_MAX_DUTY
from gwe.di import EditFanProfileBuilder
from gwe.presenter.edit_fan_profile_presenter import EditFanProfileViewInterface, EditFanProfilePresenter
from gwe.util.view import init_plot_chart, get_fan_profile_data
from gwe.model.fan_profile import FanProfile
from gwe.model.speed_step import SpeedStep

LOG = logging.getLogger(__name__)


@singleton
class EditFanProfileView(EditFanProfileViewInterface):
    @inject
    def __init__(self,
                 presenter: EditFanProfilePresenter,
                 builder: EditFanProfileBuilder,
                 ) -> None:
        LOG.debug('init EditFanProfileView')
        self._presenter: EditFanProfilePresenter = presenter
        self._presenter.view = self
        self._builder: Gtk.Builder = builder
        self._builder.connect_signals(self._presenter)
        self._init_widgets()

    def _init_widgets(self) -> None:
        self._dialog: Gtk.Dialog = self._builder.get_object('dialog')
        self._delete_profile_button: Gtk.Button = self._builder \
            .get_object('delete_profile_button')
        self._profile_name_entry: Gtk.Entry = self._builder \
            .get_object('profile_name_entry')
        self._liststore: Gtk.ListStore = self._builder.get_object('liststore')
        self._temperature_adjustment: Gtk.Adjustment = self._builder \
            .get_object('temperature_adjustment')
        self._duty_adjustment: Gtk.Adjustment = self._builder \
            .get_object('duty_adjustment')
        self._temperature_scale: Gtk.Scale = self._builder \
            .get_object('temperature_scale')
        self._duty_scale: Gtk.Scale = self._builder \
            .get_object('duty_scale')
        self._controls_grid: Gtk.Grid = self._builder.get_object('controls_grid')
        self._treeselection: Gtk.TreeSelection = self._builder.get_object('treeselection')
        self._treeview: Gtk.TreeView = self._builder.get_object('treeview')
        self._add_step_button: Gtk.Button = self._builder.get_object('add_step_button')
        self._save_step_button: Gtk.Button = self._builder \
            .get_object('save_step_button')
        self._delete_step_button: Gtk.Button = self._builder \
            .get_object('delete_step_button')
        self._init_plot_charts()

    def set_transient_for(self, window: Gtk.Window) -> None:
        self._dialog.set_transient_for(window)

    # pylint: disable=attribute-defined-outside-init
    def _init_plot_charts(self, ) -> None:
        self._chart_figure = Figure(figsize=(8, 6), dpi=72, facecolor='#00000000')
        self._chart_canvas = FigureCanvas(self._chart_figure)  # a Gtk.DrawingArea+
        self._chart_axis = self._chart_figure.add_subplot(111)
        self._chart_line, = init_plot_chart(
            self._builder.get_object('scrolled_window'),
            self._chart_figure,
            self._chart_canvas,
            self._chart_axis
        )

    def _plot_chart(self, data: Dict[int, int]) -> None:
        sorted_data = OrderedDict(sorted(data.items()))
        temperature = list(sorted_data.keys())
        duty = list(sorted_data.values())
        self._chart_line.set_xdata(temperature)
        self._chart_line.set_ydata(duty)
        self._chart_canvas.draw()
        self._chart_canvas.flush_events()

    def show(self, profile: FanProfile) -> None:
        self._treeselection.unselect_all()
        self._profile_name_entry.set_text(profile.name)
        self.refresh_liststore(profile)
        self.refresh_controls()
        self._dialog.show_all()

    def hide(self) -> None:
        self._dialog.hide()

    def get_profile_name(self) -> str:
        return str(self._profile_name_entry.get_text())

    def get_temperature(self) -> int:
        return int(self._temperature_adjustment.get_value())

    def get_duty(self) -> int:
        return int(self._duty_adjustment.get_value())

    def has_a_step_selected(self) -> bool:
        return self._treeselection.get_selected()[1] is not None

    def refresh_liststore(self, profile: FanProfile) -> None:
        self._liststore.clear()
        for step in profile.steps:
            self._liststore.append([step.id, step.temperature, step.duty])
        if profile.steps:
            if profile.steps[-1].temperature == MAX_TEMP or profile.steps[-1].duty == FAN_MAX_DUTY:
                self._add_step_button.set_sensitive(False)
            else:
                self._add_step_button.set_sensitive(True)
        else:
            self._add_step_button.set_sensitive(True)

        self._plot_chart(get_fan_profile_data(profile))

    def refresh_controls(self, step: Optional[SpeedStep] = None, unselect_list: bool = False) -> None:
        if unselect_list:
            self._treeselection.unselect_all()
        if step is None:
            self._controls_grid.set_sensitive(False)
        else:
            prev_steps = (SpeedStep
                          .select()
                          .where(SpeedStep.profile == step.profile, SpeedStep.temperature < step.temperature)
                          .order_by(SpeedStep.temperature.desc())
                          .limit(1))
            next_steps = (SpeedStep
                          .select()
                          .where(SpeedStep.profile == step.profile, SpeedStep.temperature > step.temperature)
                          .order_by(SpeedStep.temperature)
                          .limit(1))
            if not prev_steps:
                self._temperature_adjustment.set_lower(MIN_TEMP)
                self._duty_adjustment.set_lower(FAN_MIN_DUTY)
            else:
                LOG.debug(f"prev = {prev_steps[0].temperature}")
                self._temperature_adjustment.set_lower(prev_steps[0].temperature + 1)
                self._duty_adjustment.set_lower(prev_steps[0].duty)

            if not next_steps:
                self._temperature_adjustment.set_upper(MAX_TEMP)
                self._duty_adjustment.set_upper(FAN_MAX_DUTY)
            else:
                self._temperature_adjustment.set_upper(next_steps[0].temperature - 1)
                self._duty_adjustment.set_upper(next_steps[0].duty)

            self._controls_grid.set_sensitive(True)
            self._temperature_scale.clear_marks()
            self._temperature_scale.add_mark(step.temperature, Gtk.PositionType.BOTTOM)
            self._temperature_adjustment.set_value(step.temperature)
            self._duty_scale.clear_marks()
            self._duty_scale.add_mark(step.duty, Gtk.PositionType.BOTTOM)
            self._duty_adjustment.set_value(step.duty)
