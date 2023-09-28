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
from typing import Optional, Dict, List, Tuple, Any

from injector import inject, singleton
from gi.repository import Gtk
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas

from gwe.interactor.settings_interactor import SettingsInteractor
from gwe.model.status import Status
from gwe.model.fan_profile import FanProfile

try:  # AppIndicator3 may not be installed
    import gi

    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3
except (ImportError, ValueError):
    AppIndicator3 = None
from gwe.di import MainBuilder
from gwe.view.edit_fan_profile_view import EditFanProfileView
from gwe.util.view import hide_on_delete, init_plot_chart, get_fan_profile_data, is_dazzle_version_supported
from gwe.view.edit_overclock_profile_view import EditOverclockProfileView
from gwe.view.historical_data_view import HistoricalDataView
from gwe.view.preferences_view import PreferencesView
from gwe.conf import APP_PACKAGE_NAME, APP_ID, APP_NAME, APP_VERSION, APP_SOURCE_URL, APP_ICON_NAME_SYMBOLIC
from gwe.presenter.main_presenter import MainPresenter, MainViewInterface

_LOG = logging.getLogger(__name__)
if AppIndicator3 is None:
    _LOG.warning("AppIndicator3 is not installed. The App indicator will not be shown.")


@singleton
class MainView(MainViewInterface):

    @inject
    def __init__(self,
                 presenter: MainPresenter,
                 edit_fan_profile_view: EditFanProfileView,
                 edit_overclock_profile_view: EditOverclockProfileView,
                 historical_data_view: HistoricalDataView,
                 preferences_view: PreferencesView,
                 builder: MainBuilder,
                 settings_interactor: SettingsInteractor,
                 ) -> None:
        _LOG.debug('init MainView')
        self._presenter: MainPresenter = presenter
        self._edit_fan_profile_view = edit_fan_profile_view
        self._edit_overclock_profile_view = edit_overclock_profile_view
        self._historical_data_view = historical_data_view
        self._preferences_view = preferences_view
        self._presenter.main_view = self
        self._builder: Gtk.Builder = builder
        self._settings_interactor = settings_interactor
        self._first_refresh = True
        self._init_widgets()

    def _init_widgets(self) -> None:
        self._app_indicator: Optional[AppIndicator3.Indicator] = None
        self._window = self._builder.get_object("application_window")
        self._edit_fan_profile_view.set_transient_for(self._window)
        self._edit_overclock_profile_view.set_transient_for(self._window)
        self._historical_data_view.set_transient_for(self._window)
        self._preferences_view.set_transient_for(self._window)
        self._main_menu: Gtk.Menu = self._builder.get_object("main_menu")
        self._main_infobar: Gtk.InfoBar = self._builder.get_object("main_infobar")
        self._main_infobar.connect("response", lambda b, _: b.set_revealed(False))
        self._main_infobar_label: Gtk.Label = self._builder.get_object("main_infobar_label")
        self._main_infobar.set_revealed(False)
        self._statusbar: Gtk.Statusbar = self._builder.get_object('statusbar')
        self._context = self._statusbar.get_context_id(APP_PACKAGE_NAME)
        self._app_version: Gtk.Label = self._builder.get_object('app_version')
        self._app_version.set_label(f"{APP_NAME} v{APP_VERSION}")
        self._about_dialog: Gtk.AboutDialog = self._builder.get_object("about_dialog")
        self._init_about_dialog()
        self._info_name_entry: Gtk.Entry = self._builder.get_object('info_name_entry')
        self._info_vbios_entry: Gtk.Entry = self._builder.get_object('info_vbios_entry')
        self._info_driver_entry: Gtk.Entry = self._builder.get_object('info_driver_entry')
        self._info_pcie_entry: Gtk.Entry = self._builder.get_object('info_pcie_entry')
        self._info_cuda_entry: Gtk.Entry = self._builder.get_object('info_cuda_entry')
        self._info_uuid_entry: Gtk.Entry = self._builder.get_object('info_uuid_entry')
        self._info_memory_entry: Gtk.Entry = self._builder.get_object('info_memory_entry')
        self._info_memory_interface_entry: Gtk.Entry = self._builder.get_object('info_memory_interface_entry')
        self._info_memory_usage_entry: Gtk.Entry = self._builder.get_object('info_memory_usage_entry')
        self._info_gpu_usage_entry: Gtk.Entry = self._builder.get_object('info_gpu_usage_entry')
        self._info_encoder_usage_entry: Gtk.Entry = self._builder.get_object('info_encoder_usage_entry')
        self._info_decoder_usage_entry: Gtk.Entry = self._builder.get_object('info_decoder_usage_entry')
        self._power_draw_entry: Gtk.Entry = self._builder.get_object('power_draw_entry')
        self._power_limit_entry: Gtk.Entry = self._builder.get_object('power_limit_entry')
        self._power_default_entry: Gtk.Entry = self._builder.get_object('power_default_entry')
        self._power_min_entry: Gtk.Entry = self._builder.get_object('power_min_entry')
        self._power_enforced_entry: Gtk.Entry = self._builder.get_object('power_enforced_entry')
        self._power_max_entry: Gtk.Entry = self._builder.get_object('power_max_entry')
        self._clocks_graphics_current_entry: Gtk.Entry = self._builder.get_object('clocks_graphics_current_entry')
        self._clocks_graphics_max_entry: Gtk.Entry = self._builder.get_object('clocks_graphics_max_entry')
        self._clocks_sm_current_entry: Gtk.Entry = self._builder.get_object('clocks_sm_current_entry')
        self._clocks_sm_max_entry: Gtk.Entry = self._builder.get_object('clocks_sm_max_entry')
        self._clocks_memory_current_entry: Gtk.Entry = self._builder.get_object('clocks_memory_current_entry')
        self._clocks_memory_max_entry: Gtk.Entry = self._builder.get_object('clocks_memory_max_entry')
        self._clocks_video_current_entry: Gtk.Entry = self._builder.get_object('clocks_video_current_entry')
        self._clocks_video_max_entry: Gtk.Entry = self._builder.get_object('clocks_video_max_entry')
        self._overclock_gpu_offset_entry: Gtk.Entry = self._builder.get_object('overclock_gpu_offset_entry')
        self._overclock_mem_offset_entry: Gtk.Entry = self._builder.get_object('overclock_mem_offset_entry')
        self._info_memory_usage_levelbar: Gtk.LevelBar = self._builder.get_object('info_memory_usage_levelbar')
        self._info_gpu_usage_levelbar: Gtk.LevelBar = self._builder.get_object('info_gpu_usage_levelbar')
        self._info_encoder_usage_levelbar: Gtk.LevelBar = self._builder.get_object('info_encoder_usage_levelbar')
        self._info_decoder_usage_levelbar: Gtk.LevelBar = self._builder.get_object('info_decoder_usage_levelbar')
        self._temp_gpu_value: Gtk.Label = self._builder.get_object('temp_gpu_value')
        self._temp_max_gpu_value: Gtk.Label = self._builder.get_object('temp_max_gpu_value')
        self._temp_slowdown_value: Gtk.Label = self._builder.get_object('temp_slowdown_value')
        self._temp_shutdown_value: Gtk.Label = self._builder.get_object('temp_shutdown_value')
        self._fan_duty: Tuple = (
            self._builder.get_object('fan_duty_0'),
            self._builder.get_object('fan_duty_1'),
            self._builder.get_object('fan_duty_2'),
            self._builder.get_object('fan_duty_3'),
            self._builder.get_object('fan_duty_4')
        )
        self._fan_rpm: Tuple = (
            self._builder.get_object('fan_rpm_0'),
            self._builder.get_object('fan_rpm_1'),
            self._builder.get_object('fan_rpm_2'),
            self._builder.get_object('fan_rpm_3'),
            self._builder.get_object('fan_rpm_4')
        )
        self._fan_warning_label: Gtk.Label = self._builder.get_object('fan_warning_label')
        self._overclock_warning_label: Gtk.Label = self._builder.get_object('overclock_warning_label')
        self._fan_profile_frame: Gtk.Frame = self._builder.get_object('fan_profile_frame')
        self._overclock_frame: Gtk.Frame = self._builder.get_object('overclock_frame')
        self._power_limit_scale: Gtk.Scale = self._builder.get_object('power_limit_scale')
        self._power_limit_adjustment: Gtk.Adjustment = self._builder.get_object('power_limit_adjustment')
        self._fan_apply_button: Gtk.Button = self._builder.get_object('fan_apply_button')
        self._overclock_apply_button: Gtk.Button = self._builder.get_object('overclock_apply_button')
        self._power_limit_apply_button: Gtk.Button = self._builder.get_object('power_limit_apply_button')
        self._fan_liststore: Gtk.ListStore = self._builder.get_object('fan_profile_liststore')
        self._overclock_liststore: Gtk.ListStore = self._builder.get_object('overclock_profile_liststore')
        self._fan_combobox: Gtk.ComboBox = self._builder.get_object('fan_profile_combobox')
        self._overclock_combobox: Gtk.ComboBox = self._builder.get_object('overclock_profile_combobox')
        fan_scrolled_window: Gtk.ScrolledWindow = self._builder.get_object('fan_scrolled_window')
        self._fan_edit_button: Gtk.Button = self._builder.get_object('fan_edit_button')
        self._overclock_edit_button: Gtk.Button = self._builder.get_object('overclock_edit_button')
        self._init_plot_charts(fan_scrolled_window)
        if not is_dazzle_version_supported():
            self._builder.get_object("historical_data_button").set_sensitive(False)

    def _init_about_dialog(self) -> None:
        self._about_dialog.set_program_name(APP_NAME)
        self._about_dialog.set_version(APP_VERSION)
        self._about_dialog.set_website(APP_SOURCE_URL)
        self._about_dialog.connect("delete-event", hide_on_delete)
        self._about_dialog.connect("response", hide_on_delete)

    def show(self) -> None:
        self._presenter.on_start()
        self._init_app_indicator()

    def _init_app_indicator(self) -> None:
        if AppIndicator3:
            # Setting icon name in new() as '', because new() wants an icon path
            self._app_indicator = AppIndicator3.Indicator \
                .new(APP_ID, '', AppIndicator3.IndicatorCategory.HARDWARE)
            # Set the actual icon by name. If the App is not installed system-wide, the icon won't show up,
            # otherwise it will show up correctly. The set_icon_full() function needs a description for accessibility
            # purposes. I gave it the APP_NAME (should be 'gwe', maybe change it to 'GreenWithEnvy' in the future)
            self._app_indicator.set_icon_full(APP_ICON_NAME_SYMBOLIC, APP_NAME)
            if self._settings_interactor.get_bool('settings_show_app_indicator'):
                self._app_indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            else:
                self._app_indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
            self._app_indicator.set_menu(self._main_menu)

    def show_main_infobar_message(self, message: str, markup: bool = False) -> None:
        if markup:
            self._main_infobar_label.set_markup(message)
        else:
            self._main_infobar_label.set_label(message)
        self._main_infobar.set_revealed(True)

    def toggle_window_visibility(self) -> None:
        if self._window.props.visible:
            self._window.hide()
        else:
            self._window.show()

    def get_power_limit(self) -> Tuple[int, int]:
        return 0, self._power_limit_adjustment.get_value()

    def set_statusbar_text(self, text: str) -> None:
        self._statusbar.remove_all(self._context)
        self._statusbar.push(self._context, text)

    def show_about_dialog(self) -> None:
        self._about_dialog.show()

    def show_error_message_dialog(self, title: str, message: str) -> None:
        dialog = Gtk.MessageDialog(self._window, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, title)
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def refresh_status(self, status: Optional[Status], gpu_index: int) -> None:
        _LOG.debug('view status')
        if status:
            gpu_status = status.gpu_status_list[gpu_index]
            if self._first_refresh:
                self._first_refresh = False
                self._set_entry_text(self._info_name_entry, gpu_status.info.name)
                self._set_entry_text(self._info_vbios_entry, gpu_status.info.vbios)
                self._set_entry_text(self._info_driver_entry, gpu_status.info.driver)
                self._set_entry_text(self._info_cuda_entry, "{}", gpu_status.info.cuda_cores)
                self._set_entry_text(self._info_uuid_entry, gpu_status.info.uuid)
                self._set_entry_text(self._info_memory_interface_entry, "{} bit", gpu_status.info.memory_interface)
                self._set_entry_text(self._power_min_entry, "{} W", gpu_status.power.minimum)
                self._set_entry_text(self._power_max_entry, "{} W", gpu_status.power.maximum)
                self._set_label_markup(self._temp_max_gpu_value,
                                       "<span size=\"large\">{}</span> °C", gpu_status.temp.maximum)
                self._set_label_markup(self._temp_slowdown_value,
                                       "<span size=\"large\">{}</span> °C", gpu_status.temp.slowdown)
                self._set_label_markup(self._temp_shutdown_value,
                                       "<span size=\"large\">{}</span> °C", gpu_status.temp.shutdown)
                self._overclock_frame.set_sensitive(gpu_status.overclock.available)
                self._overclock_warning_label.set_visible(not gpu_status.overclock.available)
                self._fan_profile_frame.set_sensitive(gpu_status.fan.control_allowed)
                self._fan_warning_label.set_visible(not gpu_status.fan.control_allowed)
                self._remove_level_bar_offsets(self._info_gpu_usage_levelbar)
                self._remove_level_bar_offsets(self._info_memory_usage_levelbar)
                self._remove_level_bar_offsets(self._info_encoder_usage_levelbar)
                self._remove_level_bar_offsets(self._info_decoder_usage_levelbar)
                minimum = gpu_status.power.minimum
                maximum = gpu_status.power.maximum
                default = gpu_status.power.default
                limit = gpu_status.power.limit
                if (minimum is not None and maximum is not None
                        and default is not None and limit is not None
                        and minimum != maximum):
                    self._power_limit_adjustment.set_lower(minimum)
                    self._power_limit_adjustment.set_upper(maximum)
                    self._power_limit_adjustment.set_value(limit)
                    self._power_limit_scale.clear_marks()
                    self._power_limit_scale.add_mark(default, Gtk.PositionType.BOTTOM, f"{default:.0f}")
                    self._power_limit_scale.set_sensitive(True)
                    self._power_limit_apply_button.set_sensitive(True)
                else:
                    self._power_limit_scale.set_sensitive(False)
                    self._power_limit_apply_button.set_sensitive(False)

            self._set_entry_text(self._info_pcie_entry, "{}x Gen{} @ {}x Gen{}",
                                 gpu_status.info.pcie_max_link,
                                 gpu_status.info.pcie_max_generation,
                                 gpu_status.info.pcie_current_link,
                                 gpu_status.info.pcie_current_generation)
            self._set_entry_text(self._info_memory_entry, "{} MiB / {} MiB",
                                 gpu_status.info.memory_used,
                                 gpu_status.info.memory_total)
            self._set_entry_text(self._info_memory_usage_entry, "{}%", gpu_status.info.memory_usage)
            self._set_entry_text(self._info_gpu_usage_entry, "{}%", gpu_status.info.gpu_usage)
            self._set_entry_text(self._info_encoder_usage_entry, "{}%", gpu_status.info.encoder_usage)
            self._set_entry_text(self._info_decoder_usage_entry, "{}%", gpu_status.info.decoder_usage)
            self._set_entry_text(self._power_draw_entry, "{:.2f} W", gpu_status.power.draw)
            self._set_entry_text(self._power_limit_entry, "{:.0f} W", gpu_status.power.limit)
            self._set_entry_text(self._power_default_entry, "{:.0f} W", gpu_status.power.default)
            self._set_entry_text(self._power_enforced_entry, "{:.0f} W", gpu_status.power.enforced)
            self._set_entry_text(self._clocks_graphics_current_entry, "{} MHz", gpu_status.clocks.graphic_current)
            self._set_entry_text(self._clocks_graphics_max_entry, "{} MHz", gpu_status.clocks.graphic_max)
            self._set_entry_text(self._clocks_sm_current_entry, "{} MHz", gpu_status.clocks.sm_current)
            self._set_entry_text(self._clocks_sm_max_entry, "{} MHz", gpu_status.clocks.sm_max)
            self._set_entry_text(self._clocks_memory_current_entry, "{} MHz", gpu_status.clocks.memory_current)
            self._set_entry_text(self._clocks_memory_max_entry, "{} MHz", gpu_status.clocks.memory_max)
            self._set_entry_text(self._clocks_video_current_entry, "{} MHz", gpu_status.clocks.video_current)
            self._set_entry_text(self._clocks_video_max_entry, "{} MHz", gpu_status.clocks.video_max)
            self._set_level_bar(self._info_gpu_usage_levelbar, gpu_status.info.gpu_usage)
            self._set_level_bar(self._info_memory_usage_levelbar, gpu_status.info.memory_usage)
            self._set_level_bar(self._info_encoder_usage_levelbar, gpu_status.info.encoder_usage)
            self._set_level_bar(self._info_decoder_usage_levelbar, gpu_status.info.decoder_usage)
            if gpu_status.overclock.available:
                self._set_entry_text(self._overclock_gpu_offset_entry, "{} MHz", gpu_status.overclock.gpu_offset)
                self._set_entry_text(self._overclock_mem_offset_entry, "{} MHz", gpu_status.overclock.memory_offset)
            self._set_label_markup(self._temp_gpu_value,
                                   "<span size=\"xx-large\">{}</span> °C", gpu_status.temp.gpu)
            for index, value in enumerate(self._fan_duty):
                if gpu_status.fan.fan_list and index < len(gpu_status.fan.fan_list):
                    self._set_label_markup(value,
                                           "<span size=\"large\">{}</span> %", gpu_status.fan.fan_list[index][0])
                    self._set_label_markup(self._fan_rpm[index],
                                           "<span size=\"large\">{}</span> RPM", gpu_status.fan.fan_list[index][1])
                else:
                    value.set_visible(False)
                    self._fan_rpm[index].set_visible(False)

            if self._app_indicator:
                if self._settings_interactor.get_bool('settings_show_app_indicator'):
                    self._app_indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
                else:
                    self._app_indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
                if self._settings_interactor.get_bool('settings_app_indicator_show_gpu_temp') and gpu_status.temp.gpu:
                    self._app_indicator.set_label(f" {gpu_status.temp.gpu}°C", " XX°C")
                else:
                    self._app_indicator.set_label("", "")

    @staticmethod
    def _set_entry_text(label: Gtk.Entry, text: Optional[str], *args: Any) -> None:
        if text is not None and None not in args:
            label.set_sensitive(True)
            label.set_text(text.format(*args))
        else:
            label.set_sensitive(False)
            label.set_text('')

    @staticmethod
    def _set_label_markup(label: Gtk.Label, markup: Optional[str], *args: Any) -> None:
        if markup is not None and None not in args:
            label.set_sensitive(True)
            label.set_markup(markup.format(*args))
        else:
            label.set_sensitive(False)
            label.set_markup('')

    @staticmethod
    def _remove_level_bar_offsets(levelbar: Gtk.LevelBar) -> None:
        levelbar.remove_offset_value("low")
        levelbar.remove_offset_value("high")
        levelbar.remove_offset_value("full")
        levelbar.remove_offset_value("alert")

    @staticmethod
    def _set_level_bar(levelbar: Gtk.LevelBar, value: Optional[int]) -> None:
        if value is not None:
            levelbar.set_value(value / 100)
            levelbar.set_sensitive(True)
        else:
            levelbar.set_value(0)
            levelbar.set_sensitive(False)

    def refresh_chart(self, profile: Optional[FanProfile] = None, reset: bool = False) -> None:
        if profile is None and reset is None:
            raise ValueError("Both parameters are note!")

        if reset:
            self._plot_chart({})
        else:
            self._plot_chart(get_fan_profile_data(profile))

    def refresh_fan_profile_combobox(self, data: List[Tuple[int, str]], active: Optional[int]) -> None:
        self._fan_liststore.clear()
        for item in data:
            self._fan_liststore.append([item[0], item[1]])
        self._fan_combobox.set_model(self._fan_liststore)
        self._fan_combobox.set_sensitive(len(self._fan_liststore) > 1)
        if active is not None:
            self._fan_combobox.set_active(active)
        else:
            self.refresh_chart(reset=True)

    def set_apply_fan_profile_button_enabled(self, enabled: bool) -> None:
        self._fan_apply_button.set_sensitive(enabled)

    def set_edit_fan_profile_button_enabled(self, enabled: bool) -> None:
        self._fan_edit_button.set_sensitive(enabled)

    def set_apply_overclock_profile_button_enabled(self, enabled: bool) -> None:
        self._overclock_apply_button.set_sensitive(enabled)

    def set_edit_overclock_profile_button_enabled(self, enabled: bool) -> None:
        self._overclock_edit_button.set_sensitive(enabled)

    def refresh_overclock_profile_combobox(self, data: List[Tuple[int, str]], active: Optional[int]) -> None:
        self._overclock_liststore.clear()
        for item in data:
            self._overclock_liststore.append([item[0], item[1]])
        self._overclock_combobox.set_model(self._overclock_liststore)
        self._overclock_combobox.set_sensitive(len(self._overclock_liststore) > 1)
        if active is not None:
            self._overclock_combobox.set_active(active)

    # pylint: disable=attribute-defined-outside-init
    def _init_plot_charts(self, fan_scrolled_window: Gtk.ScrolledWindow) -> None:
        self._fan_figure = Figure(figsize=(8, 6), dpi=72, facecolor='#00000000')
        self._fan_canvas = FigureCanvas(self._fan_figure)  # a Gtk.DrawingArea+
        self._fan_axis = self._fan_figure.add_subplot(111)
        self._fan_growing_line, self._fan_decreasing_line = init_plot_chart(
            fan_scrolled_window,
            self._fan_figure,
            self._fan_canvas,
            self._fan_axis
        )

    def _plot_chart(self, data: Dict[int, int]) -> None:
        sorted_data = OrderedDict(sorted(data.items()))
        temperature_list = list(sorted_data.keys())
        duty_list = list(sorted_data.values())
        hysteresis = self._settings_interactor.get_int('settings_hysteresis')
        self._fan_growing_line.set_xdata(temperature_list)
        self._fan_growing_line.set_ydata(duty_list)
        self._fan_decreasing_line.set_xdata([t - hysteresis for t in temperature_list])
        self._fan_decreasing_line.set_ydata(duty_list)
        self._fan_canvas.draw()
        self._fan_canvas.flush_events()
