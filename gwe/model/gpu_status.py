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
from gwe.model.clocks import Clocks
from gwe.model.fan import Fan
from gwe.model.info import Info
from gwe.model.overclock import Overclock
from gwe.model.power import Power
from gwe.model.temp import Temp


class GpuStatus:
    def __init__(self,
                 index: int,
                 info: Info,
                 power: Power,
                 temp: Temp,
                 fan: Fan,
                 clocks: Clocks,
                 overclock: Overclock
                 ) -> None:
        self.index = index
        self.info = info
        self.power = power
        self.temp = temp
        self.fan = fan
        self.clocks = clocks
        self.overclock = overclock
