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
    NVML_TEMPERATURE_THRESHOLD_SLOWDOWN, NVML_TEMPERATURE_THRESHOLD_SHUTDOWN, NVML_CLOCK_SM, NVML_CLOCK_GRAPHICS, \
    NVML_CLOCK_MEM, NVML_ERROR_UNKNOWN

from gwe.model import Status, Info, Power, Temp, Clocks, GpuStatus, Fan, Overclock
from gwe.nvidia import nvcmd
from gwe.nvidia.nvtarget import GPU, Cooler
from gwe.util.concurrency import synchronized_with_attr
from gwe.util.deployment import is_flatpak

LOG = logging.getLogger(__name__)

NOT_AVAILABLE_STRING = 'N/A'
_NVIDIA_SMI_BINARY_NAME = 'nvidia-smi'
_NVIDIA_SETTINGS_BINARY_NAME = 'nvidia-settings'
_FLATPAK_COMMAND_PREFIX = ['flatpak-spawn', '--host']


def run_and_get_stdout(command: List[str], pipe_command: List[str] = None) -> Tuple[int, str]:
    if pipe_command is None:
        if is_flatpak():
            command = _FLATPAK_COMMAND_PREFIX + command
        process1 = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        output = process1.communicate()[0]
        output = output.decode(encoding='UTF-8')
        return process1.returncode, output
    if is_flatpak():
        command = _FLATPAK_COMMAND_PREFIX + command
        pipe_command = _FLATPAK_COMMAND_PREFIX + pipe_command
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
        self._lock = threading.RLock()
        self._gpu_count = 0
        self._gpu_setting_cache: List[Dict[str, str]] = []

    @staticmethod
    def is_nvidia_smi_available() -> bool:
        return run_and_get_stdout(['which', _NVIDIA_SMI_BINARY_NAME])[0] == 0

    @staticmethod
    def is_nvidia_settings_available() -> bool:
        return run_and_get_stdout(['which', _NVIDIA_SETTINGS_BINARY_NAME])[0] == 0

    def _get_gpu_setting_from_cache(self, gpu_index: int, name: str) -> str:
        if name not in self._gpu_setting_cache[gpu_index]:
            self._gpu_setting_cache[gpu_index][name] = query_gpu_setting(gpu_index, name)
        return self._gpu_setting_cache[gpu_index][name]

    @synchronized_with_attr("_lock")
    def get_status(self) -> Optional[Status]:
        nv = None
        try:
            time1 = time.time()
            py3nvml.nvmlInit()
            nv = nvcmd.NVidiaControl()
            nv.open()
            self._gpu_count = nv.get_gpu_count()
            gpu_status_list: List[GpuStatus] = []
            for gpu_index in range(self._gpu_count):
                handle = py3nvml.nvmlDeviceGetHandleByIndex(gpu_index)
                gpu = GPU(gpu_index)
                memory_total = None
                memory_used = None
                mem_info = self._nvml_get_val(py3nvml.nvmlDeviceGetMemoryInfo, handle)
                if mem_info:
                    memory_used = mem_info.used // 1024 // 1024
                    memory_total = mem_info.total // 1024 // 1024
                util = self._nvml_get_val(py3nvml.nvmlDeviceGetUtilizationRates, handle)
                util_enc = self._nvml_get_val(py3nvml.nvmlDeviceGetEncoderUtilization, handle)
                util_dec = self._nvml_get_val(py3nvml.nvmlDeviceGetDecoderUtilization, handle)
                info = Info(
                    name=self._nvml_get_val(py3nvml.nvmlDeviceGetName, handle),
                    vbios=self._nvml_get_val(py3nvml.nvmlDeviceGetVbiosVersion, handle),
                    driver=self._nvml_get_val(py3nvml.nvmlSystemGetDriverVersion),
                    pcie_generation=self._nvml_get_val(py3nvml.nvmlDeviceGetMaxPcieLinkGeneration, handle),
                    pcie_current_link=self._nvml_get_val(py3nvml.nvmlDeviceGetCurrPcieLinkWidth, handle),
                    pcie_max_link=self._nvml_get_val(py3nvml.nvmlDeviceGetMaxPcieLinkWidth, handle),
                    cuda_cores=nv.get_cuda_cores(gpu),
                    uuid=self._nvml_get_val(py3nvml.nvmlDeviceGetUUID, handle),
                    memory_total=memory_total,
                    memory_used=memory_used,
                    memory_interface=nv.get_memory_bus_width(gpu),
                    memory_usage=util.memory if hasattr(util, 'memory') else util,
                    gpu_usage=util.gpu if hasattr(util, 'gpu') else util,
                    encoder_usage=util_enc[0],
                    decoder_usage=util_dec[0]
                )

                power = self._get_power_from_py3nvml(handle)
                temp = self._get_temp_from_py3nvml(handle)

                perf_modes = nv.get_performance_modes(gpu)
                perf_mode = next((p for p in perf_modes if p['perf'] == len(perf_modes) - 1), None)
                if perf_mode:
                    clocks = Clocks(
                        graphic_current=self._nvml_get_val(py3nvml.nvmlDeviceGetClockInfo, handle, NVML_CLOCK_GRAPHICS),
                        graphic_max=perf_mode.get('nvclockmax'),
                        sm_current=self._nvml_get_val(py3nvml.nvmlDeviceGetClockInfo, handle, NVML_CLOCK_SM),
                        sm_max=self._nvml_get_val(py3nvml.nvmlDeviceGetMaxClockInfo, handle, NVML_CLOCK_SM),
                        memory_current=self._nvml_get_val(py3nvml.nvmlDeviceGetClockInfo, handle, NVML_CLOCK_MEM),
                        memory_max=perf_mode.get('memclockmax'),
                        video_current=self._nvml_get_val(py3nvml.nvmlDeviceGetClockInfo, handle, 3),  # Missing
                        video_max=self._nvml_get_val(py3nvml.nvmlDeviceGetMaxClockInfo, handle, 3)  # Missing
                    )
                else:
                    clocks = Clocks()

                mem_transfer_rate_offset_range = nv.get_mem_transfer_rate_offset_range(gpu)
                # perf_level = nv.get_current_performance_level(gpu)
                if mem_transfer_rate_offset_range is not None:
                    mem_clock_offset_range = (mem_transfer_rate_offset_range[0] // 2,
                                              mem_transfer_rate_offset_range[1] // 2)
                    mem_transfer_rate_offset = nv.get_mem_transfer_rate_offset(gpu)
                    mem_clock_offset = None
                    if mem_transfer_rate_offset is not None:
                        mem_clock_offset = mem_transfer_rate_offset // 2
                    overclock = Overclock(
                        available=mem_transfer_rate_offset is not None,
                        gpu_range=nv.get_gpu_nvclock_offset_range(gpu),
                        gpu_offset=nv.get_gpu_nvclock_offset(gpu),
                        memory_range=mem_clock_offset_range,
                        memory_offset=mem_clock_offset,
                        perf_level_max=perf_mode.get('perf') if perf_mode else None
                    )
                else:
                    overclock = Overclock(perf_level_max=perf_mode.get('perf') if perf_mode else None)

                manual_control = nv.get_cooler_manual_control_enabled(gpu)
                fan_list: Optional[List[Tuple[int, int]]] = None
                fan_indexes = nv.get_coolers_used_by_gpu(gpu)
                if fan_indexes:
                    fan_list = []
                    for i in fan_indexes:
                        fan = Cooler(i)
                        duty = nv.get_fan_duty(fan)
                        rpm = nv.get_fan_rpm(fan)
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
            LOG.debug('Fetching new data took {%.3f} ms' % ((time2 - time1) * 1000.0))
            return Status(gpu_status_list)
        except:
            LOG.exception("Error while getting status")
        finally:
            try:
                if nv:
                    nv.close()
                py3nvml.nvmlShutdown()
            except:
                LOG.exception("Error while getting status")
        return None

        # output = run_and_get_stdout([_NVIDIA_SMI_BINARY_NAME, '-q', '-x'])
        # if output[0]:
        #     LOG.error(output[1])
        # else:
        #     root = ElementTree.fromstring(output[1])
        #     gpu_status_list: List[GpuStatus] = []
        #     gpu_index = 0
        #     for gpu in root.findall('gpu'):
        #         if len(self._gpu_setting_cache) <= gpu_index:
        #             self._gpu_setting_cache.append({})
        #         gpu.append(root.find('driver_version'))
        #         info = self._get_info_from_smi_xml(gpu)
        #         info.cuda_cores = self._get_gpu_setting_from_cache(gpu_index, 'CUDACores')
        #         info.memory_interface = self._get_gpu_setting_from_cache(gpu_index, 'GPUMemoryInterface') + ' bit'
        #         power = self._get_power_from_smi_xml(gpu)
        #         temp = self._get_temp_from_smi_xml(gpu)
        #         clocks = self._get_clocks_from_smi_xml(gpu)
        #         fan = self._get_fan_from_settings(gpu_index)
        #         overclock = self._get_overclock_from_settings(gpu_index)
        #         gpu_status = GpuStatus(
        #             gpu_id=gpu.get('id'),
        #             index=gpu_index,
        #             info=info,
        #             power=power,
        #             temp=temp,
        #             fan=fan,
        #             clocks=clocks,
        #             overclock=overclock
        #         )
        #         gpu_status_list.append(gpu_status)
        #         gpu_index += 1
        #     self._gpu_count = gpu_index
        #     return Status(gpu_status_list)
        # return None

    # @staticmethod
    # def _get_info_from_smi_xml(gpu: Element) -> Info:
    #     max_link_width = gpu.find('pci').find('pci_gpu_link_info').find('link_widths').find('max_link_width').text
    #     pcie = "%s Gen%s @ %s Gen%s" % (
    #         max_link_width,
    #         gpu.find('pci').find('pci_gpu_link_info').find('pcie_gen').find('max_link_gen').text,
    #         gpu.find('pci').find('pci_gpu_link_info').find('link_widths').find('current_link_width').text,
    #         gpu.find('pci').find('pci_gpu_link_info').find('pcie_gen').find('current_link_gen').text,
    #     ) if max_link_width != NOT_AVAILABLE_STRING else NOT_AVAILABLE_STRING
    #     return Info(
    #         name=gpu.find('product_name').text,
    #         vbios=gpu.find('vbios_version').text,
    #         driver=gpu.find('driver_version').text,
    #         pcie=pcie,
    #         cuda_cores=NOT_AVAILABLE_STRING,
    #         uuid=gpu.find('uuid').text,
    #         memory_size="%s / %s" %
    #                     (
    #                         gpu.find('fb_memory_usage').find('used').text,
    #                         gpu.find('fb_memory_usage').find('total').text),
    #         memory_interface=NOT_AVAILABLE_STRING,
    #         memory_usage=gpu.find('utilization').find('memory_util').text,
    #         gpu_usage=gpu.find('utilization').find('gpu_util').text,
    #         encoder_usage=gpu.find('utilization').find('encoder_util').text,
    #         decoder_usage=gpu.find('utilization').find('decoder_util').text,
    #     )
    #
    # @staticmethod
    # def _get_power_from_smi_xml(gpu: Element) -> Power:
    #     return Power(
    #         draw=gpu.find('power_readings').find('power_draw').text,
    #         limit=gpu.find('power_readings').find('power_limit').text,
    #         default=gpu.find('power_readings').find('default_power_limit').text,
    #         minimum=gpu.find('power_readings').find('min_power_limit').text,
    #         enforced=gpu.find('power_readings').find('enforced_power_limit').text,
    #         maximum=gpu.find('power_readings').find('max_power_limit').text
    #     )
    #
    # @staticmethod
    # def _get_temp_from_smi_xml(gpu: Element) -> Temp:
    #     maximum_element = gpu.find('temperature').find('gpu_temp_max_gpu_threshold')
    #     slowdown_element = gpu.find('temperature').find('gpu_temp_slow_threshold')
    #     shutdown_element = gpu.find('temperature').find('gpu_temp_max_threshold')
    #     return Temp(
    #         gpu=gpu.find('temperature').find('gpu_temp').text,
    #         maximum=maximum_element.text if maximum_element is not None else NOT_AVAILABLE_STRING,
    #         slowdown=slowdown_element.text if slowdown_element is not None else NOT_AVAILABLE_STRING,
    #         shutdown=shutdown_element.text if shutdown_element is not None else NOT_AVAILABLE_STRING,
    #     )
    #
    # @staticmethod
    # def _get_clocks_from_smi_xml(gpu: Element) -> Clocks:
    #     return Clocks(
    #         graphic_current=gpu.find('clocks').find('graphics_clock').text,
    #         graphic_max=gpu.find('max_clocks').find('graphics_clock').text,
    #         sm_current=gpu.find('clocks').find('sm_clock').text,
    #         sm_max=gpu.find('max_clocks').find('sm_clock').text,
    #         memory_current=gpu.find('clocks').find('mem_clock').text,
    #         memory_max=gpu.find('max_clocks').find('mem_clock').text,
    #         video_current=gpu.find('clocks').find('video_clock').text if gpu.find('clocks').find(
    #             'video_clock') is not None else NOT_AVAILABLE_STRING,
    #         video_max=gpu.find('max_clocks').find('video_clock').text if gpu.find('clocks').find(
    #             'video_clock') is not None else NOT_AVAILABLE_STRING
    #     )
    #
    # @staticmethod
    # def _get_fan_from_settings(gpu_index: int) -> Fan:
    #     result = query_settings(None, True, False, "GPUCurrentFanSpeed", "GPUCurrentFanSpeedRPM")
    #     if result[0] == 0:
    #         fan_list: List[Tuple[int, int]] = []
    #         output = result[1].split('\n')
    #         duty_list = output[:len(output) // 2]
    #         rpm_list = output[len(output) // 2:]
    #         for index, val in enumerate(duty_list):
    #             fan_list.append((int(val), int(rpm_list[index])))
    #         result = query_settings(gpu_index, True, True, 'GPUFanControlState')
    #         manual_control = result[1].strip() == '1'
    #         contro_allowed = result[0] == 0 and result[1] != ''
    #         return Fan(
    #             fan_list=fan_list[::-1],
    #             control_allowed=contro_allowed,
    #             manual_control=manual_control
    #         )
    #     return Fan(
    #         fan_list=[],
    #         control_allowed=False,
    #         manual_control=False
    #     )
    #
    # def _get_overclock_from_settings(self, gpu_index: int) -> Overclock:
    #     result = self._get_gpu_setting_from_cache(0, "GPUPerfModes").replace('\n', ' ')
    #     if result != NOT_AVAILABLE_STRING:
    #         perf = len(result.split(';')) - 1  # it would be safer to parse and search
    #
    #         result = query_settings(gpu_index, False, True,
    #                                 "GPUGraphicsClockOffset[%d]" % perf, "GPUMemoryTransferRateOffset[%d]" % perf)
    #         if result[0] == 0 and result[1]:
    #             ranges_raw = re.findall(r'range -?\d+ - -?\d+ ', result[1])
    #             gpu_offsets = ranges_raw[0].replace('range ', '').split(' - ')
    #             memory_offsets = ranges_raw[1].replace('range ', '').split(' - ')
    #
    #             offsets_raw = re.findall(r': -?\d+. The valid', result[1])
    #             return Overclock(
    #                 available=True,
    #                 gpu_range=(int(gpu_offsets[0]), int(gpu_offsets[1])),
    #                 gpu_offset=int(offsets_raw[0].replace(':', '').replace('. The valid', '').strip()),
    #                 memory_range=(int(memory_offsets[0]) // 2, int(memory_offsets[1]) // 2),
    #                 memory_offset=int(offsets_raw[1].replace(':', '').replace('. The valid', '').strip()) // 2,
    #                 perf=perf
    #             )
    #
    #     return Overclock(
    #         available=False,
    #         gpu_range=(0, 0),
    #         gpu_offset=0,
    #         memory_range=(0, 0),
    #         memory_offset=0,
    #         perf=0
    #     )

    @staticmethod
    def set_overclock(gpu_index: int, perf: int, gpu_offset: int, memory_offset: int) -> bool:
        cmd = [_NVIDIA_SETTINGS_BINARY_NAME,
               '-a',
               "[gpu:%d]/GPUGraphicsClockOffset[%d]=%d" % (gpu_index, perf, gpu_offset),
               '-a',
               "[gpu:%d]/GPUMemoryTransferRateOffset[%d]=%d" % (gpu_index, perf, memory_offset * 2)]
        result = run_and_get_stdout(cmd, ['xargs'])
        LOG.info("Exit code: %d. %s", result[0], result[1])
        return result[0] == 0

    @staticmethod
    def set_power_limit(gpu_index: int, limit: int) -> bool:
        cmd = ['pkexec',
               _NVIDIA_SMI_BINARY_NAME,
               '-i',
               str(gpu_index),
               '-pl',
               str(limit)]
        result = run_and_get_stdout(cmd, ['xargs'])
        LOG.info("Exit code: %d. %s", result[0], result[1])
        return result[0] == 0

    def set_all_gpus_fan_to_auto(self) -> None:
        for gpu_index in range(self._gpu_count):
            self.set_fan_speed(gpu_index, manual_control=False)

    @staticmethod
    def set_fan_speed(gpu_index: int, speed: int = 100, manual_control: bool = False) -> bool:
        cmd = [_NVIDIA_SETTINGS_BINARY_NAME,
               '-a',
               "[gpu:%d]/GPUFanControlState=%d" % (gpu_index, 1 if manual_control else 0)]
        if manual_control:
            cmd.append('-a')
            cmd.append("GPUTargetFanSpeed=%d" % speed)
        result = run_and_get_stdout(cmd)
        return result[0] == 0

    @staticmethod
    def _nvml_get_val(a_function: Callable, *args: Any) -> Any:
        try:
            return a_function(*args)
        except NVMLError as err:
            if err.value == NVML_ERROR_NOT_SUPPORTED:
                LOG.debug("Function %s not supported" % a_function.__name__)
                return None
            elif err.value == NVML_ERROR_UNKNOWN:
                LOG.warning("Unknown error while executing function %s" % a_function.__name__)
                return None
            else:
                LOG.error("Error value = %d = " % err.value)
                raise err

    # def _get_status_from_py3nvml(self):
    #     py3nvml.nvmlInit()
    #     # print("Driver Version: {}".format(py3nvml.nvmlSystemGetDriverVersion()))
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
    #         # print("Device {}: {}".format(gpu_index, py3nvml.nvmlDeviceGetName(handle)))
    #         # print("UUID {}: {}".format(gpu_index,
    #         #                            gpu.find('py3nvml.nvmlDeviceGetTemperature, handle,
    #         #                                                        NVML_TEMPERATURE_GPU)))
    #
    #         py3nvml.nvmlShutdown()

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
    def _get_power_from_py3nvml(self, handle: Any) -> Power:
        power_con = self._nvml_get_val(py3nvml.nvmlDeviceGetPowerManagementLimitConstraints, handle)
        return Power(
            draw=self._convert_milliwatt_to_watt(self._nvml_get_val(py3nvml.nvmlDeviceGetPowerUsage, handle)),
            limit=self._convert_milliwatt_to_watt(
                self._nvml_get_val(py3nvml.nvmlDeviceGetPowerManagementLimit, handle)),
            default=self._convert_milliwatt_to_watt(
                self._nvml_get_val(py3nvml.nvmlDeviceGetPowerManagementDefaultLimit, handle)),
            minimum=self._convert_milliwatt_to_watt(power_con[0]),
            enforced=self._convert_milliwatt_to_watt(
                self._nvml_get_val(py3nvml.nvmlDeviceGetEnforcedPowerLimit, handle)),
            maximum=self._convert_milliwatt_to_watt(power_con[1])
        )

    @staticmethod
    def _convert_milliwatt_to_watt(milliwatt: Optional[int]) -> float:
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
