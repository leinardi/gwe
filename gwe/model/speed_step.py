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

from peewee import ForeignKeyField, IntegerField, DateTimeField, SQL, SqliteDatabase
from playhouse.signals import Model, post_save, post_delete

from gwe.di import INJECTOR, SpeedStepChangedSubject
from gwe.model.cb_change import DbChange
from gwe.model.fan_profile import FanProfile

_LOG = logging.getLogger(__name__)


class SpeedStep(Model):
    profile = ForeignKeyField(FanProfile, backref='steps')
    temperature = IntegerField()
    duty = IntegerField()
    timestamp = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])

    class Meta:
        legacy_table_names = False
        database = INJECTOR.get(SqliteDatabase)


@post_save(sender=SpeedStep)
def on_speed_step_added(_: Any, step: SpeedStep, created: bool) -> None:
    _LOG.debug("Step added")
    SPEED_STEP_CHANGED_SUBJECT.on_next(DbChange(step, DbChange.INSERT if created else DbChange.UPDATE))


@post_delete(sender=SpeedStep)
def on_speed_step_deleted(_: Any, step: SpeedStep) -> None:
    _LOG.debug("Step deleted")
    SPEED_STEP_CHANGED_SUBJECT.on_next(DbChange(step, DbChange.DELETE))


SPEED_STEP_CHANGED_SUBJECT = INJECTOR.get(SpeedStepChangedSubject)
