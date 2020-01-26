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

from peewee import CharField, Check, IntegerField, BooleanField, DateTimeField, SQL, SqliteDatabase
from playhouse.signals import Model, post_save, post_delete
from playhouse.sqlite_ext import AutoIncrementField

from gwe.di import INJECTOR, OverclockProfileChangedSubject
from gwe.model.cb_change import DbChange
from gwe.model.overclock_profile_type import OverclockProfileType

LOG = logging.getLogger(__name__)
OVERCLOCK_PROFILE_CHANGED_SUBJECT = INJECTOR.get(OverclockProfileChangedSubject)


class OverclockProfile(Model):
    id = AutoIncrementField()
    type = CharField(
        constraints=[Check(f"type='{OverclockProfileType.DEFAULT.value}' "
                           f"OR type='{OverclockProfileType.OFFSET.value}'")],
        default=OverclockProfileType.OFFSET.value)
    name = CharField()
    gpu = IntegerField(default=0)
    memory = IntegerField(default=0)
    read_only = BooleanField(default=False)
    timestamp = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])

    class Meta:
        legacy_table_names = False
        database = INJECTOR.get(SqliteDatabase)


@post_save(sender=OverclockProfile)
def on_overclock_profile_added(_: Any, profile: OverclockProfile, created: bool) -> None:
    LOG.debug("Overclock added")
    OVERCLOCK_PROFILE_CHANGED_SUBJECT.on_next(DbChange(profile, DbChange.INSERT if created else DbChange.UPDATE))


@post_delete(sender=OverclockProfile)
def on_overclock_profile_deleted(_: Any, profile: OverclockProfile) -> None:
    LOG.debug("Overclock deleted")
    OVERCLOCK_PROFILE_CHANGED_SUBJECT.on_next(DbChange(profile, DbChange.DELETE))
