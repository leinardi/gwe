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
from typing import Optional, Dict, Any, List, Tuple

from gwe.di import MainBuilder
from gwe.repository import NOT_AVAILABLE_STRING
from gwe.view.edit_speed_profile import EditSpeedProfileView
from gwe.util.path import get_data_path
from gwe.util.view import hide_on_delete, init_plot_chart, get_speed_profile_data
from injector import inject, singleton
import gi
from gi.repository import Gtk
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas

# AppIndicator3 may not be installed
from gwe.interactor import SettingsInteractor
from gwe.view.preferences import PreferencesView

try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3
except (ImportError, ValueError):
    AppIndicator3 = None

from gwe.conf import APP_PACKAGE_NAME, APP_ID, FAN_MIN_DUTY, FAN_MAX_DUTY, APP_NAME, \
    APP_VERSION, APP_SOURCE_URL
from gwe.model import Status, SpeedProfile
from gwe.presenter.main import MainPresenter, MainViewInterface

LOG = logging.getLogger(__name__)
if AppIndicator3 is None:
    LOG.warning("AppIndicator3 is not installed. The app indicator will not be shown.")


@singleton
class MainView(MainViewInterface):

    @inject
    def __init__(self,
                 presenter: MainPresenter,
                 edit_speed_profile_view: EditSpeedProfileView,
                 preferences_view: PreferencesView,
                 builder: MainBuilder,
                 settings_interactor: SettingsInteractor,
                 ) -> None:
        LOG.debug('init MainView')
        self._presenter: MainPresenter = presenter
        self._edit_speed_profile_view = edit_speed_profile_view
        self._preferences_view = preferences_view
        self._presenter.main_view = self
        self._builder: Gtk.Builder = builder
        self._settings_interactor = settings_interactor
        self._first_refresh = True
        self._init_widgets()
        self._latest_status: Optional[Status] = None

    def _init_widgets(self) -> None:
        self._app_indicator: Optional[AppIndicator3.Indicator] = None
        self._window = self._builder.get_object("application_window")
        # self._edit_speed_profile_view.set_transient_for(self._window)
        self._preferences_view.set_transient_for(self._window)
        self._main_menu: Gtk.Menu = self._builder.get_object("main_menu")
        self._main_infobar: Gtk.InfoBar = self._builder.get_object("main_infobar")
        self._main_infobar.connect("response", lambda b, _: b.set_revealed(False))
        self._main_infobar_label: Gtk.Label = self._builder.get_object("main_infobar_label")
        self._main_infobar.set_revealed(False)
        self._statusbar: Gtk.Statusbar = self._builder.get_object('statusbar')
        self._context = self._statusbar.get_context_id(APP_PACKAGE_NAME)
        self._app_version: Gtk.Label = self._builder.get_object('app_version')
        self._app_version.set_label("%s %s" % (APP_NAME, APP_VERSION))
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
        self._info_memory_usage_levelbar: Gtk.LevelBar = self._builder.get_object('info_memory_usage_levelbar')
        self._info_gpu_usage_levelbar: Gtk.LevelBar = self._builder.get_object('info_gpu_usage_levelbar')
        self._info_encoder_usage_levelbar: Gtk.LevelBar = self._builder.get_object('info_encoder_usage_levelbar')
        self._info_decoder_usage_levelbar: Gtk.LevelBar = self._builder.get_object('info_decoder_usage_levelbar')
        self._temp_gpu_value: Gtk.Label = self._builder.get_object('temp_gpu_value')
        self._temp_max_gpu_value: Gtk.Label = self._builder.get_object('temp_max_gpu_value')
        self._temp_slowdown_value: Gtk.Label = self._builder.get_object('temp_slowdown_value')
        self._temp_shutdown_value: Gtk.Label = self._builder.get_object('temp_shutdown_value')
        self._fan_duty: Tuple[Gtk.Label] = (
            self._builder.get_object('fan_duty_0'),
            self._builder.get_object('fan_duty_1'),
            self._builder.get_object('fan_duty_2'),
            self._builder.get_object('fan_duty_3'),
            self._builder.get_object('fan_duty_4')
        )
        self._fan_rpm: Tuple[Gtk.Label] = (
            self._builder.get_object('fan_rpm_0'),
            self._builder.get_object('fan_rpm_1'),
            self._builder.get_object('fan_rpm_2'),
            self._builder.get_object('fan_rpm_3'),
            self._builder.get_object('fan_rpm_4')
        )
        self._overclock_frame: Gtk.Frame = self._builder.get_object('overclock_frame')
        self._overclock_gpu_offset_scale: Gtk.Scale = self._builder.get_object('overclock_gpu_offset_scale')
        self._overclock_memory_offset_scale: Gtk.Scale = self._builder.get_object('overclock_memory_offset_scale')
        self._overclock_gpu_offset_adjustment: Gtk.Adjustment = self._builder.get_object(
            'overclock_gpu_offset_adjustment')
        self._overclock_memory_offset_adjustment: Gtk.Adjustment = self._builder.get_object(
            'overclock_memory_offset_adjustment')

        # self._cooling_fan_duty: Gtk.Label = self._builder.get_object('cooling_fan_duty')
        # self._cooling_fan_rpm: Gtk.Label = self._builder.get_object('cooling_fan_rpm')
        # self._cooling_liquid_temp: Gtk.Label = self._builder.get_object('cooling_liquid_temp')
        # self._cooling_pump_rpm: Gtk.Label = self._builder.get_object('cooling_pump_rpm')
        # self._cooling_fan_combobox: Gtk.ComboBox = self._builder.get_object('cooling_fan_profile_combobox')
        # self._cooling_fan_liststore: Gtk.ListStore = self._builder.get_object('cooling_fan_profile_liststore')
        # self._cooling_pump_combobox: Gtk.ComboBox = self._builder.get_object('cooling_pump_profile_combobox')
        # self._cooling_pump_liststore: Gtk.ListStore = self._builder.get_object('cooling_pump_profile_liststore')
        # cooling_fan_scrolled_window: Gtk.ScrolledWindow = self._builder.get_object('cooling_fan_scrolled_window')
        # cooling_pump_scrolled_window: Gtk.ScrolledWindow = self._builder.get_object('cooling_pump_scrolled_window')
        # self._cooling_fan_edit_button: Gtk.Button = self._builder.get_object('cooling_fan_edit_button')
        # self._cooling_pump_edit_button: Gtk.Button = self._builder.get_object('cooling_pump_edit_button')
        # self._cooling_fixed_speed_popover: Gtk.Popover = self._builder.get_object('cooling_fixed_speed_popover')
        # self._cooling_fixed_speed_adjustment: Gtk.Adjustment = \
        #     self._builder.get_object('cooling_fixed_speed_adjustment')
        # self._cooling_fixed_speed_scale: Gtk.Scale = self._builder.get_object('cooling_fixed_speed_scale')
        # self._init_plot_charts(cooling_fan_scrolled_window, cooling_pump_scrolled_window)

    def _init_about_dialog(self) -> None:
        self._about_dialog.set_program_name(APP_NAME)
        self._about_dialog.set_version(APP_VERSION)
        self._about_dialog.set_website(APP_SOURCE_URL)
        self._about_dialog.connect("delete-event", hide_on_delete)

    def show(self) -> None:
        self._presenter.on_start()
        self._init_app_indicator()

    def _init_app_indicator(self) -> None:
        if AppIndicator3:
            self._app_indicator = AppIndicator3.Indicator \
                .new(APP_ID, get_data_path('gwe-symbolic.svg'), AppIndicator3.IndicatorCategory.HARDWARE)
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

    # def show_add_speed_profile_dialog(self, channel: ChannelType) -> None:
    #     LOG.debug("view show_add_speed_profile_dialog %s", channel.name)

    # def show_fixed_speed_profile_popover(self, profile: SpeedProfile) -> None:
    #     if profile.channel == ChannelType.FAN.value:
    #         self._cooling_fixed_speed_popover.set_relative_to(self._cooling_fan_edit_button)
    #         self._cooling_fixed_speed_adjustment.set_lower(FAN_MIN_DUTY)
    #         self._cooling_fixed_speed_adjustment.set_upper(FAN_MAX_DUTY)
    #     else:
    #         raise ValueError("Unknown channel: %s" % profile.channel)
    #     self._cooling_fixed_speed_scale.set_name(profile.channel)
    #     self._cooling_fixed_speed_adjustment.set_value(profile.steps[0].duty)
    #     self._cooling_fixed_speed_popover.show_all()

    def get_overclock_offsets(self) -> Tuple[int, int, int, int]:
        return (
            0,
            self._latest_status.gpu_status_list[0].overclock.perf,
            self._overclock_gpu_offset_adjustment.get_value(),
            self._overclock_memory_offset_adjustment.get_value()
        )

    def dismiss_and_get_value_fixed_speed_popover(self) -> Tuple[int, str]:
        self._cooling_fixed_speed_popover.hide()
        return self._cooling_fixed_speed_scale.get_value(), self._cooling_fixed_speed_scale.get_name()

    def show_about_dialog(self) -> None:
        self._about_dialog.show()

    def set_statusbar_text(self, text: str) -> None:
        self._statusbar.remove_all(self._context)
        self._statusbar.push(self._context, text)

    def refresh_status(self, status: Optional[Status]) -> None:
        LOG.debug('view status')
        if status:
            self._latest_status = status
            gpu_status = status.gpu_status_list[0]
            if self._first_refresh:
                self._first_refresh = False
                self._set_entry_text(self._info_name_entry, gpu_status.info.name)
                self._set_entry_text(self._info_vbios_entry, gpu_status.info.vbios)
                self._set_entry_text(self._info_driver_entry, gpu_status.info.driver)
                self._set_entry_text(self._info_cuda_entry, gpu_status.info.cuda_cores)
                self._set_entry_text(self._info_uuid_entry, gpu_status.info.uuid)
                self._set_entry_text(self._info_memory_interface_entry, gpu_status.info.memory_interface)
                self._set_entry_text(self._power_min_entry, gpu_status.power.minimum)
                self._set_entry_text(self._power_max_entry, gpu_status.power.maximum)
                self._set_label_markup(self._temp_max_gpu_value,
                                       "<span size=\"large\">%s</span> °C" % gpu_status.temp.maximum.rstrip(' C'))
                self._set_label_markup(self._temp_slowdown_value,
                                       "<span size=\"large\">%s</span> °C" % gpu_status.temp.slowdown.rstrip(' C'))
                self._set_label_markup(self._temp_shutdown_value,
                                       "<span size=\"large\">%s</span> °C" % gpu_status.temp.shutdown.rstrip(' C'))
                self._overclock_frame.set_sensitive(gpu_status.overclock.available)
                if gpu_status.overclock.available:
                    self._overclock_gpu_offset_adjustment.set_value(gpu_status.overclock.gpu_offset)
                    self._overclock_memory_offset_adjustment.set_value(gpu_status.overclock.memory_offset)
                    self._overclock_memory_offset_scale.clear_marks()
                    self._overclock_memory_offset_scale.add_mark(0, Gtk.PositionType.BOTTOM, str(0))
                    self._overclock_gpu_offset_scale.clear_marks()
                    self._overclock_gpu_offset_scale.add_mark(0, Gtk.PositionType.BOTTOM, str(0))

            self._set_entry_text(self._info_pcie_entry, gpu_status.info.pcie)
            self._set_entry_text(self._info_memory_entry, gpu_status.info.memory_size)
            self._set_entry_text(self._info_memory_usage_entry, gpu_status.info.memory_usage)
            self._set_entry_text(self._info_gpu_usage_entry, gpu_status.info.gpu_usage)
            self._set_entry_text(self._info_encoder_usage_entry, gpu_status.info.encoder_usage)
            self._set_entry_text(self._info_decoder_usage_entry, gpu_status.info.decoder_usage)
            self._set_entry_text(self._power_draw_entry, gpu_status.power.draw)
            self._set_entry_text(self._power_limit_entry, gpu_status.power.limit)
            self._set_entry_text(self._power_default_entry, gpu_status.power.default)
            self._set_entry_text(self._power_enforced_entry, gpu_status.power.enforced)
            self._set_entry_text(self._clocks_graphics_current_entry, gpu_status.clocks.graphic_current)
            self._set_entry_text(self._clocks_graphics_max_entry, gpu_status.clocks.graphic_max)
            self._set_entry_text(self._clocks_sm_current_entry, gpu_status.clocks.sm_current)
            self._set_entry_text(self._clocks_sm_max_entry, gpu_status.clocks.sm_max)
            self._set_entry_text(self._clocks_memory_current_entry, gpu_status.clocks.memory_current)
            self._set_entry_text(self._clocks_memory_max_entry, gpu_status.clocks.memory_max)
            self._set_entry_text(self._clocks_video_current_entry, gpu_status.clocks.video_current)
            self._set_entry_text(self._clocks_video_max_entry, gpu_status.clocks.video_max)
            self._set_level_bar(self._info_memory_usage_levelbar, gpu_status.info.memory_usage)
            self._set_level_bar(self._info_gpu_usage_levelbar, gpu_status.info.gpu_usage)
            self._set_level_bar(self._info_encoder_usage_levelbar, gpu_status.info.encoder_usage)
            self._set_level_bar(self._info_decoder_usage_levelbar, gpu_status.info.decoder_usage)
            self._set_label_markup(self._temp_gpu_value,
                                   "<span size=\"xx-large\">%s</span> °C" % gpu_status.temp.gpu.rstrip(' C'))
            for index, value in enumerate(self._fan_duty):
                if index < len(gpu_status.fan.fan_list):
                    self._set_label_markup(value,
                                           "<span size=\"large\">%d</span> %%" % gpu_status.fan.fan_list[index][0])
                    self._set_label_markup(self._fan_rpm[index],
                                           "<span size=\"large\">%d</span> RPM" % gpu_status.fan.fan_list[index][1])
                else:
                    value.set_visible(False)
                    self._fan_rpm[index].set_visible(False)
            if gpu_status.overclock.available:
                self._overclock_gpu_offset_adjustment.set_lower(gpu_status.overclock.gpu_range[0])
                self._overclock_gpu_offset_adjustment.set_upper(gpu_status.overclock.gpu_range[1])
                self._overclock_memory_offset_adjustment.set_lower(gpu_status.overclock.memory_range[0])
                self._overclock_memory_offset_adjustment.set_upper(gpu_status.overclock.memory_range[1])

            #     self._cooling_fan_rpm.set_markup("<span size=\"xx-large\">%s</span> RPM" % status.fan_rpm)
            #     self._cooling_fan_duty.set_markup("<span size=\"xx-large\">%s</span> %%" %
            #                                       ('-' if status.fan_duty is None else "%.0f" % status.fan_duty))
            #     self._cooling_liquid_temp.set_markup("<span size=\"xx-large\">%s</span> °C" % status.liquid_temperature)

        #     if self._app_indicator:
        #         if self._settings_interactor.get_bool('settings_show_app_indicator'):
        #             self._app_indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        #         else:
        #             self._app_indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
        #         if self._settings_interactor.get_bool('settings_app_indicator_show_gpu_temp'):
        #             self._app_indicator.set_label("  %s°C" % status.liquid_temperature, "  XX°C")
        #         else:
        #             self._app_indicator.set_label("", "")

    @staticmethod
    def _set_entry_text(label: Gtk.Entry, text: str) -> None:
        if text and text != NOT_AVAILABLE_STRING:
            label.set_sensitive(True)
            label.set_text(text)
        else:
            label.set_sensitive(False)
            label.set_text('')

    @staticmethod
    def _set_label_markup(label: Gtk.Label, markup: str) -> None:
        if markup and NOT_AVAILABLE_STRING not in markup:
            label.set_sensitive(True)
            label.set_markup(markup)
        else:
            label.set_sensitive(False)
            label.set_markup('')

    @staticmethod
    def _set_level_bar(levelbar: Gtk.LevelBar, value: str) -> None:
        value_stripped = value.rstrip(' %')
        if value_stripped.isdigit():
            levelbar.set_value(int(value_stripped))
            levelbar.set_sensitive(True)
        else:
            levelbar.set_value(0)
            levelbar.set_sensitive(False)

    def refresh_chart(self, profile: Optional[SpeedProfile] = None, reset: Optional[str] = None) -> None:
        if profile is None and reset is None:
            raise ValueError("Both parameters are note!")

        if reset is not None:
            self._plot_chart({})
        else:
            self._plot_chart(get_speed_profile_data(profile))

    # def refresh_profile_combobox(self, channel: ChannelType, data: List[Tuple[int, str]],
    #                              active: Optional[int]) -> None:
    #     if channel is ChannelType.FAN:
    #         self._cooling_fan_liststore.clear()
    #         for item in data:
    #             self._cooling_fan_liststore.append([item[0], item[1]])
    #         self._cooling_fan_combobox.set_model(self._cooling_fan_liststore)
    #         self._cooling_fan_combobox.set_sensitive(len(self._cooling_fan_liststore) > 1)
    #         if active is not None:
    #             self._cooling_fan_combobox.set_active(active)
    #         else:
    #             self.refresh_chart(channel_to_reset=channel.value)
    #     else:
    #         raise ValueError("Unknown channel: %s" % channel.name)

    # def set_apply_button_enabled(self, channel: ChannelType, enabled: bool) -> None:
    #     if channel is ChannelType.FAN:
    #         self._cooling_fan_apply_button.set_sensitive(enabled)
    #     else:
    #         raise ValueError("Unknown channel: %s" % channel.name)
    #
    # def set_edit_button_enabled(self, channel: ChannelType, enabled: bool) -> None:
    #     if channel is ChannelType.FAN:
    #         self._cooling_fan_edit_button.set_sensitive(enabled)
    #     else:
    #         raise ValueError("Unknown channel: %s" % channel.name)

    # pylint: disable=attribute-defined-outside-init
    def _init_plot_charts(self,
                          fan_scrolled_window: Gtk.ScrolledWindow,
                          pump_scrolled_window: Gtk.ScrolledWindow) -> None:
        self._fan_figure = Figure(figsize=(8, 6), dpi=72, facecolor='#00000000')
        self._fan_canvas = FigureCanvas(self._fan_figure)  # a Gtk.DrawingArea+
        self._fan_axis = self._fan_figure.add_subplot(111)
        self._fan_line, = init_plot_chart(
            fan_scrolled_window,
            self._fan_figure,
            self._fan_canvas,
            self._fan_axis
        )

        self._pump_figure = Figure(figsize=(8, 6), dpi=72, facecolor='#00000000')
        self._pump_canvas = FigureCanvas(self._pump_figure)  # a Gtk.DrawingArea+
        self._pump_axis = self._pump_figure.add_subplot(111)
        self._pump_line, = init_plot_chart(
            pump_scrolled_window,
            self._pump_figure,
            self._pump_canvas,
            self._pump_axis
        )

    def _plot_chart(self, data: Dict[int, int]) -> None:
        sorted_data = OrderedDict(sorted(data.items()))
        temperature = list(sorted_data.keys())
        duty = list(sorted_data.values())
        self._fan_line.set_xdata(temperature)
        self._fan_line.set_ydata(duty)
        self._fan_canvas.draw()
        self._fan_canvas.flush_events()
