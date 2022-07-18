# This file is part of gst.
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
from gwe.model.fan_profile import FanProfile
from gwe.model.fan_profile_type import FanProfileType
from gwe.model.overclock_profile import OverclockProfile
from gwe.model.overclock_profile_type import OverclockProfileType
from gwe.model.speed_step import SpeedStep


def load_fan_db_default_data() -> None:
    FanProfile.create(name="Auto (VBIOS controlled)", type=FanProfileType.AUTO.value, read_only=True, vbios_silent_mode=False)
    fan_silent = FanProfile.create(name="Custom")

    # Fan Silent
    SpeedStep.create(profile=fan_silent.id, temperature=20, duty=0)
    SpeedStep.create(profile=fan_silent.id, temperature=30, duty=25)
    SpeedStep.create(profile=fan_silent.id, temperature=40, duty=45)
    SpeedStep.create(profile=fan_silent.id, temperature=65, duty=70)
    SpeedStep.create(profile=fan_silent.id, temperature=70, duty=90)
    SpeedStep.create(profile=fan_silent.id, temperature=75, duty=100)


def load_overclock_db_default_data() -> None:
    OverclockProfile.create(type=OverclockProfileType.DEFAULT.value, name="Default", gpu=0, memory=0, read_only=True)
