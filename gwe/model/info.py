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
from typing import Optional


class Info:
    def __init__(self,
                 name: Optional[str] = None,
                 vbios: Optional[str] = None,
                 driver: Optional[str] = None,
                 pcie_current_generation: Optional[int] = None,
                 pcie_max_generation: Optional[int] = None,
                 pcie_current_link: Optional[int] = None,
                 pcie_max_link: Optional[int] = None,
                 cuda_cores: Optional[int] = None,
                 uuid: Optional[str] = None,
                 memory_total: Optional[int] = None,
                 memory_used: Optional[int] = None,
                 memory_interface: Optional[int] = None,
                 memory_usage: Optional[int] = None,
                 gpu_usage: Optional[int] = None,
                 encoder_usage: Optional[int] = None,
                 decoder_usage: Optional[int] = None
                 ) -> None:
        self.name: Optional[str] = name
        self.vbios: Optional[str] = vbios
        self.driver: Optional[str] = driver
        self.pcie_current_generation: Optional[int] = pcie_current_generation
        self.pcie_max_generation: Optional[int] = pcie_max_generation
        self.pcie_current_link: Optional[int] = pcie_current_link
        self.pcie_max_link: Optional[int] = pcie_max_link
        self.cuda_cores: Optional[int] = cuda_cores
        self.uuid: Optional[str] = uuid
        self.memory_total: Optional[int] = memory_total
        self.memory_used: Optional[int] = memory_used
        self.memory_interface: Optional[int] = memory_interface
        self.memory_usage: Optional[int] = memory_usage
        self.gpu_usage: Optional[int] = gpu_usage
        self.encoder_usage: Optional[int] = encoder_usage
        self.decoder_usage: Optional[int] = decoder_usage
