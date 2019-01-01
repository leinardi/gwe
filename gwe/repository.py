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
import re
import subprocess
import threading
from typing import Optional, List, Tuple, Callable, Any
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from injector import singleton, inject
from py3nvml import py3nvml
from py3nvml.py3nvml import NVMLError, NVML_ERROR_NOT_SUPPORTED, NVML_TEMPERATURE_GPU, \
    NVML_TEMPERATURE_THRESHOLD_SHUTDOWN, NVML_TEMPERATURE_THRESHOLD_SLOWDOWN, NVML_CLOCK_MEM, NVML_CLOCK_SM, \
    NVML_CLOCK_GRAPHICS

from gwe.model import Status, Info, Power, Temp, Clocks, GpuStatus, Fan, Overclock
from gwe.util.concurrency import synchronized_with_attr

LOG = logging.getLogger(__name__)

NOT_AVAILABLE_STRING = 'N/A'
_NVIDIA_SMI_BINARY_NAME = 'nvidia-smi'
_NVIDIA_SETTINGS_BINARY_NAME = 'nvidia-settings'


def run_and_get_stdout(command: List[str], pipe_command: List[str] = None) -> Tuple[int, str]:
    if not pipe_command:
        process1 = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        output = process1.communicate()[0]
        output = output.decode(encoding='UTF-8')
        return process1.returncode, output
    process1 = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    process2 = subprocess.Popen(pipe_command, stdin=process1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process1.stdout.close()
    output = process2.communicate()[0]
    output = output.decode(encoding='UTF-8')
    return process2.returncode, output


def query_settings(gpu_index: Optional[int], terse: bool, xargs: bool, *attrs: str) -> Tuple[int, str]:
    cmd = [_NVIDIA_SETTINGS_BINARY_NAME]
    for attr in attrs:
        cmd.append('-q')
        cmd.append("[gpu:%d]/%s" % (gpu_index, attr) if gpu_index is not None else attr)
    if terse:
        cmd.append('-t')
    if xargs:
        result = run_and_get_stdout(cmd, ['xargs'])
    else:
        result = run_and_get_stdout(cmd)
    return result[0], result[1].rstrip('\n')


def query_gpu_setting(gpu_index: int, attr: str) -> str:
    result = query_settings(gpu_index, True, False, attr)
    if result[0] == 0:
        return result[1]
    else:
        return NOT_AVAILABLE_STRING


@singleton
class NvidiaRepository:
    @inject
    def __init__(self) -> None:
        self.lock = threading.RLock()

    @staticmethod
    def is_nvidia_smi_available() -> bool:
        return run_and_get_stdout(['which', _NVIDIA_SMI_BINARY_NAME])[0] == 0

    @staticmethod
    def is_nvidia_settings_available() -> bool:
        return run_and_get_stdout(['which', _NVIDIA_SETTINGS_BINARY_NAME])[0] == 0

    @synchronized_with_attr("lock")
    def get_status(self) -> Optional[Status]:
        output = run_and_get_stdout([_NVIDIA_SMI_BINARY_NAME, '-q', '-x'])
        if output[0]:
            LOG.error(output[1])
        else:
            root = ElementTree.fromstring(output[1])
            gpu_status_list: List[GpuStatus] = []
            gpu_index = 0
            for gpu in root.findall('gpu'):
                gpu.append(root.find('driver_version'))
                info = self._get_info_from_smi_xml(gpu)
                info.cuda_cores = query_gpu_setting(gpu_index, 'CUDACores')
                info.memory_interface = query_gpu_setting(gpu_index, 'GPUMemoryInterface') + ' bit'
                power = self._get_power_from_smi_xml(gpu)
                temp = self._get_temp_from_smi_xml(gpu)
                clocks = self._get_clocks_from_smi_xml(gpu)
                fan = self._get_fan_from_settings()
                overclock = self._get_overclock_from_settings()
                gpu_status = GpuStatus(
                    gpu_id=gpu.get('id'),
                    info=info,
                    power=power,
                    temp=temp,
                    fan=fan,
                    clocks=clocks,
                    overclock=overclock
                )
                gpu_status_list.append(gpu_status)
                gpu_index += 1
            return Status(gpu_status_list)
        return None

    @staticmethod
    def _get_info_from_smi_xml(gpu: Element) -> Info:
        max_link_width = gpu.find('pci').find('pci_gpu_link_info').find('link_widths').find('max_link_width').text
        pcie = "%s Gen%s @ %s Gen%s" % (
            max_link_width,
            gpu.find('pci').find('pci_gpu_link_info').find('pcie_gen').find('max_link_gen').text,
            gpu.find('pci').find('pci_gpu_link_info').find('link_widths').find('current_link_width').text,
            gpu.find('pci').find('pci_gpu_link_info').find('pcie_gen').find('current_link_gen').text,
        ) if max_link_width != NOT_AVAILABLE_STRING else NOT_AVAILABLE_STRING
        return Info(
            name=gpu.find('product_name').text,
            vbios=gpu.find('vbios_version').text,
            driver=gpu.find('driver_version').text,
            pcie=pcie,
            cuda_cores=NOT_AVAILABLE_STRING,
            uuid=gpu.find('uuid').text,
            memory_size="%s / %s" %
                        (
                            gpu.find('fb_memory_usage').find('used').text,
                            gpu.find('fb_memory_usage').find('total').text),
            memory_interface=NOT_AVAILABLE_STRING,
            memory_usage=gpu.find('utilization').find('memory_util').text,
            gpu_usage=gpu.find('utilization').find('gpu_util').text,
            encoder_usage=gpu.find('utilization').find('encoder_util').text,
            decoder_usage=gpu.find('utilization').find('decoder_util').text,
        )

    @staticmethod
    def _get_power_from_smi_xml(gpu: Element) -> Power:
        return Power(
            draw=gpu.find('power_readings').find('power_draw').text,
            limit=gpu.find('power_readings').find('power_limit').text,
            default=gpu.find('power_readings').find('default_power_limit').text,
            minimum=gpu.find('power_readings').find('min_power_limit').text,
            enforced=gpu.find('power_readings').find('enforced_power_limit').text,
            maximum=gpu.find('power_readings').find('max_power_limit').text
        )

    @staticmethod
    def _get_temp_from_smi_xml(gpu: Element) -> Temp:
        maximum_element = gpu.find('temperature').find('gpu_temp_max_gpu_threshold')
        slowdown_element = gpu.find('temperature').find('gpu_temp_slow_threshold')
        shutdown_element = gpu.find('temperature').find('gpu_temp_max_threshold')
        return Temp(
            gpu=gpu.find('temperature').find('gpu_temp').text,
            maximum=maximum_element.text if maximum_element is not None else NOT_AVAILABLE_STRING,
            slowdown=slowdown_element.text if slowdown_element is not None else NOT_AVAILABLE_STRING,
            shutdown=shutdown_element.text if shutdown_element is not None else NOT_AVAILABLE_STRING,
        )

    @staticmethod
    def _get_clocks_from_smi_xml(gpu: Element) -> Clocks:
        return Clocks(
            graphic_current=gpu.find('clocks').find('graphics_clock').text,
            graphic_max=gpu.find('max_clocks').find('graphics_clock').text,
            sm_current=gpu.find('clocks').find('sm_clock').text,
            sm_max=gpu.find('max_clocks').find('sm_clock').text,
            memory_current=gpu.find('clocks').find('mem_clock').text,
            memory_max=gpu.find('max_clocks').find('mem_clock').text,
            video_current=gpu.find('clocks').find('video_clock').text if gpu.find('clocks').find(
                'video_clock') is not None else NOT_AVAILABLE_STRING,
            video_max=gpu.find('max_clocks').find('video_clock').text if gpu.find('clocks').find(
                'video_clock') is not None else NOT_AVAILABLE_STRING
        )

    @staticmethod
    def _get_fan_from_settings() -> Fan:
        result = query_settings(None, True, False, "GPUCurrentFanSpeed", "GPUCurrentFanSpeedRPM")
        if result[0] == 0:
            fan_list: List[Tuple[int, int]] = []
            output = result[1].split('\n')
            duty_list = output[:len(output) // 2]
            rpm_list = output[len(output) // 2:]
            for index, val in enumerate(duty_list):
                fan_list.append((int(val), int(rpm_list[index])))
            return Fan(fan_list[::-1])
        else:
            return Fan([])

    @staticmethod
    def _get_overclock_from_settings() -> Overclock:
        result = query_settings(0, True, True, "GPUPerfModes")
        if result[0] == 0:
            perf = len(result[1].split(';')) - 1  # it would be safer to parse and search

            result = query_settings(0, False, True,
                                    "GPUGraphicsClockOffset[%d]" % perf, "GPUMemoryTransferRateOffset[%d]" % perf)
            if result[0] == 0 and result[1]:
                ranges_raw = re.findall(r'range -?\d+ - -?\d+ ', result[1])
                gpu_offsets = ranges_raw[0].replace('range ', '').split(' - ')
                memory_offsets = ranges_raw[1].replace('range ', '').split(' - ')

                offsets_raw = re.findall(r': -?\d+. The valid', result[1])
                return Overclock(
                    available=True,
                    gpu_range=(int(gpu_offsets[0]), int(gpu_offsets[1])),
                    gpu_offset=int(offsets_raw[0].replace(':', '').replace('. The valid', '').strip()),
                    memory_range=(int(memory_offsets[0]), int(memory_offsets[1])),
                    memory_offset=int(offsets_raw[1].replace(':', '').replace('. The valid', '').strip()),
                    perf=perf
                )

        return Overclock(
            available=False,
            gpu_range=(0, 0),
            gpu_offset=0,
            memory_range=(0, 0),
            memory_offset=0,
            perf=0
        )

    @staticmethod
    def _set_overclock(gpu_index: int, perf: int, gpu_offset: int, memory_offset: int) -> None:
        cmd = [_NVIDIA_SETTINGS_BINARY_NAME,
               '-a',
               "[gpu:%d]/GPUGraphicsClockOffset[%d]=%d" % (gpu_index, perf, gpu_offset),
               '-a',
               "[gpu:%d]/GPUMemoryTransferRateOffset[%d]=%d" % (gpu_index, perf, memory_offset)]
        result = run_and_get_stdout(cmd, ['xargs'])
        LOG.info("Exit code: %d. %s", result[0], result[1])

# @staticmethod
# def _py3nvml_error_handler(a_function: Callable, *args: Any) -> Any:
#     try:
#         return a_function(*args)
#     except NVMLError as err:
#         if err.value == NVML_ERROR_NOT_SUPPORTED:
#             return "N/A"
#         else:
#             raise err
# def _get_status_from_py3nvml(self):
#     py3nvml.nvmlInit()
#     print("Driver Version: {}".format(py3nvml.nvmlSystemGetDriverVersion()))
#     # e.g. will print:
#     #   Driver Version: 352.00
#     gpu_count = py3nvml.nvmlDeviceGetCount()
#     for gpu_index in range(gpu_count):
#         handle = py3nvml.nvmlDeviceGetHandleByIndex(gpu_index)
#         info = self._get_info_from_py3nvml(handle)
#         power = self._get_power_from_py3nvml(handle)
#         temp = self._get_temp_from_py3nvml(handle)
#         clocks = self._get_clocks_from_py3nvml(handle)
#
#         print("Device {}: {}".format(gpu_index, py3nvml.nvmlDeviceGetName(handle)))
#         print("UUID {}: {}".format(gpu_index,
#                                    gpu.find('py3nvml.nvmlDeviceGetTemperature, handle,
#                                                                NVML_TEMPERATURE_GPU)))
#
#         py3nvml.nvmlShutdown()
#
# def _get_info_from_py3nvml(self, handle: Any) -> Info:
#     mem_info = self._py3nvml_error_handler(py3nvml.nvmlDeviceGetMemoryInfo, handle)
#     util = self._py3nvml_error_handler(py3nvml.nvmlDeviceGetUtilizationRates, handle)
#     util_enc = self._py3nvml_error_handler(py3nvml.nvmlDeviceGetEncoderUtilization, handle)
#     util_dec = self._py3nvml_error_handler(py3nvml.nvmlDeviceGetDecoderUtilization, handle)
#     return Info(
#         name=self._py3nvml_error_handler(py3nvml.nvmlDeviceGetName, handle),
#         vbios=self._py3nvml_error_handler(py3nvml.nvmlDeviceGetVbiosVersion, handle),
#         driver=self._py3nvml_error_handler(py3nvml.nvmlSystemGetDriverVersion),
#         pcie="%sx g%s @ %sx g%s" % (
#             self._py3nvml_error_handler(py3nvml.nvmlDeviceGetMaxPcieLinkWidth, handle),
#             self._py3nvml_error_handler(py3nvml.nvmlDeviceGetMaxPcieLinkGeneration, handle),
#             self._py3nvml_error_handler(py3nvml.nvmlDeviceGetCurrPcieLinkWidth, handle),
#             self._py3nvml_error_handler(py3nvml.nvmlDeviceGetCurrPcieLinkGeneration, handle)
#
#         ),
#         cuda_version=NOT_AVAILABLE_STRING,
#         cuda_count=NOT_AVAILABLE_STRING,
#         uuid=self._py3nvml_error_handler(py3nvml.nvmlDeviceGetUUID, handle),
#         memory_size="%s / %s MiB" %
#                     (str(round(mem_info.used / 1024 / 1024)), str(round(mem_info.total / 1024 / 1024))),
#         memory_interface=NOT_AVAILABLE_STRING,
#         memory_usage=(str(util.memory) + ' %') if hasattr(util, 'memory') else util,
#         gpu_usage=(str(util.gpu) + ' %') if hasattr(util, 'gpu') else util,
#         encoder_usage=(str(util_enc[0]) + ' %') if isinstance(util_enc, list) else util_enc,
#         decoder_usage=(str(util_dec[0]) + ' %') if isinstance(util_dec, list) else util_dec,
#     )
#
# def _get_power_from_py3nvml(self, handle: Any) -> Power:
#     draw = self._py3nvml_error_handler(py3nvml.nvmlDeviceGetPowerUsage, handle)
#     limit = self._py3nvml_error_handler(py3nvml.nvmlDeviceGetPowerManagementLimit, handle)
#     default = self._py3nvml_error_handler(py3nvml.nvmlDeviceGetPowerManagementDefaultLimit, handle)
#     enforced = self._py3nvml_error_handler(py3nvml.nvmlDeviceGetEnforcedPowerLimit, handle)
#     power_con = self._py3nvml_error_handler(py3nvml.nvmlDeviceGetPowerManagementLimitConstraints, handle)
#     return Power(
#         draw=("%.2f W" % (draw / 1000)) if isinstance(draw, int) else draw,
#         limit=("%.2f W" % (limit / 1000)) if isinstance(limit, int) else limit,
#         default=("%.2f W" % (default / 1000)) if isinstance(default, int) else default,
#         minimum=("%.2f W" % (power_con[0] / 1000)) if isinstance(power_con, list) else power_con,
#         enforced=("%.2f W" % (enforced / 1000)) if isinstance(enforced, int) else enforced,
#         maximum=("%.2f W" % (power_con[1] / 1000)) if isinstance(power_con, list) else power_con
#     )
#
# def _get_temp_from_py3nvml(self, handle: Any) -> Temp:
#     return Temp(
#         gpu=str(self._py3nvml_error_handler(
#             py3nvml.nvmlDeviceGetTemperature, handle, NVML_TEMPERATURE_GPU)) + ' C',
#         maximum=NOT_AVAILABLE_STRING,
#         slowdown=str(self._py3nvml_error_handler(
#             py3nvml.nvmlDeviceGetTemperatureThreshold, handle, NVML_TEMPERATURE_THRESHOLD_SLOWDOWN)) + ' C',
#         shutdown=str(self._py3nvml_error_handler(
#             py3nvml.nvmlDeviceGetTemperatureThreshold, handle, NVML_TEMPERATURE_THRESHOLD_SHUTDOWN)) + ' C',
#     )
#
# def _get_clocks_from_py3nvml(self, handle: Any) -> Clocks:
#     return Clocks(
#         graphic_current=str(self._py3nvml_error_handler(
#             py3nvml.nvmlDeviceGetClockInfo, handle, NVML_CLOCK_GRAPHICS)) + ' MHz',
#         graphic_max=str(self._py3nvml_error_handler(
#             py3nvml.nvmlDeviceGetMaxClockInfo, handle, NVML_CLOCK_GRAPHICS)) + ' MHz',
#         sm_current=str(self._py3nvml_error_handler(
#             py3nvml.nvmlDeviceGetClockInfo, handle, NVML_CLOCK_SM)) + ' MHz',
#         sm_max=str(self._py3nvml_error_handler(
#             py3nvml.nvmlDeviceGetMaxClockInfo, handle, NVML_CLOCK_SM)) + ' MHz',
#         memory_current=str(self._py3nvml_error_handler(
#             py3nvml.nvmlDeviceGetClockInfo, handle, NVML_CLOCK_MEM)) + ' MHz',
#         memory_max=str(self._py3nvml_error_handler(
#             py3nvml.nvmlDeviceGetMaxClockInfo, handle, NVML_CLOCK_MEM)) + ' MHz',
#         video_current=NOT_AVAILABLE_STRING,
#         video_max=NOT_AVAILABLE_STRING,
#     )
