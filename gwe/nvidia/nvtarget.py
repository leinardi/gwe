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

############################################################################

#
# Attribute Targets
#
# Targets define attribute groups.  For example, some attributes are only
# valid to set on a GPU, others are only valid when talking about an
# X Screen.  Target types are then what is used to identify the target
# group of the attribute you wish to set/query.
#
# Here are the supported target types:
#

NV_CTRL_TARGET_TYPE_X_SCREEN = 0
NV_CTRL_TARGET_TYPE_GPU = 1
NV_CTRL_TARGET_TYPE_FRAMELOCK = 2
# Visual Computing System - deprecated.  To be removed along with all
# VCS-specific attributes in a later release.
NV_CTRL_TARGET_TYPE_VCSC = 3
NV_CTRL_TARGET_TYPE_GVI = 4
NV_CTRL_TARGET_TYPE_COOLER = 5  # e.g., fan
NV_CTRL_TARGET_TYPE_THERMAL_SENSOR = 6
NV_CTRL_TARGET_TYPE_3D_VISION_PRO_TRANSCEIVER = 7
NV_CTRL_TARGET_TYPE_DISPLAY = 8


###############################################################################
# Targets, to indicate where a command should be executed.
#
class Target:
    def __init__(self) -> None:
        self._id = -1
        self._type = -1
        self._name = ''

    def id(self) -> int:
        return self._id

    def type(self) -> int:
        return self._type

    def __str__(self) -> str:
        return '<nVidia %s #%d>' % (self._name, self.id())


class GPU(Target):
    def __init__(self, ngpu: int = 0) -> None:
        """Target a GPU"""
        super().__init__()
        self._id = ngpu
        self._type = NV_CTRL_TARGET_TYPE_GPU
        self._name = 'GPU'


class Screen(Target):
    def __init__(self, nscr: int = 0) -> None:
        """Target an X screen"""
        super().__init__()
        self._id = nscr
        self._type = NV_CTRL_TARGET_TYPE_X_SCREEN
        self._name = 'X screen'


class Cooler(Target):
    def __init__(self, nfan: int = 0) -> None:
        """Target a fann"""
        super().__init__()
        self._id = nfan
        self._type = NV_CTRL_TARGET_TYPE_COOLER
        self._name = 'Cooler'
