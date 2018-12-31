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

# pylint: disable=too-many-locals,too-many-instance-attributes
import logging
from typing import Optional, Any, Tuple, List

from playhouse.signals import Model, post_save, post_delete
from playhouse.sqlite_ext import AutoIncrementField
from peewee import CharField, DateTimeField, SqliteDatabase, SQL, IntegerField, Check, \
    ForeignKeyField, BooleanField, BlobField

from gwe.di import INJECTOR, SpeedProfileChangedSubject, SpeedStepChangedSubject

LOG = logging.getLogger(__name__)
SPEED_PROFILE_CHANGED_SUBJECT = INJECTOR.get(SpeedProfileChangedSubject)
SPEED_STEP_CHANGED_SUBJECT = INJECTOR.get(SpeedStepChangedSubject)


class Info:
    def __init__(self,
                 name: str,
                 vbios: str,
                 driver: str,
                 pcie: str,
                 cuda_cores: str,
                 uuid: str,
                 memory_size: str,
                 memory_interface: str,
                 memory_usage: str,
                 gpu_usage: str,
                 encoder_usage: str,
                 decoder_usage: str
                 ) -> None:
        self.name: str = name
        self.vbios: str = vbios
        self.driver: str = driver
        self.pcie: str = pcie
        self.cuda_cores: str = cuda_cores
        self.uuid: str = uuid
        self.memory_size: str = memory_size
        self.memory_interface: str = memory_interface
        self.memory_usage: str = memory_usage
        self.gpu_usage: str = gpu_usage
        self.encoder_usage: str = encoder_usage
        self.decoder_usage: str = decoder_usage


class Power:
    def __init__(self,
                 draw: str,
                 limit: str,
                 default: str,
                 minimum: str,
                 enforced: str,
                 maximum: str
                 ) -> None:
        self.draw: str = draw
        self.limit: str = limit
        self.default: str = default
        self.minimum: str = minimum
        self.enforced: str = enforced
        self.maximum: str = maximum


class Temp:
    def __init__(self,
                 gpu: str,
                 maximum: str,
                 slowdown: str,
                 shutdown: str
                 ) -> None:
        self.gpu: str = gpu
        self.maximum: str = maximum
        self.slowdown: str = slowdown
        self.shutdown: str = shutdown


class Fan:
    def __init__(self,
                 fan_list: List[Tuple[int, int]]
                 ) -> None:
        self.fan_list = fan_list


class Clocks:
    def __init__(self,
                 graphic_current: str,
                 graphic_max: str,
                 sm_current: str,
                 sm_max: str,
                 memory_current: str,
                 memory_max: str,
                 video_current: str,
                 video_max: str
                 ) -> None:
        self.graphic_current: str = graphic_current
        self.graphic_max: str = graphic_max
        self.sm_current: str = sm_current
        self.sm_max: str = sm_max
        self.memory_current: str = memory_current
        self.memory_max: str = memory_max
        self.video_current: str = video_current
        self.video_max: str = video_max


class Overclock:
    def __init__(self,
                 available: bool,
                 gpu_range: Tuple[int, int],
                 gpu_offset: int,
                 memory_range: Tuple[int, int],
                 memory_offset: int) -> None:
        self.available = available
        self.gpu_range = gpu_range
        self.gpu_offset = gpu_offset
        self.memory_range = memory_range
        self.memory_offset = memory_offset


class GpuStatus:
    def __init__(self,
                 gpu_id: str,
                 info: Info,
                 power: Power,
                 temp: Temp,
                 fan: Fan,
                 clocks: Clocks,
                 overclock: Overclock
                 ) -> None:
        self.gpu_id = gpu_id
        self.info = info
        self.power = power
        self.temp = temp
        self.fan = fan
        self.clocks = clocks
        self.overclock = overclock


class Status:
    def __init__(self,
                 gpu_status_list: List[GpuStatus]
                 ) -> None:
        self.gpu_status_list = gpu_status_list


class DbChange:
    INSERT = 0
    DELETE = 1
    UPDATE = 2

    def __init__(self, entry: Any, cahnge_type: int) -> None:
        self.entry: Any = entry
        self.type: int = cahnge_type


class SpeedProfile(Model):
    id = AutoIncrementField()
    name = CharField()
    read_only = BooleanField(default=False)
    single_step = BooleanField(default=False)
    timestamp = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])

    class Meta:
        legacy_table_names = False
        database = INJECTOR.get(SqliteDatabase)


@post_save(sender=SpeedProfile)
def on_speed_profile_added(_: Any, profile: SpeedProfile, created: bool) -> None:
    LOG.debug("Profile added")
    SPEED_PROFILE_CHANGED_SUBJECT.on_next(DbChange(profile, DbChange.INSERT if created else DbChange.UPDATE))


@post_delete(sender=SpeedProfile)
def on_speed_profile_deleted(_: Any, profile: SpeedProfile) -> None:
    LOG.debug("Profile deleted")
    SPEED_PROFILE_CHANGED_SUBJECT.on_next(DbChange(profile, DbChange.DELETE))


class SpeedStep(Model):
    profile = ForeignKeyField(SpeedProfile, backref='steps')
    temperature = IntegerField()
    duty = IntegerField()
    timestamp = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])

    class Meta:
        legacy_table_names = False
        database = INJECTOR.get(SqliteDatabase)


@post_save(sender=SpeedStep)
def on_speed_step_added(_: Any, step: SpeedStep, created: bool) -> None:
    LOG.debug("Profile added")
    SPEED_STEP_CHANGED_SUBJECT.on_next(DbChange(step, DbChange.INSERT if created else DbChange.UPDATE))


@post_delete(sender=SpeedStep)
def on_speed_step_deleted(_: Any, step: SpeedStep) -> None:
    LOG.debug("Step deleted")
    SPEED_STEP_CHANGED_SUBJECT.on_next(DbChange(step, DbChange.DELETE))


class CurrentSpeedProfile(Model):
    profile = ForeignKeyField(SpeedProfile, unique=True)
    timestamp = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])

    class Meta:
        legacy_table_names = False
        database = INJECTOR.get(SqliteDatabase)


class Setting(Model):
    key = CharField(primary_key=True)
    value = BlobField()

    class Meta:
        legacy_table_names = False
        database = INJECTOR.get(SqliteDatabase)


def load_db_default_data() -> None:
    fan_silent = SpeedProfile.create(name="Silent", read_only=True)
    fan_perf = SpeedProfile.create(name="Performance", read_only=True)

    # Fan Silent
    SpeedStep.create(profile=fan_silent.id, temperature=20, duty=0)
    SpeedStep.create(profile=fan_silent.id, temperature=30, duty=25)
    SpeedStep.create(profile=fan_silent.id, temperature=40, duty=45)
    SpeedStep.create(profile=fan_silent.id, temperature=50, duty=55)
    SpeedStep.create(profile=fan_silent.id, temperature=55, duty=60)
    SpeedStep.create(profile=fan_silent.id, temperature=60, duty=65)
    SpeedStep.create(profile=fan_silent.id, temperature=65, duty=70)
    SpeedStep.create(profile=fan_silent.id, temperature=68, duty=80)
    SpeedStep.create(profile=fan_silent.id, temperature=70, duty=90)
    SpeedStep.create(profile=fan_silent.id, temperature=75, duty=100)

    # Fan Performance
    SpeedStep.create(profile=fan_perf.id, temperature=20, duty=50)
    SpeedStep.create(profile=fan_perf.id, temperature=35, duty=50)
    SpeedStep.create(profile=fan_perf.id, temperature=60, duty=100)
