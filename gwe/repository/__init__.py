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
import subprocess
from typing import List, Tuple

from gwe.util.deployment import is_flatpak

_FLATPAK_COMMAND_PREFIX = ['flatpak-spawn', '--host']


def run_and_get_stdout(command: List[str], pipe_command: List[str] = None) -> Tuple[int, str, str]:
    if pipe_command is None:
        if is_flatpak():
            command = _FLATPAK_COMMAND_PREFIX + command
        process1 = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        output, error = process1.communicate()
        return process1.returncode, output.decode(encoding='UTF-8').strip(), error.decode(encoding='UTF-8').strip()
    if is_flatpak():
        command = _FLATPAK_COMMAND_PREFIX + command
        pipe_command = _FLATPAK_COMMAND_PREFIX + pipe_command
    process1 = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    process2 = subprocess.Popen(pipe_command, stdin=process1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process1.stdout.close()
    output, error = process1.communicate()
    return process2.returncode, output.decode(encoding='UTF-8').strip(), error.decode(encoding='UTF-8').strip()
