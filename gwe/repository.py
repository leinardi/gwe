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
import subprocess
import threading
import time
from typing import Optional, List, Tuple, Dict, Callable, Any

from injector import singleton, inject
from py3nvml import py3nvml
from py3nvml.py3nvml import NVMLError, NVML_ERROR_NOT_SUPPORTED, NVML_TEMPERATURE_GPU, \
    NVML_TEMPERATURE_THRESHOLD_SLOWDOWN, NVML_TEMPERATURE_THRESHOLD_SHUTDOWN, NVML_CLOCK_SM, NVML_ERROR_UNKNOWN
from Xlib import display
from Xlib.ext.nvcontrol import Gpu, Cooler
from gwe.model import Status, Info, Power, Temp, Clocks, GpuStatus, Fan, Overclock
from gwe.util.concurrency import synchronized_with_attr
from gwe.util.deployment import is_flatpak

LOG = logging.getLogger(__name__)

NOT_AVAILABLE_STRING = 'N/A'
_NVIDIA_SMI_BINARY_NAME = 'nvidia-smi'
_NVIDIA_SETTINGS_BINARY_NAME = 'nvidia-settings'
_FLATPAK_COMMAND_PREFIX = ['flatpak-spawn', '--host']


def run_and_get_stdout(command: List[str], pipe_command: List[str] = None) -> Tuple[int, str, str]:
    if pipe_command is None:
        if is_flatpak():
            command = _FLATPAK_COMMAND_PREFIX + command
        process1 = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        output, error = process1.communicate()
        return process1.returncode, output.decode(encoding='UTF-8').strip(), error.decode(encoding='UTF-8').strip()
    if is_flatpak():
        command = _FLATPAK_COMMAND_PREFIX + command
        pipe_command = _FLATPAK_COMMAND_PREFIX + pipe_command
    process1 = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    process2 = subprocess.Popen(pipe_command, stdin=process1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process1.stdout.close()
    output, error = process1.communicate()
    return process2.returncode, output.decode(encoding='UTF-8').strip(), error.decode(encoding='UTF-8').strip()


@singleton
class NvidiaRepository:
    @inject
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._gpu_count = 0
        self._gpu_setting_cache: List[Dict[str, str]] = []
        self._ctrl_display: Optional[str] = None

    @staticmethod
    def is_nvidia_smi_available() -> bool:
        return run_and_get_stdout(['which', _NVIDIA_SMI_BINARY_NAME])[0] == 0

    def set_ctrl_display(self, ctrl_display: str) -> None:
        self._ctrl_display = ctrl_display

    @synchronized_with_attr("_lock")
    def get_status(self) -> Optional[Status]:
        xlib_display = None
        try:
            time1 = time.time()
            py3nvml.nvmlInit()
            xlib_display = display.Display(self._ctrl_display)
            self._gpu_count = xlib_display.nvcontrol_get_gpu_count()
            gpu_status_list: List[GpuStatus] = []
            for gpu_index in range(self._gpu_count):
                gpu = Gpu(gpu_index)
                uuid = xlib_display.nvcontrol_get_gpu_uuid(gpu)
                handle = py3nvml.nvmlDeviceGetHandleByUUID(uuid.encode('utf-8'))
                memory_total = None
                memory_used = None
                mem_info = self._nvml_get_val(py3nvml.nvmlDeviceGetMemoryInfo, handle)
                if mem_info is not None:
                    memory_used = mem_info.used // 1024 // 1024
                    memory_total = mem_info.total // 1024 // 1024
                util = xlib_display.nvcontrol_get_utilization_rates(gpu)
                info = Info(
                    name=xlib_display.nvcontrol_get_name(gpu),
                    vbios=xlib_display.nvcontrol_get_vbios_version(gpu),
                    driver=xlib_display.nvcontrol_get_driver_version(gpu),
                    pcie_current_generation=xlib_display.nvcontrol_get_curr_pcie_link_generation(gpu),
                    pcie_max_generation=self._nvml_get_val(py3nvml.nvmlDeviceGetMaxPcieLinkGeneration, handle),
                    pcie_current_link=xlib_display.nvcontrol_get_curr_pcie_link_width(gpu),
                    pcie_max_link=xlib_display.nvcontrol_get_max_pcie_link_width(gpu),
                    cuda_cores=xlib_display.nvcontrol_get_cuda_cores(gpu),
                    uuid=uuid,
                    memory_total=memory_total,
                    memory_used=memory_used,
                    memory_interface=xlib_display.nvcontrol_get_memory_bus_width(gpu),
                    memory_usage=util.get('memory') if util is not None else None,
                    gpu_usage=util.get('graphics') if util is not None else None,
                    encoder_usage=xlib_display.nvcontrol_get_encoder_utilization(gpu),
                    decoder_usage=xlib_display.nvcontrol_get_decoder_utilization(gpu)
                )

                power = self._get_power_from_py3nvml(handle)
                temp = self._get_temp_from_py3nvml(handle)

                perf_modes = xlib_display.nvcontrol_get_performance_modes(gpu)
                perf_mode = next((p for p in perf_modes if p['perf'] == len(perf_modes) - 1), None)
                clock_info = xlib_display.nvcontrol_get_clock_info(gpu)
                if perf_mode:
                    clocks = Clocks(
                        graphic_current=clock_info.get('nvclock') if clock_info is not None else None,
                        graphic_max=perf_mode.get('nvclockmax') if perf_mode is not None else None,
                        sm_current=self._nvml_get_val(py3nvml.nvmlDeviceGetClockInfo, handle, NVML_CLOCK_SM),
                        sm_max=self._nvml_get_val(py3nvml.nvmlDeviceGetMaxClockInfo, handle, NVML_CLOCK_SM),
                        memory_current=clock_info.get('memclock') if clock_info is not None else None,
                        memory_max=perf_mode.get('memclockmax') if perf_mode is not None else None,
                        video_current=self._nvml_get_val(py3nvml.nvmlDeviceGetClockInfo, handle, 3),  # Missing
                        video_max=self._nvml_get_val(py3nvml.nvmlDeviceGetMaxClockInfo, handle, 3)  # Missing
                    )
                else:
                    clocks = Clocks()

                perf_level_max = perf_mode.get('perf') if perf_mode else None
                mem_transfer_rate_offset_range = \
                    xlib_display.nvcontrol_get_mem_transfer_rate_offset_range(gpu, perf_level_max)
                if mem_transfer_rate_offset_range is not None:
                    mem_clock_offset_range = (mem_transfer_rate_offset_range[0] // 2,
                                              mem_transfer_rate_offset_range[1] // 2)
                    mem_transfer_rate_offset = xlib_display.nvcontrol_get_mem_transfer_rate_offset(gpu, perf_level_max)
                    mem_clock_offset = None
                    if mem_transfer_rate_offset is not None:
                        mem_clock_offset = mem_transfer_rate_offset // 2
                    overclock = Overclock(
                        available=mem_transfer_rate_offset is not None,
                        gpu_range=xlib_display.nvcontrol_get_gpu_nvclock_offset_range(gpu, perf_level_max),
                        gpu_offset=xlib_display.nvcontrol_get_gpu_nvclock_offset(gpu, perf_level_max),
                        memory_range=mem_clock_offset_range,
                        memory_offset=mem_clock_offset,
                        perf_level_max=perf_level_max
                    )
                else:
                    overclock = Overclock(perf_level_max=perf_mode.get('perf') if perf_mode else None)

                manual_control = xlib_display.nvcontrol_get_cooler_manual_control_enabled(gpu)
                fan_list: Optional[List[Tuple[int, int]]] = None
                fan_indexes = xlib_display.nvcontrol_get_coolers_used_by_gpu(gpu)
                if fan_indexes:
                    fan_list = []
                    for i in fan_indexes:
                        fan = Cooler(i)
                        duty = xlib_display.nvcontrol_get_fan_duty(fan)
                        rpm = xlib_display.nvcontrol_get_fan_rpm(fan)
                        if duty is not None and rpm is not None:
                            fan_list.append((duty, rpm))
                fan = Fan(
                    fan_list=fan_list,
                    control_allowed=manual_control is not None,
                    manual_control=manual_control is not None and manual_control,
                )

                gpu_status = GpuStatus(
                    index=gpu_index,
                    info=info,
                    power=power,
                    temp=temp,
                    fan=fan,
                    clocks=clocks,
                    overclock=overclock
                )

                # Used to test Empty data
                # gpu_status = GpuStatus(
                #     index=gpu_index,
                #     info=Info(),
                #     power=Power(),
                #     temp=Temp(),
                #     fan=Fan(),
                #     clocks=Clocks(),
                #     overclock=Overclock()
                # )
                gpu_status_list.append(gpu_status)
            time2 = time.time()
            LOG.debug(f'Fetching new data took {((time2 - time1) * 1000.0):.3f} ms')
            return Status(gpu_status_list)
        except:
            LOG.exception("Error while getting status")
        finally:
            try:
                if xlib_display:
                    xlib_display.close()
                py3nvml.nvmlShutdown()
            except:
                LOG.exception("Error while getting status")
        return None

    def set_overclock(self, gpu_index: int, perf: int, gpu_offset: int, memory_offset: int) -> bool:
        xlib_display = display.Display(self._ctrl_display)
        gpu = Gpu(gpu_index)
        gpu_result = xlib_display.nvcontrol_set_gpu_nvclock_offset(gpu, perf, gpu_offset)
        mem_result = xlib_display.nvcontrol_set_mem_transfer_rate_offset(gpu, perf, memory_offset * 2)
        xlib_display.close()
        return gpu_result is True and mem_result is True

    @staticmethod
    def set_power_limit(gpu_index: int, limit: int) -> bool:
        cmd = ['pkexec',
               _NVIDIA_SMI_BINARY_NAME,
               '-i',
               str(gpu_index),
               '-pl',
               str(limit)]
        result = run_and_get_stdout(cmd)
        LOG.info(f"Exit code: {result[0]}. {result[1]}\n{result[1]}")
        return result[0] == 0

    def set_all_gpus_fan_to_auto(self) -> None:
        for gpu_index in range(self._gpu_count):
            self.set_fan_speed(gpu_index, manual_control=False)

    def set_fan_speed(self, gpu_index: int, speed: int = 100, manual_control: bool = False) -> bool:
        xlib_display = display.Display(self._ctrl_display)
        gpu = Gpu(gpu_index)
        fan_indexes = xlib_display.nvcontrol_get_coolers_used_by_gpu(gpu)
        error = False
        if fan_indexes:
            result = xlib_display.nvcontrol_set_cooler_manual_control_enabled(gpu, manual_control)
            if not result:
                error = True
            for fan_index in fan_indexes:
                result = xlib_display.nvcontrol_set_fan_duty(Cooler(fan_index), speed)
                if not result:
                    error = True
        xlib_display.close()
        return error

    @staticmethod
    def _nvml_get_val(a_function: Callable, *args: Any) -> Any:
        try:
            return a_function(*args)
        except NVMLError as err:
            if err.value == NVML_ERROR_NOT_SUPPORTED:
                LOG.debug(f"Function {a_function.__name__} not supported")
                return None
            if err.value == NVML_ERROR_UNKNOWN:
                LOG.warning(f"Unknown error while executing function {a_function.__name__}")
                return None
            LOG.error(f"Error value = {err.value}")
            raise err

    def _get_power_from_py3nvml(self, handle: Any) -> Power:
        power_con = self._nvml_get_val(py3nvml.nvmlDeviceGetPowerManagementLimitConstraints, handle)
        return Power(
            draw=self._convert_milliwatt_to_watt(self._nvml_get_val(py3nvml.nvmlDeviceGetPowerUsage, handle)),
            limit=self._convert_milliwatt_to_watt(
                self._nvml_get_val(py3nvml.nvmlDeviceGetPowerManagementLimit, handle)),
            default=self._convert_milliwatt_to_watt(
                self._nvml_get_val(py3nvml.nvmlDeviceGetPowerManagementDefaultLimit, handle)),
            minimum=None if power_con is None else self._convert_milliwatt_to_watt(power_con[0]),
            enforced=self._convert_milliwatt_to_watt(
                self._nvml_get_val(py3nvml.nvmlDeviceGetEnforcedPowerLimit, handle)),
            maximum=None if power_con is None else self._convert_milliwatt_to_watt(power_con[1])
        )

    @staticmethod
    def _convert_milliwatt_to_watt(milliwatt: Optional[int]) -> Optional[float]:
        return None if milliwatt is None else milliwatt / 1000

    def _get_temp_from_py3nvml(self, handle: Any) -> Temp:
        return Temp(
            gpu=self._nvml_get_val(py3nvml.nvmlDeviceGetTemperature, handle, NVML_TEMPERATURE_GPU),
            maximum=self._nvml_get_val(
                py3nvml.nvmlDeviceGetTemperatureThreshold, handle, 3),  # NVML_TEMPERATURE_THRESHOLD_GPU_MAX is missing
            slowdown=self._nvml_get_val(
                py3nvml.nvmlDeviceGetTemperatureThreshold, handle, NVML_TEMPERATURE_THRESHOLD_SLOWDOWN),
            shutdown=self._nvml_get_val(
                py3nvml.nvmlDeviceGetTemperatureThreshold, handle, NVML_TEMPERATURE_THRESHOLD_SHUTDOWN),
        )
