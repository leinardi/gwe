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
from typing import Any

from peewee import CharField, BlobField, SqliteDatabase
from playhouse.signals import Model, post_save, post_delete

from gwe.di import INJECTOR, SettingChangedSubject
from gwe.model.cb_change import DbChange


class Setting(Model):
    key = CharField(primary_key=True)
    value = BlobField()

    class Meta:
        legacy_table_names = False
        database = INJECTOR.get(SqliteDatabase)


@post_save(sender=Setting)
def on_speed_step_added(_: Any, step: Setting, created: bool) -> None:
    SPEED_STEP_CHANGED_SUBJECT.on_next(DbChange(step, DbChange.INSERT if created else DbChange.UPDATE))


@post_delete(sender=Setting)
def on_speed_step_deleted(_: Any, step: Setting) -> None:
    SPEED_STEP_CHANGED_SUBJECT.on_next(DbChange(step, DbChange.DELETE))


SPEED_STEP_CHANGED_SUBJECT = INJECTOR.get(SettingChangedSubject)
