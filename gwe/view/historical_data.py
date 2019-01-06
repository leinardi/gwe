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
import logging
from typing import Dict, Tuple, Any

from gi.repository import Gtk, GLib, Dazzle, Gdk
from gi.repository.GObject import TYPE_DOUBLE
from injector import singleton, inject

from gwe.conf import GRAPH_COLOR_HEX
from gwe.di import HistoricalDataBuilder
from gwe.presenter.historical_data import HistoricalDataViewInterface, HistoricalDataPresenter, MONITORING_INTERVAL, \
    ChartType
from gwe.view.graph_stacked_renderer import GraphStackedRenderer

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
        self._init_widgets()

    def _init_widgets(self) -> None:
        self._dialog: Gtk.Dialog = self._builder.get_object('dialog')
        self._init_plot_charts()

    def set_transient_for(self, window: Gtk.Window) -> None:
        self._dialog.set_transient_for(window)

    # pylint: disable=attribute-defined-outside-init
    def _init_plot_charts(self) -> None:
        self._graph_views: Dict[ChartType, Tuple[Gtk.Label, Gtk.Label, Gtk.Label]] = {}
        self._graph_models: Dict[ChartType, Dazzle.GraphModel] = {}
        for graph_type in ChartType:
            self._graph_container: Gtk.Frame = self._builder.get_object('graph_container_%d' % graph_type.value)
            self._graph_views[graph_type] = (self._builder.get_object('graph_min_value_%d' % graph_type.value),
                                             self._builder.get_object('graph_max_value_%d' % graph_type.value),
                                             self._builder.get_object('graph_max_axis_%d' % graph_type.value))
            graph_views = Dazzle.GraphView()
            graph_model = Dazzle.GraphModel()
            graph_renderer = GraphStackedRenderer()
            graph_views.set_hexpand(True)
            graph_views.props.height_request = 80
            # self._dialog.set_css_name("rg-graph")
            # self._dialog.get_style_context().add_class("line")
            # line_color_normal = self._dialog.get_style_context().get_color(self._dialog.get_style_context().get_state())
            # self._dialog.get_style_context().remove_class("line")
            # self._dialog.get_style_context().add_class("stacked")
            # color_normal = self._dialog.get_style_context().get_color(self._dialog.get_style_context().get_state())
            # self._dialog.get_style_context().remove_class("stacked")
            graph_renderer.line_width = 1.5
            stroke_color = Gdk.RGBA()
            stroke_color.parse(GRAPH_COLOR_HEX)
            stacked_color = Gdk.RGBA()
            stacked_color.parse(GRAPH_COLOR_HEX)
            stacked_color.alpha = 0.5
            graph_renderer.stroke_color_rgba = stroke_color
            graph_renderer.stacked_color_rgba = stacked_color
            graph_model.set_timespan(MONITORING_INTERVAL * 1000 * 1000)
            graph_model.set_max_samples(MONITORING_INTERVAL / 3)
            graph_model.props.value_max = 100.0
            graph_model.props.value_min = 0.0

            column_ram = Dazzle.GraphColumn().new("Col0", TYPE_DOUBLE)
            graph_model.add_column(column_ram)

            graph_views.set_model(graph_model)
            graph_views.add_renderer(graph_renderer)

            self._graph_container.add(graph_views)

            graph_model_iter = graph_model.push(GLib.get_monotonic_time())
            graph_model.iter_set(graph_model_iter, 0, 0.0)

            self._graph_models[graph_type] = graph_model

    def refresh_charts(self, data_dict: Dict[ChartType, Tuple[int, float, str, float, float]]) -> None:
        for graph_type, data_tuple in data_dict.items():
            self._graph_models[graph_type].props.value_max = float(data_tuple[4])
            graph_model_iter = self._graph_models[graph_type].push(GLib.get_monotonic_time())
            self._graph_models[graph_type].iter_set(graph_model_iter, 0, data_tuple[1])
            self._graph_views[graph_type][2].set_text("%.0f %s" % (data_tuple[1], data_tuple[2]))
        # if self._dialog.props.visible:
        #     time1 = time.time()
        #

        #     chart_data = self._charts[chart_type]
        #     chart_data['line'].set_xdata(data_tuple[0])
        #     chart_data['line'].set_ydata(data_tuple[1])
        #     chart_data['axis'].set_ylabel(data_tuple[2])
        #     chart_data['axis'].set_xlim(datetime.utcnow() + timedelta(seconds=-MONITORING_INTERVAL),
        #                                 datetime.utcnow())
        #     data_low = min(data_tuple[1])
        #     data_high = max(data_tuple[1])
        #     high = max(data_tuple[4], data_high)
        #     chart_data['axis'].set_ybound(lower=min(data_tuple[3], int(data_low)) - 10, upper=high + high * 0.1)
        #     chart_data['canvas'].draw()
        #     chart_data['canvas'].flush_events()
        # time2 = time.time()
        # LOG.debug('Refresh chart took {%.3f} ms' % ((time2 - time1) * 1000.0))

    def show(self) -> None:
        self._dialog.show_all()

    def hide(self) -> None:
        self._dialog.hide()

#     @staticmethod
#     def init_plot_chart(scrolled_window: Gtk.ScrolledWindow,
#                         figure: Figure,
#                         canvas: FigureCanvas,
#                         axis: Axes) -> Any:
#         axis.grid(True, linestyle=':')
#         axis.set_facecolor('#00000000')
#         figure.subplots_adjust(bottom=0.2, left=0.08, right=0.97)
#         canvas.set_size_request(600, 100)
#         scrolled_window.add_with_viewport(canvas)
#         # Returns a tuple of line objects, thus the comma
#         lines = axis.plot_date([], [], 'o-', linewidth=1.0, markersize=2, antialiased=True)
#         axis.set_ybound(lower=-10, upper=110)
#         axis.set_xlim(datetime.utcnow() + timedelta(seconds=-MONITORING_INTERVAL), datetime.utcnow())
#         # axis.xaxis.set_major_locator(DayLocator())
#         # axis.xaxis.set_minor_locator(HourLocator(arange(0, 25, 6)))
#         axis.xaxis.set_major_formatter(MyFormatter())
#
#         # axis.fmt_xdata = DateFormatter('%Y-%m-%d %H:%M:%S')
#         # figure.autofmt_xdate()
#         figure.canvas.draw()
#         return lines
#
#
# class MyFormatter(Formatter):
#     def __call__(self, x, pos=0):
#         date = num2date(x)
#         return timeago.format(date, datetime.now(timezone.utc)).replace('utes ago', '')
