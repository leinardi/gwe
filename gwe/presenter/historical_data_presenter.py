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
from enum import Enum
from typing import Any, Tuple, Dict

from gi.repository import Gtk, GLib
from injector import singleton, inject

from gwe.interactor import SettingsInteractor
from gwe.model.status import Status
from gwe.util.view import hide_on_delete, is_dazzle_version_supported

LOG = logging.getLogger(__name__)

MONITORING_INTERVAL = 300


class GraphType(Enum):
    GPU_CLOCK = 1
    MEMORY_CLOCK = 2
    GPU_TEMP = 3
    FAN_DUTY = 4
    FAN_RPM = 5
    GPU_LOAD = 6
    MEMORY_LOAD = 7
    MEMORY_USAGE = 8
    POWER_DRAW = 9


class HistoricalDataViewInterface:
    def show(self) -> None:
        raise NotImplementedError()

    def hide(self) -> None:
        raise NotImplementedError()

    def reset_graphs(self) -> None:
        raise NotImplementedError()

    def refresh_graphs(self, data: Dict[GraphType, Tuple[int, float, str, float, float]]) -> None:
        raise NotImplementedError()


@singleton
class HistoricalDataPresenter:
    @inject
    def __init__(self,
                 settings_interactor: SettingsInteractor,
                 ) -> None:
        LOG.debug("init HistoricalDataPresenter ")
        self._settings_interactor = settings_interactor
        self.view: HistoricalDataViewInterface = HistoricalDataViewInterface()
        self._gpu_index: int = 0

    def add_status(self, new_status: Status, gpu_index: int) -> None:
        if is_dazzle_version_supported():
            if self._gpu_index != gpu_index:
                self._gpu_index = gpu_index
                self.view.reset_graphs()

            data: Dict[GraphType, Tuple[int, float, str, float, float]] = {}
            time = GLib.get_monotonic_time()
            gpu_status = new_status.gpu_status_list[gpu_index]
            gpu_clock = gpu_status.clocks.graphic_current
            if gpu_clock is not None:
                data[GraphType.GPU_CLOCK] = (time, float(gpu_clock), 'MHz', 0.0, 2000.0)
            mem_clock = gpu_status.clocks.memory_current
            if mem_clock is not None:
                data[GraphType.MEMORY_CLOCK] = (time, float(mem_clock), 'MHz', 0.0, 7000.0)
            gpu_temp = gpu_status.temp.gpu
            if gpu_temp is not None:
                data[GraphType.GPU_TEMP] = (time, float(gpu_temp), '°C', 0.0, 100.0)
            if gpu_status.fan.fan_list:
                fan_duty = gpu_status.fan.fan_list[0][0]
                data[GraphType.FAN_DUTY] = (time, float(fan_duty), '%', 0.0, 100.0)
                fan_rpm = gpu_status.fan.fan_list[0][1]
                data[GraphType.FAN_RPM] = (time, float(fan_rpm), 'rpm', 0.0, 2200.0)
            gpu_load = gpu_status.info.gpu_usage
            if gpu_load is not None:
                data[GraphType.GPU_LOAD] = (time, float(gpu_load), '%', 0.0, 100.0)
            mem_load = gpu_status.info.memory_usage
            if mem_load is not None:
                data[GraphType.MEMORY_LOAD] = (time, float(mem_load), '%', 0.0, 100.0)
            mem_usage = gpu_status.info.memory_used
            if mem_usage is not None:
                data[GraphType.MEMORY_USAGE] = (time, float(mem_usage), 'MiB', 0.0, float(gpu_status.info.memory_total))
            power_draw = gpu_status.power.draw
            maximum = gpu_status.power.maximum
            if power_draw is not None:
                data[GraphType.POWER_DRAW] = (time, power_draw, 'W', 0.0, 400 if maximum is None else maximum)
            self.view.refresh_graphs(data)

    def show(self) -> None:
        self.view.show()

    @staticmethod
    def on_dialog_delete_event(widget: Gtk.Widget, *_: Any) -> Any:
        return hide_on_delete(widget)

    def get_refresh_interval(self) -> int:
        return self._settings_interactor.get_int('settings_refresh_interval')
