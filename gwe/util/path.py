# This file is part of gwe.
#
# Copyright (c) 2018 Roberto Leinardi
#
# gsi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gsi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gsi.  If not, see <http://www.gnu.org/licenses/>.

from pathlib import Path

from xdg import BaseDirectory

from gwe.conf import APP_PACKAGE_NAME

_ROOT: Path = Path(__file__).parent.parent


def get_data_path(path: str) -> str:
    return str(_ROOT.joinpath('data').joinpath(path))


def get_config_path(file: str) -> str:
    return str(Path(BaseDirectory.save_config_path(APP_PACKAGE_NAME)).joinpath(file))
