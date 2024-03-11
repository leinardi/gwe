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

from peewee import IntegerField, SqliteDatabase
from playhouse.signals import Model, post_save

from gwe.di import INJECTOR, GPUAttributesChangedSubject
from gwe.model.cb_change import DbChange

_LOG = logging.getLogger(__name__)
GPU_ATTRIBUTES_CHANGED_SUBJECT = INJECTOR.get(GPUAttributesChangedSubject)


class GPUAttributes(Model):
    gpu = IntegerField(default=-1)
    persistence_mode = IntegerField(default=-1)
    power_limit = IntegerField(default=-1)

    class Meta:
        legacy_table_names = False
        database = INJECTOR.get(SqliteDatabase)


@post_save(sender=GPUAttributes)
def on_gpu_attributes_added(_: Any, profile: GPUAttributes, created: bool) -> None:
    _LOG.debug("GPU attributes saved")
    GPU_ATTRIBUTES_CHANGED_SUBJECT.on_next(DbChange(profile, DbChange.INSERT if created else DbChange.UPDATE))
