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
from peewee import ForeignKeyField, DateTimeField, BooleanField, SQL, SqliteDatabase
from playhouse.signals import Model

from gwe.di import INJECTOR
from gwe.model.fan_profile import FanProfile


class CurrentFanProfile(Model):
    profile = ForeignKeyField(FanProfile, unique=True)
    timestamp = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])
    vbios_silent_mode = BooleanField(default=False)

    class Meta:
        legacy_table_names = False
        database = INJECTOR.get(SqliteDatabase)
