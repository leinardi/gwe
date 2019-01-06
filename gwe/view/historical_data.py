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
import time
from _datetime import datetime, timedelta, timezone
import logging
from typing import Dict, Tuple, List, Any, Optional

import timeago
from gi.repository import Gtk
from injector import singleton, inject
from matplotlib.axes import Axes
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
from matplotlib.dates import DayLocator, HourLocator, DateFormatter, num2date
from matplotlib.figure import Figure
from matplotlib.ticker import Formatter
from gwe.di import HistoricalDataBuilder
from gwe.presenter.historical_data import HistoricalDataViewInterface, HistoricalDataPresenter, MONITORING_INTERVAL, \
    ChartType

LOG = logging.getLogger(__name__)


@singleton
class HistoricalDataView(HistoricalDataViewInterface):
    @inject
    def __init__(self,
                 presenter: HistoricalDataPresenter,
                 builder: HistoricalDataBuilder,
                 ) -> None:
        LOG.debug('init HistoricalDataView')
        self._presenter: HistoricalDataPresenter = presenter
        self._presenter.view = self
        self._builder: Gtk.Builder = builder
        self._builder.connect_signals(self._presenter)
        self._charts: Dict[ChartType, Dict[str, Any]] = {}
        self._latest_data_dict: Optional[Dict[ChartType, Tuple[List[datetime], List[float], str, int, int]]] = None
        self._init_widgets()

    def _init_widgets(self) -> None:
        self._dialog: Gtk.Dialog = self._builder.get_object('dialog')
        self._init_plot_charts()

    def set_transient_for(self, window: Gtk.Window) -> None:
        self._dialog.set_transient_for(window)

    # pylint: disable=attribute-defined-outside-init
    def _init_plot_charts(self) -> None:
        gpu_clock_chart: Dict[str, Any] = {'figure': Figure(dpi=72, facecolor='#00000000')}
        gpu_clock_chart['canvas'] = FigureCanvas(gpu_clock_chart['figure'])  # a Gtk.DrawingArea+
        gpu_clock_chart['axis'] = gpu_clock_chart['figure'].add_subplot(1, 1, 1)
        gpu_clock_chart['line'] = self.init_plot_chart(
            self._builder.get_object('gpu_clock_scrolled_window'),
            gpu_clock_chart['figure'],
            gpu_clock_chart['canvas'],
            gpu_clock_chart['axis']
        )[0]
        self._charts[ChartType.GPU_CLOCK] = gpu_clock_chart

        mem_clock_chart: Dict[str, Any] = {'figure': Figure(dpi=72, facecolor='#00000000')}
        mem_clock_chart['canvas'] = FigureCanvas(mem_clock_chart['figure'])  # a Gtk.DrawingArea+
        mem_clock_chart['axis'] = mem_clock_chart['figure'].add_subplot(1, 1, 1)
        mem_clock_chart['line'] = self.init_plot_chart(
            self._builder.get_object('memory_clock_scrolled_window'),
            mem_clock_chart['figure'],
            mem_clock_chart['canvas'],
            mem_clock_chart['axis']
        )[0]
        self._charts[ChartType.MEMORY_CLOCK] = mem_clock_chart

        gpu_temp_chart: Dict[str, Any] = {'figure': Figure(dpi=72, facecolor='#00000000')}
        gpu_temp_chart['canvas'] = FigureCanvas(gpu_temp_chart['figure'])  # a Gtk.DrawingArea+
        gpu_temp_chart['axis'] = gpu_temp_chart['figure'].add_subplot(1, 1, 1)
        gpu_temp_chart['line'] = self.init_plot_chart(
            self._builder.get_object('gpu_temp_scrolled_window'),
            gpu_temp_chart['figure'],
            gpu_temp_chart['canvas'],
            gpu_temp_chart['axis']
        )[0]
        self._charts[ChartType.GPU_TEMP] = gpu_temp_chart

        fan_duty_chart: Dict[str, Any] = {'figure': Figure(dpi=72, facecolor='#00000000')}
        fan_duty_chart['canvas'] = FigureCanvas(fan_duty_chart['figure'])  # a Gtk.DrawingArea+
        fan_duty_chart['axis'] = fan_duty_chart['figure'].add_subplot(1, 1, 1)
        fan_duty_chart['line'] = self.init_plot_chart(
            self._builder.get_object('fan_duty_scrolled_window'),
            fan_duty_chart['figure'],
            fan_duty_chart['canvas'],
            fan_duty_chart['axis']
        )[0]
        self._charts[ChartType.FAN_DUTY] = fan_duty_chart

        fan_rpm_chart: Dict[str, Any] = {'figure': Figure(dpi=72, facecolor='#00000000')}
        fan_rpm_chart['canvas'] = FigureCanvas(fan_rpm_chart['figure'])  # a Gtk.DrawingArea+
        fan_rpm_chart['axis'] = fan_rpm_chart['figure'].add_subplot(1, 1, 1)
        fan_rpm_chart['line'] = self.init_plot_chart(
            self._builder.get_object('fan_rpm_scrolled_window'),
            fan_rpm_chart['figure'],
            fan_rpm_chart['canvas'],
            fan_rpm_chart['axis']
        )[0]
        self._charts[ChartType.FAN_RPM] = fan_rpm_chart

        gpu_load_chart: Dict[str, Any] = {'figure': Figure(dpi=72, facecolor='#00000000')}
        gpu_load_chart['canvas'] = FigureCanvas(gpu_load_chart['figure'])  # a Gtk.DrawingArea+
        gpu_load_chart['axis'] = gpu_load_chart['figure'].add_subplot(1, 1, 1)
        gpu_load_chart['line'] = self.init_plot_chart(
            self._builder.get_object('gpu_load_scrolled_window'),
            gpu_load_chart['figure'],
            gpu_load_chart['canvas'],
            gpu_load_chart['axis']
        )[0]
        self._charts[ChartType.GPU_LOAD] = gpu_load_chart

        mem_load_chart: Dict[str, Any] = {'figure': Figure(dpi=72, facecolor='#00000000')}
        mem_load_chart['canvas'] = FigureCanvas(mem_load_chart['figure'])  # a Gtk.DrawingArea+
        mem_load_chart['axis'] = mem_load_chart['figure'].add_subplot(1, 1, 1)
        mem_load_chart['line'] = self.init_plot_chart(
            self._builder.get_object('memory_load_scrolled_window'),
            mem_load_chart['figure'],
            mem_load_chart['canvas'],
            mem_load_chart['axis']
        )[0]
        self._charts[ChartType.MEMORY_LOAD] = mem_load_chart

        mem_usage_chart: Dict[str, Any] = {'figure': Figure(dpi=72, facecolor='#00000000')}
        mem_usage_chart['canvas'] = FigureCanvas(mem_usage_chart['figure'])  # a Gtk.DrawingArea+
        mem_usage_chart['axis'] = mem_usage_chart['figure'].add_subplot(1, 1, 1)
        mem_usage_chart['line'] = self.init_plot_chart(
            self._builder.get_object('memory_usage_scrolled_window'),
            mem_usage_chart['figure'],
            mem_usage_chart['canvas'],
            mem_usage_chart['axis']
        )[0]
        self._charts[ChartType.MEMORY_USAGE] = mem_usage_chart

        power_draw_chart: Dict[str, Any] = {'figure': Figure(dpi=72, facecolor='#00000000')}
        power_draw_chart['canvas'] = FigureCanvas(power_draw_chart['figure'])  # a Gtk.DrawingArea+
        power_draw_chart['axis'] = power_draw_chart['figure'].add_subplot(1, 1, 1)
        power_draw_chart['line'] = self.init_plot_chart(
            self._builder.get_object('power_draw_scrolled_window'),
            power_draw_chart['figure'],
            power_draw_chart['canvas'],
            power_draw_chart['axis']
        )[0]
        self._charts[ChartType.POWER_DRAW] = power_draw_chart

    def refresh_charts(self, data_dict: Dict[ChartType, Tuple[List[datetime], List[float], str, int, int]]) -> None:
        self._latest_data_dict = data_dict
        if self._dialog.props.visible:
            time1 = time.time()
            for chart_type, data_tuple in data_dict.items():
                chart_data = self._charts[chart_type]
                chart_data['line'].set_xdata(data_tuple[0])
                chart_data['line'].set_ydata(data_tuple[1])
                chart_data['axis'].set_ylabel(data_tuple[2])
                chart_data['axis'].set_xlim(datetime.utcnow() + timedelta(seconds=-MONITORING_INTERVAL),
                                            datetime.utcnow())
                data_low = min(data_tuple[1])
                data_high = max(data_tuple[1])
                high = max(data_tuple[4], data_high)
                chart_data['axis'].set_ybound(lower=min(data_tuple[3], int(data_low)) - 10, upper=high + high * 0.1)
                chart_data['canvas'].draw()
                chart_data['canvas'].flush_events()
            time2 = time.time()
            LOG.debug('Refresh chart took {%.3f} ms' % ((time2 - time1) * 1000.0))

    def show(self) -> None:
        self._dialog.show_all()
        if self._latest_data_dict:
            self.refresh_charts(self._latest_data_dict)

    def hide(self) -> None:
        self._dialog.hide()

    @staticmethod
    def init_plot_chart(scrolled_window: Gtk.ScrolledWindow,
                        figure: Figure,
                        canvas: FigureCanvas,
                        axis: Axes) -> Any:
        axis.grid(True, linestyle=':')
        axis.set_facecolor('#00000000')
        figure.subplots_adjust(bottom=0.2, left=0.08, right=0.97)
        canvas.set_size_request(600, 100)
        scrolled_window.add_with_viewport(canvas)
        # Returns a tuple of line objects, thus the comma
        lines = axis.plot_date([], [], 'o-', linewidth=1.0, markersize=2, antialiased=True)
        axis.set_ybound(lower=-10, upper=110)
        axis.set_xlim(datetime.utcnow() + timedelta(seconds=-MONITORING_INTERVAL), datetime.utcnow())
        # axis.xaxis.set_major_locator(DayLocator())
        # axis.xaxis.set_minor_locator(HourLocator(arange(0, 25, 6)))
        axis.xaxis.set_major_formatter(MyFormatter())

        # axis.fmt_xdata = DateFormatter('%Y-%m-%d %H:%M:%S')
        # figure.autofmt_xdate()
        figure.canvas.draw()
        return lines


class MyFormatter(Formatter):
    def __call__(self, x, pos=0):
        date = num2date(x)
        return timeago.format(date, datetime.now(timezone.utc)).replace('utes ago', '')
