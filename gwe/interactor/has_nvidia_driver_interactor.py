# This file is part of gwe.
#
# Copyright (c) 2020 Roberto Leinardi
#
# gwe is free software: you can redistribute it and/or modify
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
import os
from enum import Enum, auto

import reactivex
from injector import singleton, inject
from reactivex import Observable

from gwe.repository.nvidia_repository import NvidiaRepository


class HasNvidiaDriverResult(Enum):
    POSITIVE = auto()
    NV_CONTROL_MISSING = auto()
    NVML_MISSING = auto()
    DRIVER_VERSION_ERROR = auto()


@singleton
class HasNvidiaDriverInteractor:
    @inject
    def __init__(self, nvidia_repository: NvidiaRepository, ) -> None:
        self._nvidia_repository = nvidia_repository

    def execute(self) -> Observable:
        return reactivex.defer(lambda _: reactivex.just(self._has_nvidia_driver()))

    def _has_nvidia_driver(self) -> HasNvidiaDriverResult:
        if not self._nvidia_repository.has_nvml_shared_library():
            return HasNvidiaDriverResult.NVML_MISSING
        if 'WAYLAND_DISPLAY' not in os.environ and not self._nvidia_repository.has_nv_control_extension():
            return HasNvidiaDriverResult.NV_CONTROL_MISSING
        if not self._nvidia_repository.has_min_driver_version():
            return HasNvidiaDriverResult.DRIVER_VERSION_ERROR
        return HasNvidiaDriverResult.POSITIVE
