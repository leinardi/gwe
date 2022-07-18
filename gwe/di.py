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

import os
import logging
import shutil
from typing import NewType

from gi.repository import Gtk
from injector import Module, provider, singleton, Injector
from peewee import SqliteDatabase, BooleanField
from playhouse.migrate import SqliteMigrator, migrate
from reactivex.disposable import CompositeDisposable
from reactivex.subject import Subject

from gwe.conf import APP_PACKAGE_NAME, APP_MAIN_UI_NAME, APP_DB_NAME, APP_EDIT_FAN_PROFILE_UI_NAME, \
    APP_PREFERENCES_UI_NAME, APP_HISTORICAL_DATA_UI_NAME, APP_EDIT_OC_PROFILE_UI_NAME, APP_DB_VERSION
from gwe.util.path import get_config_path

_LOG = logging.getLogger(__name__)

SpeedStepChangedSubject = NewType('SpeedStepChangedSubject', Subject)
FanProfileChangedSubject = NewType('FanProfileChangedSubject', Subject)
OverclockProfileChangedSubject = NewType('OverclockProfileChangedSubject', Subject)
SettingChangedSubject = NewType('SettingChangedSubject', Subject)
MainBuilder = NewType('MainBuilder', Gtk.Builder)
EditFanProfileBuilder = NewType('EditFanProfileBuilder', Gtk.Builder)
EditOverclockProfileBuilder = NewType('EditOverclockProfileBuilder', Gtk.Builder)
HistoricalDataBuilder = NewType('HistoricalDataBuilder', Gtk.Builder)
PreferencesBuilder = NewType('PreferencesBuilder', Gtk.Builder)

_UI_RESOURCE_PATH = "/com/leinardi/gwe/ui/{}"


# pylint: disable=no-self-use
class ProviderModule(Module):
    @singleton
    @provider
    def provide_main_builder(self) -> MainBuilder:
        _LOG.debug("provide Gtk.Builder")
        builder = MainBuilder(Gtk.Builder())
        builder.set_translation_domain(APP_PACKAGE_NAME)
        builder.add_from_resource(_UI_RESOURCE_PATH.format(APP_MAIN_UI_NAME))
        return builder

    @singleton
    @provider
    def provide_edit_fan_profile_builder(self) -> EditFanProfileBuilder:
        _LOG.debug("provide Gtk.Builder")
        builder = EditFanProfileBuilder(Gtk.Builder())
        builder.set_translation_domain(APP_PACKAGE_NAME)
        builder.add_from_resource(_UI_RESOURCE_PATH.format(APP_EDIT_FAN_PROFILE_UI_NAME))
        return builder

    @singleton
    @provider
    def provide_edit_overclock_profile_builder(self) -> EditOverclockProfileBuilder:
        _LOG.debug("provide Gtk.Builder")
        builder = EditOverclockProfileBuilder(Gtk.Builder())
        builder.set_translation_domain(APP_PACKAGE_NAME)
        builder.add_from_resource(_UI_RESOURCE_PATH.format(APP_EDIT_OC_PROFILE_UI_NAME))
        return builder

    @singleton
    @provider
    def provide_historical_data_builder(self) -> HistoricalDataBuilder:
        _LOG.debug("provide Gtk.Builder")
        builder = HistoricalDataBuilder(Gtk.Builder())
        builder.set_translation_domain(APP_PACKAGE_NAME)
        builder.add_from_resource(_UI_RESOURCE_PATH.format(APP_HISTORICAL_DATA_UI_NAME))
        return builder

    @singleton
    @provider
    def provide_preferences_builder(self) -> PreferencesBuilder:
        _LOG.debug("provide Gtk.Builder")
        builder = PreferencesBuilder(Gtk.Builder())
        builder.set_translation_domain(APP_PACKAGE_NAME)
        builder.add_from_resource(_UI_RESOURCE_PATH.format(APP_PREFERENCES_UI_NAME))
        return builder

    @singleton
    @provider
    def provide_thread_pool_scheduler(self) -> CompositeDisposable:
        _LOG.debug("provide CompositeDisposable")
        return CompositeDisposable()

    @staticmethod
    def _create_database(path_to_db: str) -> SqliteDatabase:
        database = SqliteDatabase(path_to_db)

        if os.path.exists(path_to_db):
            if database.pragma('user_version') == 0:
                _LOG.debug("upgrading database to version 1")
                shutil.copyfile(path_to_db, path_to_db + '.bak')

                database.pragma('user_version', 1, permanent=True)

                migrator = SqliteMigrator(database)
                vbios_silent_mode = BooleanField(default=False)
                migrate(
                    migrator.add_column('fan_profile', 'vbios_silent_mode', vbios_silent_mode),
                    migrator.add_column('current_fan_profile', 'vbios_silent_mode', vbios_silent_mode)
                )

                database.commit()
        else:
            database.pragma('user_version', APP_DB_VERSION, permanent=True)

        return database

    @singleton
    @provider
    def provide_database(self) -> SqliteDatabase:
        _LOG.debug("provide SqliteDatabase")
        return self._create_database(get_config_path(APP_DB_NAME))

    @singleton
    @provider
    def provide_speed_step_changed_subject(self) -> SpeedStepChangedSubject:
        return SpeedStepChangedSubject(Subject())

    @singleton
    @provider
    def provide_fan_profile_changed_subject(self) -> FanProfileChangedSubject:
        return FanProfileChangedSubject(Subject())

    @singleton
    @provider
    def provide_overclock_profile_changed_subject(self) -> OverclockProfileChangedSubject:
        return OverclockProfileChangedSubject(Subject())

    @singleton
    @provider
    def provide_setting_changed_subject(self) -> SettingChangedSubject:
        return SettingChangedSubject(Subject())


INJECTOR = Injector(ProviderModule)
