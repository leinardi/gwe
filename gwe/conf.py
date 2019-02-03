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
from typing import Dict, Any

APP_PACKAGE_NAME = "gwe"
APP_NAME = "GWE"
APP_ID = "com.leinardi.gwe"
APP_VERSION = "0.6.0"
APP_ICON_NAME = APP_PACKAGE_NAME + ".svg"
APP_DB_NAME = APP_PACKAGE_NAME + ".db"
APP_MAIN_UI_NAME = "main.glade"
APP_EDIT_FAN_PROFILE_UI_NAME = "edit_fan_profile.glade"
APP_PREFERENCES_UI_NAME = "preferences.glade"
APP_DESKTOP_ENTRY_NAME = APP_PACKAGE_NAME + ".desktop"
APP_DESCRIPTION = 'GUI to control cooling and overclock of nVidia cards'
APP_SOURCE_URL = 'https://gitlab.com/leinardi/gwe'
APP_AUTHOR = 'Roberto Leinardi'
APP_AUTHOR_EMAIL = 'roberto@leinardi.com'

MIN_TEMP = 0
MAX_TEMP = 100
FAN_MIN_DUTY = 0
FAN_MAX_DUTY = 100

SETTINGS_DEFAULTS: Dict[str, Any] = {
    'settings_launch_on_login': False,
    'settings_load_last_profile': True,
    'settings_refresh_interval': 3,
    'settings_show_app_indicator': True,
    'settings_app_indicator_show_gpu_temp': True,
}

DESKTOP_ENTRY: Dict[str, str] = {
    'Type': 'Application',
    'Encoding': 'UTF-8',
    'Name': APP_NAME,
    'Comment': APP_DESCRIPTION,
    'Terminal': 'false',
    'Categories': 'System;Settings;',
}
