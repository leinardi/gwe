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
from typing import Optional

from injector import singleton, inject

from gwe.conf import SETTINGS_DEFAULTS
from gwe.model.setting import Setting


@singleton
class SettingsInteractor:
    @inject
    def __init__(self) -> None:
        pass

    @staticmethod
    def get_bool(key: str, default: Optional[bool] = None) -> bool:
        if default is None:
            default = SETTINGS_DEFAULTS[key]
        setting: Setting = Setting.get_or_none(key=key)
        if setting is not None:
            return bool(setting.value)
        return bool(default)

    @staticmethod
    def set_bool(key: str, value: bool) -> None:
        setting: Setting = Setting.get_or_none(key=key)
        if setting is not None:
            setting.value = value
            setting.save()
        else:
            Setting.create(key=key, value=value)

    @staticmethod
    def get_int(key: str, default: Optional[int] = None) -> int:
        if default is None:
            default = SETTINGS_DEFAULTS[key]
        setting: Setting = Setting.get_or_none(key=key)
        if setting is not None:
            return int(setting.value)
        assert default is not None
        return default

    @staticmethod
    def set_int(key: str, value: int) -> None:
        setting: Setting = Setting.get_or_none(key=key)
        if setting is not None:
            setting.value = value
            setting.save()
        else:
            Setting.create(key=key, value=value)

    @staticmethod
    def get_str(key: str, default: Optional[str] = None) -> str:
        if default is None:
            default = SETTINGS_DEFAULTS[key]
        setting: Setting = Setting.get_or_none(key=key)
        if setting is not None:
            return str(setting.value.decode("utf-8"))
        return str(default)

    @staticmethod
    def set_str(key: str, value: str) -> None:
        setting: Setting = Setting.get_or_none(key=key)
        if setting is not None:
            setting.value = value.encode("utf-8")
            setting.save()
        else:
            Setting.create(key=key, value=value.encode("utf-8"))
