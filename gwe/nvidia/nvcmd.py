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
import struct
from typing import Optional, Dict, List, Tuple

from gwe.nvidia.minx import XFORMATS, XFORMATBYTES
from gwe.nvidia.nvctrl import NVidiaControlLowLevel, NV_CTRL_BUS_TYPE, NV_CTRL_OPERATING_SYSTEM, NV_CTRL_ARCHITECTURE, \
    NV_CTRL_VIDEO_RAM, NV_CTRL_IRQ, NV_CTRL_CONNECTED_DISPLAYS, NV_CTRL_ENABLED_DISPLAYS, NV_CTRL_FRAMELOCK, \
    NV_CTRL_STRING_PRODUCT_NAME, NV_CTRL_STRING_NVIDIA_DRIVER_VERSION, NV_CTRL_STRING_VBIOS_VERSION, \
    NV_CTRL_GVO_SUPPORTED, NV_CTRL_GPU_CORE_TEMPERATURE, NV_CTRL_GPU_CORE_THRESHOLD, \
    NV_CTRL_GPU_DEFAULT_CORE_THRESHOLD, NV_CTRL_GPU_MAX_CORE_THRESHOLD, NV_CTRL_AMBIENT_TEMPERATURE, \
    NV_CTRL_GPU_CURRENT_CLOCK_FREQS, NV_CTRL_GPU_CORES, NV_CTRL_GPU_MEMORY_BUS_WIDTH, \
    NV_CTRL_TOTAL_DEDICATED_GPU_MEMORY, NV_CTRL_USED_DEDICATED_GPU_MEMORY, NV_CTRL_GPU_PCIE_CURRENT_LINK_WIDTH, \
    NV_CTRL_GPU_PCIE_GENERATION, NV_CTRL_STRING_GPU_UUID, NV_CTRL_STRING_GPU_UTILIZATION, \
    NV_CTRL_VIDEO_ENCODER_UTILIZATION, NV_CTRL_VIDEO_DECODER_UTILIZATION, NV_CTRL_STRING_PERFORMANCE_MODES, \
    NV_CTRL_GPU_NVCLOCK_OFFSET, NV_CTRL_GPU_MEM_TRANSFER_RATE_OFFSET, NV_CTRL_THERMAL_COOLER_CURRENT_LEVEL, \
    NV_CTRL_THERMAL_COOLER_SPEED, NV_CTRL_GPU_COOLER_MANUAL_CONTROL, NV_CTRL_XINERAMA, NV_CTRL_MAX_DISPLAYS, \
    NV_CTRL_PROBE_DISPLAYS, NV_CTRL_GPU_PCIE_MAX_LINK_WIDTH, NV_CTRL_GPU_CURRENT_PERFORMANCE_LEVEL, \
    NV_CTRL_BINARY_DATA_COOLERS_USED_BY_GPU
from gwe.nvidia.nvtarget import GPU, Target, Screen

_BUS_TYPES: List[str] = ['AGP', 'PCI', 'PCI Express', 'Integrated']
_OS_TYPES: List[str] = ['Linux', 'FreeBSD', 'SunOS']
_ARCH_TYPES: List[str] = ['x86', 'x86-64', 'IA64']


class NVidiaControl(NVidiaControlLowLevel):
    """This class extends nvctrl.NVidiaControlLowLevel with methods for
    accessing the NV-CONTROL functions on a higher level."""

    def get_gpu_count(self) -> Optional[int]:
        """Return the number of GPU's present in the system."""
        reply = self.query_target_count(GPU())
        return int(reply.count)

    def get_bus_type(self, target: Target) -> Optional[str]:
        """Return the bus type through which the GPU driving the specified X
        screen is connected to the computer."""
        reply = self.query_int_attribute(target, [], NV_CTRL_BUS_TYPE)
        if not reply.flags:
            return None
        return str(_BUS_TYPES[reply.value])

    def get_os_type(self) -> Optional[str]:
        """return the operating system on which the X server is running."""
        reply = self.query_int_attribute(GPU(), [], NV_CTRL_OPERATING_SYSTEM)
        if not reply.flags:
            return None
        return str(_OS_TYPES[reply.value])

    def get_host_architecture(self) -> Optional[str]:
        """return the architecture on which the X server is running."""
        reply = self.query_int_attribute(GPU(), [], NV_CTRL_ARCHITECTURE)
        if not reply.flags:
            return None
        return str(_ARCH_TYPES[reply.value])

    def get_vram(self, target: Target) -> Optional[int]:
        """Return the total amount of memory available to the specified GPU
        (or the GPU driving the specified X screen). Note: if the GPU supports
        TurboCache(TM), the value reported may exceed the amount of video
        memory installed on the GPU. The value reported for integrated GPUs may
        likewise exceed the amount of dedicated system memory set aside by the
        system BIOS for use by the integrated GPU."""
        reply = self.query_int_attribute(target, [], NV_CTRL_VIDEO_RAM)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_irq(self, target: Target) -> Optional[int]:
        """Return the interrupt request line used by the GPU driving the screen"""
        reply = self.query_int_attribute(target, [], NV_CTRL_IRQ)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_connected_displays(self, target: Target) -> Optional[List[str]]:
        """Return an array with connected display numbers"""
        reply = self.query_int_attribute(target, [], NV_CTRL_CONNECTED_DISPLAYS)
        if not reply.flags:
            return None
        return self.mask2displays(reply.value)

    def get_enabled_displays(self, target: Target) -> Optional[List[str]]:
        """returns an array of displays that are enabled on the specified X
        screen or GPU."""
        reply = self.query_int_attribute(target, [], NV_CTRL_ENABLED_DISPLAYS)
        if not reply.flags:
            return None
        return self.mask2displays(reply.value)

    def supports_framelock(self, target: Target) -> Optional[bool]:
        """returns whether the underlying GPU supports Frame Lock. All of the
        other frame lock attributes are only applicable if this returns True."""
        reply = self.query_int_attribute(target, [], NV_CTRL_FRAMELOCK)
        if not reply.flags:
            return None
        return int(reply.value) == 1

    def get_name(self, target: Target) -> Optional[str]:
        """the GPU product name on which the specified X screen is running"""
        reply = self.query_string_attribute(target, [], NV_CTRL_STRING_PRODUCT_NAME)
        if not reply.flags:
            return None
        return str(reply.string)

    def get_driver_version(self, target: Target) -> Optional[str]:
        """the NVIDIA (kernel level) driver version for the specified screen or GPU"""
        reply = self.query_string_attribute(target, [], NV_CTRL_STRING_NVIDIA_DRIVER_VERSION)
        if not reply.flags:
            return None
        return str(reply.string)

    def get_vbios_version(self, target: Target) -> Optional[str]:
        """the version of the VBIOS for the specified screen or GPU"""
        reply = self.query_string_attribute(target, [], NV_CTRL_STRING_VBIOS_VERSION)
        if not reply.flags:
            return None
        return str(reply.string)

    def gvo_supported(self, screen: Screen) -> Optional[int]:
        """returns whether this X screen supports GVO; if this screen does not
        support GVO output, then all other GVO attributes are unavailable."""
        reply = self.query_int_attribute(screen, [], NV_CTRL_GVO_SUPPORTED)
        if not reply.flags:
            return None
        return int(reply.value) == 1

    def get_core_temp(self, target: Target) -> Optional[int]:
        """return the current core temperature of the GPU driving the X screen."""
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_CORE_TEMPERATURE)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_core_threshold(self, target: Target) -> Optional[int]:
        """return the current GPU core slowdown threshold temperature. It
        reflects the temperature at which the GPU is throttled to prevent
        overheating."""
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_CORE_THRESHOLD)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_default_core_threshold(self, target: Target) -> Optional[int]:
        """return the default core threshold temperature."""
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_DEFAULT_CORE_THRESHOLD)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_max_core_threshold(self, target: Target) -> Optional[int]:
        """return the maximum core threshold temperature."""
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_MAX_CORE_THRESHOLD)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_ambient_temp(self, target: Target) -> Optional[int]:
        """return the current temperature in the immediate neighbourhood of
        the GPU driving the X screen."""
        reply = self.query_int_attribute(target, [], NV_CTRL_AMBIENT_TEMPERATURE)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_current_clocks(self, target: Target) -> Optional[Tuple[int, int]]:
        """return the current (GPU, memory) clocks of the graphics device
        driving the X screen."""
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_CURRENT_CLOCK_FREQS)
        if not reply.flags:
            return None
        return int(reply.value) >> 16, reply.value & 0xFFFF

    def get_cuda_cores(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_CORES)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_memory_bus_width(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_MEMORY_BUS_WIDTH)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_total_dedicated_gpu_memory(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_TOTAL_DEDICATED_GPU_MEMORY)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_used_dedicated_gpu_memory(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_USED_DEDICATED_GPU_MEMORY)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_pcie_current_link_width(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_PCIE_CURRENT_LINK_WIDTH)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_pcie_max_link_width(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_PCIE_MAX_LINK_WIDTH)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_pcie_generation(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_PCIE_GENERATION)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_gpu_uuid(self, target: Target) -> Optional[str]:
        reply = self.query_string_attribute(target, [], NV_CTRL_STRING_GPU_UUID)
        if not reply.flags:
            return None
        return str(reply.string)

    def get_gpu_utilization(self, target: Target) -> Dict[str, int]:
        reply = None
        for i in range(10):
            reply = self.query_string_attribute(target, [], NV_CTRL_STRING_GPU_UTILIZATION)
            if not reply.flags:
                return {}
            if reply.string != '':
                break
            # TODO Log error
        result = {}
        if reply and reply.string and reply.string != '':
            for line in reply.string.split(','):
                key_value = line.split('=')
                result[key_value[0].strip()] = int(key_value[1]) if key_value[1].isdigit else key_value[1]
        return result

    def get_video_encoder_utilization(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_VIDEO_ENCODER_UTILIZATION)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_video_decoder_utilization(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_VIDEO_DECODER_UTILIZATION)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_current_performance_level(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_CURRENT_PERFORMANCE_LEVEL)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_performance_modes(self, target: Target) -> Optional[List[Dict[str, int]]]:
        reply = None
        for i in range(3):
            reply = self.query_string_attribute(target, [], NV_CTRL_STRING_PERFORMANCE_MODES)
            if not reply.flags:
                return None
            if reply.string != '':
                break
            # TODO Log error
        result = []
        if reply and reply.string and reply.string != '':
            for perf in reply.string.split(';'):
                perf_dict = {}
                for line in perf.split(','):
                    key_value = line.split('=')
                    perf_dict[key_value[0].strip()] = int(key_value[1]) if key_value[1].isdigit else key_value[1]
                result.append(perf_dict)
        return result

    def get_gpu_nvclock_offset(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_NVCLOCK_OFFSET)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_gpu_nvclock_offset_range(self, target: Target) -> Optional[Tuple[int, int]]:
        reply = self.query_valid_attr_values(target, [], NV_CTRL_GPU_NVCLOCK_OFFSET)
        if not reply.flags:
            return None
        return reply.min, reply.max

    def get_mem_transfer_rate_offset(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_MEM_TRANSFER_RATE_OFFSET)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_mem_transfer_rate_offset_range(self, target: Target) -> Optional[Tuple[int, int]]:
        reply = self.query_valid_attr_values(target, [], NV_CTRL_GPU_MEM_TRANSFER_RATE_OFFSET)
        if not reply.flags:
            return None
        return reply.min, reply.max

    def get_fan_duty(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_THERMAL_COOLER_CURRENT_LEVEL)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_fan_rpm(self, target: Target) -> Optional[int]:
        reply = self.query_int_attribute(target, [], NV_CTRL_THERMAL_COOLER_SPEED)
        if not reply.flags:
            return None
        return int(reply.value)

    def get_cooler_manual_control_enabled(self, target: Target) -> Optional[bool]:
        reply = self.query_int_attribute(target, [], NV_CTRL_GPU_COOLER_MANUAL_CONTROL)
        if not reply.flags:
            return None
        return int(reply.value) == 1

    def get_coolers_used_by_gpu(self, target: Target) -> Optional[Tuple]:
        reply = self.query_binary_data(target, [], NV_CTRL_BINARY_DATA_COOLERS_USED_BY_GPU)
        if not reply.flags:
            return None
        structcode = XFORMATS['CARD32']
        format_size = XFORMATBYTES['CARD32']
        size = len(reply.data) // format_size
        structcode = str(size) + structcode
        fans = struct.unpack(structcode, reply.data)
        if len(fans) > 1:
            return fans[1:]
        else:
            return None

    def get_xinerama_enabled(self, target: Target) -> Optional[bool]:
        """return whether Xinerama is enabled or not"""
        reply = self.query_int_attribute(target, [], NV_CTRL_XINERAMA)
        if not reply.flags:
            return None
        return int(reply.value) == 1

    def get_max_displays(self, target: Target) -> Optional[int]:
        """return the maximum number of display devices that can be driven
        simultaneously on a GPU (e.g., that can be used in a MetaMode at once).
        Note that this does not indicate the maximum number of bits that can be
        set in NV_CTRL_CONNECTED_DISPLAYS, because more display devices can be
        connected than are actively in use."""
        res = self.query_int_attribute(target, [], NV_CTRL_MAX_DISPLAYS)
        if not res.flags:
            return None
        return int(res.value)

    def probe_displays(self, target: Target) -> Optional[List[str]]:
        """re-probes the hardware to detect what display devices are connected
        to the GPU or GPU driving the specified X screen. Returns an array
        of displays."""
        reply = self.query_int_attribute(target, [], NV_CTRL_PROBE_DISPLAYS)
        if not reply.flags:
            return None
        return self.mask2displays(reply.value)
