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

import os
import shutil
import subprocess
from pathlib import Path

from gwe.util.log import LOG
from gwe.util.path import get_data_path

UDEV_RULES_DIR = '/lib/udev/rules.d/'
UDEV_RULE_FILE_NAME = '60-gwe.rules'


def add_udev_rule() -> int:
    if os.geteuid() == 0:
        if not os.path.isdir(UDEV_RULES_DIR):
            LOG.error("Udev rules have not been added (%s is not a directory)", UDEV_RULES_DIR)
            return 1
        try:
            shutil.copy(get_data_path(UDEV_RULE_FILE_NAME), UDEV_RULES_DIR)
        except IOError:
            LOG.exception("Unable to add udev rule")
            return 1
        try:
            subprocess.call(["udevadm", "control", "--reload-rules"])
            subprocess.call(["udevadm", "trigger", "--subsystem-match=usb", "--attr-match=idVendor=1e71",
                             "--action=add"])
        except OSError:
            LOG.exception("unable to update udev rules (to apply the new rule a reboot may be needed)")
            return 1
        LOG.info("Rule added")
        return 0

    LOG.error("You must have root privileges to modify udev rules. Run this command again using sudo.")
    return 1


def remove_udev_rule() -> int:
    if os.geteuid() == 0:
        path = Path(UDEV_RULES_DIR).joinpath(UDEV_RULE_FILE_NAME)
        if not path.is_file():
            LOG.error("Unable to add udev rule (file %s not found)", str(path))
            return 1
        try:
            path.unlink()
        except IOError:
            LOG.exception("Unable to add udev rule")
            return 1
        try:
            subprocess.call(["udevadm", "control", "--reload-rules"])
            subprocess.call(["udevadm", "trigger", "--subsystem-match=usb", "--attr-match=idVendor=1e71",
                             "--action=add"])
        except OSError:
            LOG.exception("unable to update udev rules (to apply the new rule a reboot may be needed)")
            return 1
        LOG.info("Rule removed")
        return 0

    LOG.error("You must have root privileges to modify udev rules. Run this command again using sudo.")
    return 1
