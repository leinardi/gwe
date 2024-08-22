# This file is part of gwe.
#
# Copyright (c) 2020 Roberto Leinardi
#
# gst is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gst is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gst.  If not, see <http://www.gnu.org/licenses/>.
import logging
import threading
import subprocess
import time
import os
from typing import List, Dict, Optional, Tuple, Callable, Any
from ctypes import *

from Xlib import display
from Xlib.ext.nvcontrol import Gpu, Cooler
from injector import singleton, inject
import pynvml

from gwe.model.clocks import Clocks
from gwe.model.fan import Fan
from gwe.model.gpu_status import GpuStatus
from gwe.model.info import Info
from gwe.model.overclock import Overclock
from gwe.model.power import Power
from gwe.model.status import Status
from gwe.model.temp import Temp
from gwe.util.concurrency import synchronized_with_attr

_LOG = logging.getLogger(__name__)
nv_control_extension = False

# Nvidia doesn't know how to make proper python bindings so we do it for them
def DeviceGetClockOffsets(device, ctype, pstate):
    c_clockOffsetsInfo = pynvml.c_nvmlClockOffset_t()
    c_clockOffsetsInfo.version = pynvml.nvmlClockOffset_v1
    c_clockOffsetsInfo.type = ctype
    c_clockOffsetsInfo.pstate = pstate
    fn = pynvml._nvmlGetFunctionPointer("nvmlDeviceGetClockOffsets");
    ret = fn(device, byref(c_clockOffsetsInfo))
    pynvml._nvmlCheckReturn(ret)
    return c_clockOffsetsInfo

def DeviceGetFanControlPolicy_v2(handle, fan):
    c_fanControlPolicy = pynvml._nvmlFanControlPolicy_t()
    fn = pynvml._nvmlGetFunctionPointer("nvmlDeviceGetFanControlPolicy_v2")
    ret = fn(handle, fan, byref(c_fanControlPolicy))
    _nvmlCheckReturn(ret)
    return c_fanControlPolicy.value


@singleton
class NvidiaRepository:
    @inject
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._gpu_count = 0
        self._gpu_setting_cache: List[Dict[str, str]] = []
        self._ctrl_display: Optional[str] = None
        self.elevated_process = None

    def check_elevated_process(self) -> None:
        if self.elevated_process == None:
            if 'MESON_BUILD_ROOT' in os.environ:
                path = os.environ['MESON_BUILD_ROOT'] + '/bin/gwe-agent'
            else:
                path = '/usr/bin/gwe-agent'
            self.elevated_process = subprocess.Popen(
                ['pkexec', 'python', '-B', path],
                bufsize=1,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                universal_newlines=True)
            result = self.elevated_process.stderr.readline()
            if result != "ready\n":
                self.elevated_process.communicate()
                self.elevated_process = None
                return False
        return True

    def remove_elevated_process(self) -> None:
        if not self.elevated_process == None:
            self.elevated_process.stdin.write("0 quit")
            self.elevated_process.communicate()

    def set_ctrl_display(self, ctrl_display: str) -> None:
        self._ctrl_display = ctrl_display

    @synchronized_with_attr("_lock")
    def has_nv_control_extension(self) -> bool:
        xlib_display = None

        try:
            xlib_display = display.Display(self._ctrl_display)
            nv_control_extension = bool(xlib_display.has_extension('NV-CONTROL'))
            return nv_control_extension
        except:
            _LOG.exception("Error while checking NV-CONTROL extension")
        finally:
            try:
                if xlib_display:
                    xlib_display.close()
            except:
                _LOG.exception("Error while checking NV-CONTROL extension")
        nv_control_extension = False
        return False

    @synchronized_with_attr("_lock")
    def has_nvml_shared_library(self) -> bool:
        try:
            pynvml.nvmlInit()
            pynvml.nvmlShutdown()
            return True
        except:
            _LOG.exception("Error while checking NVML Shared Library")
        return False

    @synchronized_with_attr("_lock")
    def has_min_driver_version(self) -> bool:
        try:
            pynvml.nvmlInit()
            driver = self._nvml_get_val(pynvml.nvmlSystemGetDriverVersion)
            pynvml.nvmlShutdown()
        except:
            _LOG.exception("Error while checking NVML Shared Library")
            return False
        vmajor = int(driver.split(".", 1)[0])
        if 'WAYLAND_DISPLAY' not in os.environ and vmajor >= 535 or vmajor >= 555:
            return True

    @synchronized_with_attr("_lock")
    def get_status(self) -> Optional[Status]:
        xlib_display = None
        try:
            time1 = time.time()
            pynvml.nvmlInit()
            self._gpu_count = self._nvml_get_val(pynvml.nvmlDeviceGetCount)
            gpu_status_list: List[GpuStatus] = []
            for gpu_index in range(self._gpu_count):
                gpu = Gpu(gpu_index)
                handle = self._nvml_get_val(pynvml.nvmlDeviceGetHandleByIndex, gpu_index)
                memory_total = None
                memory_used = None
                mem_info = self._nvml_get_val(pynvml.nvmlDeviceGetMemoryInfo, handle)
                if mem_info is not None:
                    memory_used = mem_info.used // 1024 // 1024
                    memory_total = mem_info.total // 1024 // 1024
                util = self._nvml_get_val(pynvml.nvmlDeviceGetUtilizationRates, handle)
                info = Info(
                    name=self._nvml_get_val(pynvml.nvmlDeviceGetName, handle),
                    vbios=self._nvml_get_val(pynvml.nvmlDeviceGetVbiosVersion, handle),
                    driver=self._nvml_get_val(pynvml.nvmlSystemGetDriverVersion),
                    pcie_current_generation=self._nvml_get_val(pynvml.nvmlDeviceGetCurrPcieLinkGeneration, handle),
                    pcie_max_generation=self._nvml_get_val(pynvml.nvmlDeviceGetMaxPcieLinkGeneration, handle),
                    pcie_current_link=self._nvml_get_val(pynvml.nvmlDeviceGetCurrPcieLinkWidth, handle),
                    pcie_max_link=self._nvml_get_val(pynvml.nvmlDeviceGetMaxPcieLinkWidth, handle),
                    cuda_cores=self._nvml_get_val(pynvml.nvmlDeviceGetNumGpuCores, handle),
                    uuid = self._nvml_get_val(pynvml.nvmlDeviceGetUUID, handle),
                    memory_total=memory_total,
                    memory_used=memory_used,
                    memory_interface=self._nvml_get_val(pynvml.nvmlDeviceGetMemoryBusWidth, handle),
                    memory_usage=util.memory if util is not None else None,
                    gpu_usage=util.gpu if util is not None else None,
                    encoder_usage=self._nvml_get_val(pynvml.nvmlDeviceGetEncoderUtilization, handle)[0],
                    decoder_usage=self._nvml_get_val(pynvml.nvmlDeviceGetDecoderUtilization, handle)[0],
                    persistence_mode=self._nvml_get_val(pynvml.nvmlDeviceGetPersistenceMode, handle)
                )

                power = self._get_power_from_pynvml(handle)
                temp = self._get_temp_from_pynvml(handle)

                clocks = Clocks(
                    graphic_current=self._nvml_get_val(pynvml.nvmlDeviceGetClockInfo, handle, pynvml.NVML_CLOCK_GRAPHICS),
                    graphic_max=self._nvml_get_val(pynvml.nvmlDeviceGetMaxClockInfo, handle, pynvml.NVML_CLOCK_GRAPHICS),
                    sm_current=self._nvml_get_val(pynvml.nvmlDeviceGetClockInfo, handle, pynvml.NVML_CLOCK_SM),
                    sm_max=self._nvml_get_val(pynvml.nvmlDeviceGetMaxClockInfo, handle, pynvml.NVML_CLOCK_SM),
                    memory_current=self._nvml_get_val(pynvml.nvmlDeviceGetClockInfo, handle, pynvml.NVML_CLOCK_MEM),
                    memory_max=self._nvml_get_val(pynvml.nvmlDeviceGetMaxClockInfo, handle, pynvml.NVML_CLOCK_MEM),
                    video_current=self._nvml_get_val(pynvml.nvmlDeviceGetClockInfo, handle, pynvml.NVML_CLOCK_VIDEO),
                    video_max=self._nvml_get_val(pynvml.nvmlDeviceGetMaxClockInfo, handle, pynvml.NVML_CLOCK_VIDEO)
                )

                if nv_control_extension:
                    xlib_display = display.Display(self._ctrl_display)
                    perf_modes = xlib_display.nvcontrol_get_performance_modes(gpu)
                    perf_mode = next((p for p in perf_modes if p['perf'] == len(perf_modes) - 1), None)
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
                else:
                    gpuclockinfo = self._nvml_get_val(DeviceGetClockOffsets, handle, 0, 0)
                    memclockinfo = self._nvml_get_val(DeviceGetClockOffsets, handle, 2, 0)
                    overclock = Overclock(
                        available=True,
                        gpu_range=(gpuclockinfo.minClockOffsetMHz ,gpuclockinfo.maxClockOffsetMHz),
                        gpu_offset=gpuclockinfo.clockOffsetMHz,
                        memory_range=(memclockinfo.minClockOffsetMHz ,memclockinfo.maxClockOffsetMHz),
                        memory_offset=memclockinfo.clockOffsetMHz,
                        perf_level_max=0
                    )
                    fan_list: Optional[List[Tuple[int, int]]] = None
                    fan_indexes = self._nvml_get_val(pynvml.nvmlDeviceGetNumFans, handle) or 0
                    manual_control = False
                    if fan_indexes > 0:
                        manual_control = self._nvml_get_val(DeviceGetFanControlPolicy_v2, handle, 0) == pynvml.NVML_FAN_POLICY_MANUAL
                        fan_list = []
                        for i in range(fan_indexes):
                            duty = self._nvml_get_val(pynvml.nvmlDeviceGetFanSpeed_v2, handle, i)
                            rpm = 0 # No RPM in nvml for now
                            if duty is not None:
                                fan_list.append((duty, rpm))
                    fan = Fan(
                        fan_list=fan_list,
                        control_allowed=fan_indexes > 0,
                        manual_control=manual_control,
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
            _LOG.debug(f'Fetching new data took {((time2 - time1) * 1000.0):.3f} ms')
            return Status(gpu_status_list)
        except:
            _LOG.exception("Error while getting status")
        finally:
            try:
                if xlib_display:
                    xlib_display.close()
                pynvml.nvmlShutdown()
            except:
                _LOG.exception("Error while getting status")
        return None

    def set_overclock(self, gpu_index: int, perf: int, gpu_offset: int, memory_offset: int) -> bool:
        if nv_control_extension:
            xlib_display = display.Display(self._ctrl_display)
            gpu = Gpu(gpu_index)
            gpu_result = (xlib_display.nvcontrol_set_gpu_nvclock_offset(gpu, perf, gpu_offset) or
                        xlib_display.nvcontrol_set_gpu_nvclock_offset_all_levels(gpu, gpu_offset))
            mem_result = (xlib_display.nvcontrol_set_mem_transfer_rate_offset(gpu, perf, memory_offset * 2) or
                        xlib_display.nvcontrol_set_mem_transfer_rate_offset_all_levels(gpu, memory_offset * 2))
            xlib_display.close()
        else:
            if not self.check_elevated_process():
                return False
            self.elevated_process.stdin.write(str(gpu_index) + " gpu " + str(gpu_offset) + "\n")
            gpu_result = not int(self.elevated_process.stderr.readline())
            self.elevated_process.stdin.write(str(gpu_index) + " mem " + str(memory_offset) + "\n")
            mem_result = not int(self.elevated_process.stderr.readline())
        return gpu_result is True and mem_result is True

    def set_power_limit(self, gpu_index: int, limit: int) -> bool:
        if not self.check_elevated_process():
            return False
        self.elevated_process.stdin.write(str(gpu_index) + " pl " + str(limit) + "\n")
        result = int(self.elevated_process.stderr.readline())
        return result == 0

    def set_persistence_mode(self, gpu_index: int, mode: bool) -> bool:
        if not self.check_elevated_process():
            return False
        self.elevated_process.stdin.write(str(gpu_index) + " pm " + str(int(mode)) + "\n")
        result = int(self.elevated_process.stderr.readline())
        return result == 0

    def set_all_gpus_fan_to_auto(self) -> None:
        for gpu_index in range(self._gpu_count):
            self.set_fan_speed(gpu_index, manual_control=False)

    def set_fan_speed(self, gpu_index: int, speed: int = 100, manual_control: bool = False) -> bool:
        if nv_control_extension:
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
        else:
            pynvml.nvmlInit()
            handle = self._nvml_get_val(pynvml.nvmlDeviceGetHandleByIndex, gpu_index)
            fan_indexes = self._nvml_get_val(pynvml.nvmlDeviceGetNumFans, handle)
            if fan_indexes is not None and fan_indexes > 0:
                for fan_index in range(fan_indexes):
                    try:
                        if manual_control:
                            pynvml.nvmlDeviceSetFanSpeed_v2(handle, fan_index, speed)
                        else:
                            pynvml.nvmlDeviceSetDefaultFanSpeed_v2(handle, fan_index)
                    except pynvml.NVMLError as err:
                        if err.value == NVML_ERROR_INVALID_ARGUMENT:
                            _LOG.warning(f"Error setting speed for fan{fan_index} on gpu{gpu_index}")
                            return True
            pynvml.nvmlShutdown()

    @staticmethod
    def _nvml_get_val(a_function: Callable, *args: Any) -> Any:
        try:
            return a_function(*args)
        except pynvml.NVMLError as err:
            if err.value == pynvml.NVML_ERROR_NOT_SUPPORTED:
                _LOG.debug(f"Function {a_function.__name__} not supported")
                return None
            if err.value == pynvml.NVML_ERROR_UNKNOWN:
                _LOG.warning(f"Unknown error while executing function {a_function.__name__}")
                return None
            _LOG.error(f"Error value = {err.value}")
            raise err

    def _get_power_from_pynvml(self, handle: Any) -> Power:
        power_con = self._nvml_get_val(pynvml.nvmlDeviceGetPowerManagementLimitConstraints, handle)
        return Power(
            draw=self._convert_milliwatt_to_watt(self._nvml_get_val(pynvml.nvmlDeviceGetPowerUsage, handle)),
            limit=self._convert_milliwatt_to_watt(
                self._nvml_get_val(pynvml.nvmlDeviceGetPowerManagementLimit, handle)),
            default=self._convert_milliwatt_to_watt(
                self._nvml_get_val(pynvml.nvmlDeviceGetPowerManagementDefaultLimit, handle)),
            minimum=None if power_con is None else self._convert_milliwatt_to_watt(power_con[0]),
            enforced=self._convert_milliwatt_to_watt(
                self._nvml_get_val(pynvml.nvmlDeviceGetEnforcedPowerLimit, handle)),
            maximum=None if power_con is None else self._convert_milliwatt_to_watt(power_con[1])
        )

    @staticmethod
    def _convert_milliwatt_to_watt(milliwatt: Optional[int]) -> Optional[float]:
        return None if milliwatt is None else milliwatt / 1000

    def _get_temp_from_pynvml(self, handle: Any) -> Temp:
        return Temp(
            gpu=self._nvml_get_val(pynvml.nvmlDeviceGetTemperature, handle, pynvml.NVML_TEMPERATURE_GPU),
            maximum=self._nvml_get_val(
                pynvml.nvmlDeviceGetTemperatureThreshold, handle, 3),  # NVML_TEMPERATURE_THRESHOLD_GPU_MAX is missing
            slowdown=self._nvml_get_val(
                pynvml.nvmlDeviceGetTemperatureThreshold, handle, pynvml.NVML_TEMPERATURE_THRESHOLD_SLOWDOWN),
            shutdown=self._nvml_get_val(
                pynvml.nvmlDeviceGetTemperatureThreshold, handle, pynvml.NVML_TEMPERATURE_THRESHOLD_SHUTDOWN),
        )
