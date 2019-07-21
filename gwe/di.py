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

import logging

from gi.repository import Gtk
from injector import Module, provider, singleton, Injector, Key
from peewee import SqliteDatabase
from rx.disposable import CompositeDisposable
from rx.subject import Subject

from gwe.conf import APP_PACKAGE_NAME, APP_MAIN_UI_NAME, APP_DB_NAME, APP_EDIT_FAN_PROFILE_UI_NAME, \
    APP_PREFERENCES_UI_NAME, APP_HISTORICAL_DATA_UI_NAME, APP_EDIT_OC_PROFILE_UI_NAME
from gwe.util.path import get_config_path

LOG = logging.getLogger(__name__)

SpeedStepChangedSubject = Key("SpeedStepChangedSubject")
FanProfileChangedSubject = Key("FanProfileChangedSubject")
OverclockProfileChangedSubject = Key("OverclockProfileChangedSubject")
MainBuilder = Key(APP_MAIN_UI_NAME)
EditFanProfileBuilder = Key(APP_EDIT_FAN_PROFILE_UI_NAME)
EditOverclockProfileBuilder = Key(APP_EDIT_OC_PROFILE_UI_NAME)
HistoricalDataBuilder = Key(APP_HISTORICAL_DATA_UI_NAME)
PreferencesBuilder = Key(APP_PREFERENCES_UI_NAME)

_UI_RESOURCE_PATH = "/com/leinardi/gwe/ui/{}"


# pylint: disable=no-self-use
class ProviderModule(Module):
    @singleton
    @provider
    def provide_main_builder(self) -> MainBuilder:
        LOG.debug("provide Gtk.Builder")
        builder = Gtk.Builder()
        builder.set_translation_domain(APP_PACKAGE_NAME)
        builder.add_from_resource(_UI_RESOURCE_PATH.format(APP_MAIN_UI_NAME))
        return builder

    @singleton
    @provider
    def provide_edit_fan_profile_builder(self) -> EditFanProfileBuilder:
        LOG.debug("provide Gtk.Builder")
        builder = Gtk.Builder()
        builder.set_translation_domain(APP_PACKAGE_NAME)
        builder.add_from_resource(_UI_RESOURCE_PATH.format(APP_EDIT_FAN_PROFILE_UI_NAME))
        return builder

    @singleton
    @provider
    def provide_edit_overclock_profile_builder(self) -> EditOverclockProfileBuilder:
        LOG.debug("provide Gtk.Builder")
        builder = Gtk.Builder()
        builder.set_translation_domain(APP_PACKAGE_NAME)
        builder.add_from_resource(_UI_RESOURCE_PATH.format(APP_EDIT_OC_PROFILE_UI_NAME))
        return builder

    @singleton
    @provider
    def provide_historical_data_builder(self) -> HistoricalDataBuilder:
        LOG.debug("provide Gtk.Builder")
        builder = Gtk.Builder()
        builder.set_translation_domain(APP_PACKAGE_NAME)
        builder.add_from_resource(_UI_RESOURCE_PATH.format(APP_HISTORICAL_DATA_UI_NAME))
        return builder

    @singleton
    @provider
    def provide_preferences_builder(self) -> PreferencesBuilder:
        LOG.debug("provide Gtk.Builder")
        builder = Gtk.Builder()
        builder.set_translation_domain(APP_PACKAGE_NAME)
        builder.add_from_resource(_UI_RESOURCE_PATH.format(APP_PREFERENCES_UI_NAME))
        return builder

    @singleton
    @provider
    def provide_thread_pool_scheduler(self) -> CompositeDisposable:
        LOG.debug("provide CompositeDisposable")
        return CompositeDisposable()

    @singleton
    @provider
    def provide_database(self) -> SqliteDatabase:
        LOG.debug("provide SqliteDatabase")
        database = SqliteDatabase(get_config_path(APP_DB_NAME))
        database.connect()
        return database

    @singleton
    @provider
    def provide_speed_step_changed_subject(self) -> SpeedStepChangedSubject:
        return Subject()

    @singleton
    @provider
    def provide_fan_profile_changed_subject(self) -> FanProfileChangedSubject:
        return Subject()

    @singleton
    @provider
    def provide_overclock_profile_changed_subject(self) -> OverclockProfileChangedSubject:
        return Subject()


INJECTOR = Injector(ProviderModule)
