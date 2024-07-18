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
import json
import logging
from typing import Optional

import requests
import reactivex
from injector import singleton, inject
from packaging.version import Version
from reactivex import Observable

from gwe.conf import APP_ID, APP_VERSION

_LOG = logging.getLogger(__name__)


@singleton
class CheckNewVersionInteractor:
    URL_PATTERN = 'https://flathub.org/api/v1/apps/{package}'

    @inject
    def __init__(self) -> None:
        pass

    def execute(self) -> Observable:
        _LOG.debug("CheckNewVersionInteractor.execute()")
        return reactivex.defer(lambda _: reactivex.just(self._check_new_version()))

    def _check_new_version(self) -> Optional[Version]:
        req = requests.get(self.URL_PATTERN.format(package=APP_ID))
        version = Version("0")
        if req.status_code == requests.codes.ok:
            j = json.loads(req.text)
            current_release_version = j.get('currentReleaseVersion', "0.0.0")
            version = Version(current_release_version)
        return version if version > Version(APP_VERSION) else None
