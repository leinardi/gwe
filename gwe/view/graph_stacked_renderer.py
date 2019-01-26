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
#
# Code based on GNOME Usage from Petr Štětka
#

import cairo
from gi.overrides.GObject import TYPE_DOUBLE, TYPE_UINT, TYPE_UINT64, TYPE_INT, TYPE_INT64

from gi.repository import Dazzle, GObject, Gdk


class GraphStackedRenderer(GObject.Object, Dazzle.GraphRenderer):

    def __init__(self) -> None:
        GObject.Object.__init__(self)
        self._column = 0
        self._line_width = 1.0
        self._stroke_color_rgba: Gdk.RGBA = Gdk.RGBA(0.5, 0.5, 0.5, 1)
        self._stacked_color_rgba: Gdk.RGBA = Gdk.RGBA(0.5, 0.5, 0.5, 0.5)

    def set_stroke_color_rgba(self, color: Gdk.RGBA) -> None:
        self._stroke_color_rgba = color

    def set_stacked_color_rgba(self, color: Gdk.RGBA) -> None:
        self._stacked_color_rgba = color

    def set_line_width(self, width: float) -> None:
        self._line_width = width

    def do_render(self,
                  model: Dazzle.GraphModel,
                  x_begin: int,
                  x_end: int,
                  y_begin: float,
                  y_end: float,
                  cr: cairo.Context,
                  area: cairo.RectangleInt) -> None:
        model_iter = Dazzle.GraphModelIter()
        cr.save()

        if model.get_iter_first(model_iter):
            chunk = area.width / (model.props.max_samples - 1) / 2.0
            last_x = self._calc_x(model_iter, x_begin, x_end, area.width)
            last_y = area.height

            cr.move_to(last_x, area.height)

            while Dazzle.GraphModel.iter_next(model_iter):
                x = self._calc_x(model_iter, x_begin, x_end, area.width)
                y = self._calc_y(model_iter, y_begin, y_end, area.height, self._column)

                cr.curve_to(last_x + chunk, last_y, last_x + chunk, y, x, y)

                last_x = x
                last_y = y

        cr.set_line_width(self._line_width)
        cr.set_source_rgba(self._stacked_color_rgba.red,
                           self._stacked_color_rgba.green,
                           self._stacked_color_rgba.blue,
                           self._stacked_color_rgba.alpha)
        cr.rel_line_to(0, area.height)
        cr.stroke_preserve()
        cr.close_path()
        cr.fill()

        if model.get_iter_first(model_iter):
            chunk = area.width / (model.props.max_samples - 1) / 2.0
            last_x = self._calc_x(model_iter, x_begin, x_end, area.width)
            last_y = area.height

            cr.move_to(last_x, last_y)

            while Dazzle.GraphModel.iter_next(model_iter):
                x = self._calc_x(model_iter, x_begin, x_end, area.width)
                y = self._calc_y(model_iter, y_begin, y_end, area.height, self._column)

                cr.curve_to(last_x + chunk, last_y, last_x + chunk, y, x, y)

                last_x = x
                last_y = y

        cr.set_source_rgba(self._stroke_color_rgba.red,
                           self._stroke_color_rgba.green,
                           self._stroke_color_rgba.blue,
                           self._stacked_color_rgba.alpha)
        cr.stroke()
        cr.restore()

    @staticmethod
    def _calc_x(model_iter: Dazzle.GraphModelIter, begin: float, end: int, width: int) -> float:
        timestamp: int = Dazzle.GraphModel.iter_get_timestamp(model_iter)
        return (timestamp - begin) / (end - begin) * width

    @staticmethod
    def _calc_y(model_iter: Dazzle.GraphModelIter,
                range_begin: float,
                range_end: float,
                height: int,
                column: int) -> float:
        y = 0.0
        val = GObject.Value()
        Dazzle.GraphModel.iter_get_value(model_iter, column, val)

        if val.g_type == TYPE_DOUBLE:
            y = val.get_double()
        elif val.g_type == TYPE_UINT:
            y = val.get_double()
        elif val.g_type == TYPE_UINT64:
            y = val.get_double()
        elif val.g_type == TYPE_INT:
            y = val.get_double()
        elif val.g_type == TYPE_INT64:
            y = val.get_double()

        y -= range_begin
        y /= (range_end - range_begin)
        y = height - (y * height)

        return y
