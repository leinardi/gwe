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
from typing import Any

from peewee import CharField, Check, BooleanField, DateTimeField, SQL, SqliteDatabase
from playhouse.signals import Model, post_save, post_delete
from playhouse.sqlite_ext import AutoIncrementField

from gwe.di import INJECTOR, FanProfileChangedSubject
from gwe.model.cb_change import DbChange
from gwe.model.fan_profile_type import FanProfileType

_LOG = logging.getLogger(__name__)
FAN_PROFILE_CHANGED_SUBJECT = INJECTOR.get(FanProfileChangedSubject)


class FanProfile(Model):
    id = AutoIncrementField()
    type = CharField(
        constraints=[Check(f"type='{FanProfileType.AUTO.value}' OR type='{FanProfileType.FAN_CURVE.value}'")],
        default=FanProfileType.FAN_CURVE.value)
    name = CharField()
    read_only = BooleanField(default=False)
    timestamp = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])
    vbios_silent_mode = BooleanField(default=False)

    class Meta:
        legacy_table_names = False
        database = INJECTOR.get(SqliteDatabase)


@post_save(sender=FanProfile)
def on_fan_profile_added(_: Any, profile: FanProfile, created: bool) -> None:
    _LOG.debug("Fan added")
    FAN_PROFILE_CHANGED_SUBJECT.on_next(DbChange(profile, DbChange.INSERT if created else DbChange.UPDATE))


@post_delete(sender=FanProfile)
def on_fan_profile_deleted(_: Any, profile: FanProfile) -> None:
    _LOG.debug("Fan deleted")
    FAN_PROFILE_CHANGED_SUBJECT.on_next(DbChange(profile, DbChange.DELETE))
