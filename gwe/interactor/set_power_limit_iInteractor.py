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

import reactivex
from injector import singleton, inject
from reactivex import Observable

from gwe.repository.nvidia_repository import NvidiaRepository

_LOG = logging.getLogger(__name__)


@singleton
class SetPowerLimitInteractor:
    @inject
    def __init__(self, nvidia_repository: NvidiaRepository, ) -> None:
        self._nvidia_repository = nvidia_repository

    def execute(self, gpu_index: int, limit: int) -> Observable:
        _LOG.debug("SetPowerLimitInteractor.execute()")
        return reactivex.defer(lambda _: reactivex.just(self._nvidia_repository.set_power_limit(gpu_index, limit)))
