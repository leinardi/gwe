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
from enum import Enum
from typing import Optional, Any, Tuple, List

from playhouse.signals import Model, post_save, post_delete
from playhouse.sqlite_ext import AutoIncrementField
from peewee import CharField, DateTimeField, SqliteDatabase, SQL, IntegerField, Check, \
    ForeignKeyField, BooleanField, BlobField

from gwe.di import INJECTOR, FanProfileChangedSubject, SpeedStepChangedSubject

LOG = logging.getLogger(__name__)
FAN_PROFILE_CHANGED_SUBJECT = INJECTOR.get(FanProfileChangedSubject)
SPEED_STEP_CHANGED_SUBJECT = INJECTOR.get(SpeedStepChangedSubject)


class Info:
    def __init__(self,
                 name: Optional[str] = None,
                 vbios: Optional[str] = None,
                 driver: Optional[str] = None,
                 pcie_generation: Optional[int] = None,
                 pcie_current_link: Optional[int] = None,
                 pcie_max_link: Optional[int] = None,
                 cuda_cores: Optional[int] = None,
                 uuid: Optional[str] = None,
                 memory_total: Optional[int] = None,
                 memory_used: Optional[int] = None,
                 memory_interface: Optional[int] = None,
                 memory_usage: Optional[int] = None,
                 gpu_usage: Optional[int] = None,
                 encoder_usage: Optional[int] = None,
                 decoder_usage: Optional[int] = None
                 ) -> None:
        self.name: Optional[str] = name
        self.vbios: Optional[str] = vbios
        self.driver: Optional[str] = driver
        self.pcie_generation: Optional[int] = pcie_generation
        self.pcie_current_link: Optional[int] = pcie_current_link
        self.pcie_max_link: Optional[int] = pcie_max_link
        self.cuda_cores: Optional[int] = cuda_cores
        self.uuid: Optional[str] = uuid
        self.memory_total: Optional[int] = memory_total
        self.memory_used: Optional[int] = memory_used
        self.memory_interface: Optional[int] = memory_interface
        self.memory_usage: Optional[int] = memory_usage
        self.gpu_usage: Optional[int] = gpu_usage
        self.encoder_usage: Optional[int] = encoder_usage
        self.decoder_usage: Optional[int] = decoder_usage


class Power:
    def __init__(self,
                 draw: Optional[float] = None,
                 limit: Optional[float] = None,
                 default: Optional[float] = None,
                 minimum: Optional[float] = None,
                 enforced: Optional[float] = None,
                 maximum: Optional[float] = None
                 ) -> None:
        self.draw: Optional[float] = draw
        self.limit: Optional[float] = limit
        self.default: Optional[float] = default
        self.minimum: Optional[float] = minimum
        self.enforced: Optional[float] = enforced
        self.maximum: Optional[float] = maximum


class Temp:
    def __init__(self,
                 gpu: Optional[int] = None,
                 maximum: Optional[int] = None,
                 slowdown: Optional[int] = None,
                 shutdown: Optional[int] = None
                 ) -> None:
        self.gpu: Optional[int] = gpu
        self.maximum: Optional[int] = maximum
        self.slowdown: Optional[int] = slowdown
        self.shutdown: Optional[int] = shutdown


class Fan:
    def __init__(self,
                 fan_list: List[Tuple[int, int]] = None,
                 control_allowed: bool = False,
                 manual_control: bool = False
                 ) -> None:
        self.fan_list = fan_list
        self.control_allowed = control_allowed
        self.manual_control = manual_control


class Clocks:
    def __init__(self,
                 graphic_current: Optional[int] = None,
                 graphic_max: Optional[int] = None,
                 sm_current: Optional[int] = None,
                 sm_max: Optional[int] = None,
                 memory_current: Optional[int] = None,
                 memory_max: Optional[int] = None,
                 video_current: Optional[int] = None,
                 video_max: Optional[int] = None
                 ) -> None:
        self.graphic_current: Optional[int] = graphic_current
        self.graphic_max: Optional[int] = graphic_max
        self.sm_current: Optional[int] = sm_current
        self.sm_max: Optional[int] = sm_max
        self.memory_current: Optional[int] = memory_current
        self.memory_max: Optional[int] = memory_max
        self.video_current: Optional[int] = video_current
        self.video_max: Optional[int] = video_max


class Overclock:
    def __init__(self,
                 perf_level_max: Optional[int] = None,
                 available: bool = False,
                 gpu_range: Optional[Tuple[int, int]] = None,
                 gpu_offset: Optional[int] = None,
                 memory_range: Optional[Tuple[int, int]] = None,
                 memory_offset: Optional[int] = None
                 ) -> None:
        self.perf_level_max: Optional[int] = perf_level_max
        self.available: bool = available
        self.gpu_range: Optional[Tuple[int, int]] = gpu_range
        self.gpu_offset: Optional[int] = gpu_offset
        self.memory_range: Optional[Tuple[int, int]] = memory_range
        self.memory_offset: Optional[int] = memory_offset


class GpuStatus:
    def __init__(self,
                 index: int,
                 info: Info,
                 power: Power,
                 temp: Temp,
                 fan: Fan,
                 clocks: Clocks,
                 overclock: Overclock
                 ) -> None:
        self.index = index
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


class FanProfileType(Enum):
    AUTO = 'auto'
    FAN_CURVE = 'fan_curve'


class FanProfile(Model):
    id = AutoIncrementField()
    type = CharField(
        constraints=[Check("type='%s' OR type='%s'" % (FanProfileType.AUTO.value, FanProfileType.FAN_CURVE.value))],
        default=FanProfileType.FAN_CURVE.value)
    name = CharField()
    read_only = BooleanField(default=False)
    timestamp = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])

    class Meta:
        legacy_table_names = False
        database = INJECTOR.get(SqliteDatabase)


@post_save(sender=FanProfile)
def on_fan_profile_added(_: Any, profile: FanProfile, created: bool) -> None:
    LOG.debug("Profile added")
    FAN_PROFILE_CHANGED_SUBJECT.on_next(DbChange(profile, DbChange.INSERT if created else DbChange.UPDATE))


@post_delete(sender=FanProfile)
def on_fan_profile_deleted(_: Any, profile: FanProfile) -> None:
    LOG.debug("Profile deleted")
    FAN_PROFILE_CHANGED_SUBJECT.on_next(DbChange(profile, DbChange.DELETE))


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
    LOG.debug("Profile added")
    SPEED_STEP_CHANGED_SUBJECT.on_next(DbChange(step, DbChange.INSERT if created else DbChange.UPDATE))


@post_delete(sender=SpeedStep)
def on_speed_step_deleted(_: Any, step: SpeedStep) -> None:
    LOG.debug("Step deleted")
    SPEED_STEP_CHANGED_SUBJECT.on_next(DbChange(step, DbChange.DELETE))


class CurrentFanProfile(Model):
    profile = ForeignKeyField(FanProfile, unique=True)
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
    FanProfile.create(name="Auto (VBIOS controlled)", type=FanProfileType.AUTO.value, read_only=True)
    fan_silent = FanProfile.create(name="Custom")

    # Fan Silent
    SpeedStep.create(profile=fan_silent.id, temperature=20, duty=0)
    SpeedStep.create(profile=fan_silent.id, temperature=30, duty=25)
    SpeedStep.create(profile=fan_silent.id, temperature=40, duty=45)
    SpeedStep.create(profile=fan_silent.id, temperature=65, duty=70)
    SpeedStep.create(profile=fan_silent.id, temperature=70, duty=90)
    SpeedStep.create(profile=fan_silent.id, temperature=75, duty=100)
