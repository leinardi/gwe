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
import _datetime
import logging
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, List, Tuple, Dict

from gi.repository import Gtk
from injector import singleton, inject

from gwe.model import Status, GpuStatus
from gwe.repository import NOT_AVAILABLE_STRING
from gwe.util.view import hide_on_delete

LOG = logging.getLogger(__name__)

MONITORING_INTERVAL = 300


class ChartType(Enum):
    GPU_CLOCK = auto()
    MEMORY_CLOCK = auto()
    GPU_TEMP = auto()
    FAN_DUTY = auto()
    FAN_RPM = auto()
    GPU_LOAD = auto()
    MEMORY_LOAD = auto()
    MEMORY_USAGE = auto()
    POWER_DRAW = auto()


class HistoricalDataViewInterface:
    def show(self) -> None:
        raise NotImplementedError()

    def hide(self) -> None:
        raise NotImplementedError()

    def refresh_charts(self, data: Dict[ChartType, Tuple[List[datetime], List[float], str, int, int]]) -> None:
        raise NotImplementedError()


@singleton
class HistoricalDataPresenter:
    @inject
    def __init__(self) -> None:
        LOG.debug("init HistoricalDataPresenter ")
        self.view: HistoricalDataViewInterface = HistoricalDataViewInterface()
        self._data: List[Tuple[datetime, Status]] = []

    def add_status(self, new_status: Status) -> None:
        if self._data:
            if self._data[0][0] < datetime.utcnow() + timedelta(seconds=-MONITORING_INTERVAL):
                self._data.pop(0)
        self._data.append((datetime.utcnow(), new_status))
        gpu_index = 0
        temp_data: Dict[ChartType, Tuple[List[datetime], List[float], str, int, int]] = {
            ChartType.GPU_CLOCK: ([], [], 'MHz', 0, 2000),
            ChartType.MEMORY_CLOCK: ([], [], 'MHz', 0, 7000),
            ChartType.GPU_TEMP: ([], [], '°C', 0, 100),
            ChartType.FAN_DUTY: ([], [], '%', 0, 100),
            ChartType.FAN_RPM: ([], [], 'rpm', 0, 2200),
            ChartType.GPU_LOAD: ([], [], '%', 0, 100),
            ChartType.MEMORY_LOAD: ([], [], '%', 0, 100),
            ChartType.MEMORY_USAGE: ([], [], '%', 0, 100),
            ChartType.POWER_DRAW: ([], [], 'W', 0, 400)}
        for date, status in self._data:
            self._get_gpu_clock_data(date, status.gpu_status_list[gpu_index], temp_data[ChartType.GPU_CLOCK])
            self._get_mem_clock_data(date, status.gpu_status_list[gpu_index], temp_data[ChartType.MEMORY_CLOCK])
            self._get_gpu_temp_data(date, status.gpu_status_list[gpu_index], temp_data[ChartType.GPU_TEMP])
            self._get_fan_duty_data(date, status.gpu_status_list[gpu_index], temp_data[ChartType.FAN_DUTY])
            self._get_fan_rpm_data(date, status.gpu_status_list[gpu_index], temp_data[ChartType.FAN_RPM])
            self._get_gpu_load_data(date, status.gpu_status_list[gpu_index], temp_data[ChartType.GPU_LOAD])
            self._get_mem_load_data(date, status.gpu_status_list[gpu_index], temp_data[ChartType.MEMORY_LOAD])
            # self._get_mem_usage_data(date, status.gpu_status_list[gpu_index], temp_data[ChartType.MEMORY_USAGE])
            self._get_power_draw_data(date, status.gpu_status_list[gpu_index], temp_data[ChartType.POWER_DRAW])

        gpu_data: Dict[ChartType, Tuple[List[datetime], List[float], str, int, int]] = {}
        for chart_type, data_tuple in temp_data.items():
            if data_tuple[0]:
                gpu_data[chart_type] = data_tuple
        self.view.refresh_charts(gpu_data)

    @staticmethod
    def _get_gpu_clock_data(date: _datetime,
                            gpu_status: GpuStatus,
                            gpu_clock_data: Tuple[List[datetime], List[float], str, int, int]) -> None:
        if NOT_AVAILABLE_STRING not in gpu_status.clocks.graphic_current:
            try:
                clock = int(gpu_status.clocks.graphic_current.rstrip(' MHz'))
                gpu_clock_data[0].append(date)
                gpu_clock_data[1].append(clock)
            except ValueError:
                LOG.exception('Unable to parse clock %s', gpu_status.temp.gpu)

    @staticmethod
    def _get_mem_clock_data(date: _datetime,
                            gpu_status: GpuStatus,
                            mem_clock_data: Tuple[List[datetime], List[float], str, int, int]) -> None:
        if NOT_AVAILABLE_STRING not in gpu_status.clocks.graphic_current:
            try:
                clock = int(gpu_status.clocks.memory_current.rstrip(' MHz'))
                mem_clock_data[0].append(date)
                mem_clock_data[1].append(clock)
            except ValueError:
                LOG.exception('Unable to parse clock %s', gpu_status.temp.mem)

    @staticmethod
    def _get_gpu_temp_data(date: _datetime,
                           gpu_status: GpuStatus,
                           gpu_temp_data: Tuple[List[datetime], List[float], str, int, int]) -> None:
        if NOT_AVAILABLE_STRING not in gpu_status.temp.gpu:
            try:
                temperature = int(gpu_status.temp.gpu.rstrip(' C'))
                gpu_temp_data[0].append(date)
                gpu_temp_data[1].append(temperature)
            except ValueError:
                LOG.exception('Unable to parse temperature %s', gpu_status.temp.gpu)

    @staticmethod
    def _get_fan_duty_data(date: _datetime,
                           gpu_status: GpuStatus,
                           fan_duty_data: Tuple[List[datetime], List[float], str, int, int]) -> None:
        if NOT_AVAILABLE_STRING not in gpu_status.fan.fan_list:
            try:
                duty = int(gpu_status.fan.fan_list[0][0])
                fan_duty_data[0].append(date)
                fan_duty_data[1].append(duty)
            except ValueError:
                LOG.exception('Unable to parse fan duty %s', gpu_status.temp.gpu)

    @staticmethod
    def _get_fan_rpm_data(date: _datetime,
                          gpu_status: GpuStatus,
                          fan_rpm_data: Tuple[List[datetime], List[float], str, int, int]) -> None:
        if NOT_AVAILABLE_STRING not in gpu_status.fan.fan_list:
            try:
                rpm = int(gpu_status.fan.fan_list[0][1])
                fan_rpm_data[0].append(date)
                fan_rpm_data[1].append(rpm)
            except ValueError:
                LOG.exception('Unable to parse fan rpm %s', gpu_status.temp.gpu)

    @staticmethod
    def _get_gpu_load_data(date: _datetime,
                           gpu_status: GpuStatus,
                           gpu_load_data: Tuple[List[datetime], List[float], str, int, int]) -> None:
        if NOT_AVAILABLE_STRING not in gpu_status.info.gpu_usage:
            try:
                load = int(gpu_status.info.gpu_usage.rstrip(' %'))
                gpu_load_data[0].append(date)
                gpu_load_data[1].append(load)
            except ValueError:
                LOG.exception('Unable to parse load %s', gpu_status.temp.gpu)

    @staticmethod
    def _get_mem_load_data(date: _datetime,
                           gpu_status: GpuStatus,
                           mem_load_data: Tuple[List[datetime], List[float], str, int, int]) -> None:
        if NOT_AVAILABLE_STRING not in gpu_status.info.memory_usage:
            try:
                load = int(gpu_status.info.memory_usage.rstrip(' %'))
                mem_load_data[0].append(date)
                mem_load_data[1].append(load)
            except ValueError:
                LOG.exception('Unable to parse load %s', gpu_status.temp.mem)

    @staticmethod
    def _get_mem_usage_data(date: _datetime,
                            gpu_status: GpuStatus,
                            mem_usage_data: Tuple[List[datetime], List[float], str, int, int]) -> None:
        if NOT_AVAILABLE_STRING not in gpu_status.info.memory_usage:
            try:
                usage = int(gpu_status.info.memory_usage.rstrip(' %'))
                mem_usage_data[0].append(date)
                mem_usage_data[1].append(usage)
            except ValueError:
                LOG.exception('Unable to parse usage %s', gpu_status.temp.mem)

    @staticmethod
    def _get_power_draw_data(date: _datetime,
                             gpu_status: GpuStatus,
                             power_draw_data: Tuple[List[datetime], List[float], str, int, int]) -> None:
        if NOT_AVAILABLE_STRING not in gpu_status.power.draw:
            try:
                load = float(gpu_status.power.draw.rstrip(' W'))
                power_draw_data[0].append(date)
                power_draw_data[1].append(load)
            except ValueError:
                LOG.exception('Unable to parse load %s', gpu_status.temp.gpu)

    def show(self) -> None:
        self.view.show()

    def on_dialog_delete_event(self, widget: Gtk.Widget, *_: Any) -> Any:
        return hide_on_delete(widget)
