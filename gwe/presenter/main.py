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
import multiprocessing
from typing import Optional, Any, List, Tuple, Callable

from injector import inject, singleton
from rx import Observable
from rx.concurrency import GtkScheduler, ThreadPoolScheduler
from rx.concurrency.schedulerbase import SchedulerBase
from rx.disposables import CompositeDisposable

from gwe.conf import APP_NAME, APP_SOURCE_URL, APP_VERSION, APP_ID
from gwe.di import FanProfileChangedSubject, SpeedStepChangedSubject, OverclockProfileChangedSubject, INJECTOR
from gwe.interactor import GetStatusInteractor, SettingsInteractor, \
    CheckNewVersionInteractor, SetOverclockInteractor, SetPowerLimitInteractor, SetFanSpeedInteractor
from gwe.model import Status, FanProfile, CurrentFanProfile, DbChange, FanProfileType, GpuStatus, \
    CurrentOverclockProfile, OverclockProfile
from gwe.presenter.edit_fan_profile import EditFanProfilePresenter
from gwe.presenter.edit_overclock_profile import EditOverclockProfilePresenter
from gwe.presenter.historical_data import HistoricalDataPresenter
from gwe.presenter.preferences import PreferencesPresenter
from gwe.util.view import show_notification, open_uri, get_default_application

LOG = logging.getLogger(__name__)
_ADD_NEW_PROFILE_INDEX = -10


class MainViewInterface:
    def toggle_window_visibility(self) -> None:
        raise NotImplementedError()

    def refresh_status(self, status: Optional[Status], gpu_index: int) -> None:
        raise NotImplementedError()

    def refresh_fan_profile_combobox(self, data: List[Tuple[int, str]], active: Optional[int]) -> None:
        raise NotImplementedError()

    def refresh_overclock_profile_combobox(self, data: List[Tuple[int, str]], active: Optional[int]) -> None:
        raise NotImplementedError()

    def refresh_chart(self, profile: Optional[FanProfile] = None, reset: bool = False) -> None:
        raise NotImplementedError()

    def set_apply_fan_profile_button_enabled(self, enabled: bool) -> None:
        raise NotImplementedError()

    def set_edit_fan_profile_button_enabled(self, enabled: bool) -> None:
        raise NotImplementedError()

    def set_apply_overclock_profile_button_enabled(self, enabled: bool) -> None:
        raise NotImplementedError()

    def set_edit_overclock_profile_button_enabled(self, enabled: bool) -> None:
        raise NotImplementedError()

    def set_statusbar_text(self, text: str) -> None:
        raise NotImplementedError()

    def show_main_infobar_message(self, message: str, markup: bool = False) -> None:
        raise NotImplementedError()

    def get_power_limit(self) -> Tuple[int, int]:
        raise NotImplementedError()

    def show_about_dialog(self) -> None:
        raise NotImplementedError()


@singleton
class MainPresenter:
    @inject
    def __init__(self,
                 edit_fan_profile_presenter: EditFanProfilePresenter,
                 edit_overclock_profile_presenter: EditOverclockProfilePresenter,
                 historical_data_presenter: HistoricalDataPresenter,
                 preferences_presenter: PreferencesPresenter,
                 get_status_interactor: GetStatusInteractor,
                 set_power_limit_interactor: SetPowerLimitInteractor,
                 set_overclock_interactor: SetOverclockInteractor,
                 set_fan_speed_interactor: SetFanSpeedInteractor,
                 settings_interactor: SettingsInteractor,
                 check_new_version_interactor: CheckNewVersionInteractor,
                 speed_step_changed_subject: SpeedStepChangedSubject,
                 fan_profile_changed_subject: FanProfileChangedSubject,
                 overclock_profile_changed_subject: OverclockProfileChangedSubject,
                 composite_disposable: CompositeDisposable,
                 ) -> None:
        LOG.debug("init MainPresenter ")
        self.main_view: MainViewInterface = MainViewInterface()
        self._edit_fan_profile_presenter = edit_fan_profile_presenter
        self._edit_overclock_profile_presenter = edit_overclock_profile_presenter
        self._historical_data_presenter = historical_data_presenter
        self._preferences_presenter = preferences_presenter
        self._scheduler: SchedulerBase = ThreadPoolScheduler(multiprocessing.cpu_count())
        self._get_status_interactor: GetStatusInteractor = get_status_interactor
        self._set_power_limit_interactor = set_power_limit_interactor
        self._set_overclock_interactor = set_overclock_interactor
        self._settings_interactor = settings_interactor
        self._check_new_version_interactor = check_new_version_interactor
        self._set_fan_speed_interactor = set_fan_speed_interactor
        self._speed_step_changed_subject = speed_step_changed_subject
        self._fan_profile_changed_subject = fan_profile_changed_subject
        self._overclock_profile_changed_subject = overclock_profile_changed_subject
        self._composite_disposable: CompositeDisposable = composite_disposable
        self._fan_profile_selected: Optional[FanProfile] = None
        self._fan_profile_applied: Optional[FanProfile] = None
        self._overclock_profile_selected: Optional[OverclockProfile] = None
        self._overclock_profile_applied: Optional[OverclockProfile] = None
        self._latest_status: Optional[Status] = None
        self._gpu_index: int = 0

    def on_start(self) -> None:
        self._refresh_fan_profile_ui(True)
        self._register_db_listeners()
        self._start_refresh()
        self._check_new_version()

    def on_historical_data_button_clicked(self, *_: Any) -> None:
        self._historical_data_presenter.show()

    def on_power_limit_apply_button_clicked(self, *_: Any) -> None:
        self._composite_disposable \
            .add(self._set_power_limit_interactor.execute(*self.main_view.get_power_limit())
                 .subscribe_on(self._scheduler)
                 .observe_on(GtkScheduler())
                 .subscribe(on_next=self._handle_set_power_limit_result, on_error=self._handle_set_power_limit_result)
                 )

    def on_fan_edit_button_clicked(self, *_: Any) -> None:
        profile = self._fan_profile_selected
        if profile:
            self._edit_fan_profile_presenter.show_edit(profile)
        else:
            LOG.error('Profile is None!')

    def on_fan_apply_button_clicked(self, *_: Any) -> None:
        if self._fan_profile_selected:
            self._fan_profile_applied = self._fan_profile_selected
            if self._fan_profile_selected.type == FanProfileType.AUTO.value:
                self._set_fan_speed(self._gpu_index, manual_control=False)
            self._refresh_fan_profile_ui(profile_id=self._fan_profile_selected.id)
            self._update_current_fan_profile(self._fan_profile_selected)

    def on_overclock_edit_button_clicked(self, *_: Any) -> None:
        profile = self._overclock_profile_selected
        assert self._latest_status is not None
        overclock = self._latest_status.gpu_status_list[self._gpu_index].overclock
        if profile:
            self._edit_overclock_profile_presenter.show_edit(profile, overclock, self._gpu_index)
        else:
            LOG.error('Profile is None!')

    def on_overclock_apply_button_clicked(self, *_: Any) -> None:
        if self._overclock_profile_selected:
            self._overclock_profile_applied = self._overclock_profile_selected
            self._refresh_overclock_profile_ui(profile_id=self._overclock_profile_selected.id)
            assert self._latest_status is not None
            self._composite_disposable.add(self._set_overclock_interactor.execute(
                self._gpu_index,
                self._latest_status.gpu_status_list[self._gpu_index].overclock.perf_level_max,
                self._overclock_profile_applied.gpu,
                self._overclock_profile_applied.memory)
                                           .subscribe_on(self._scheduler)
                                           .observe_on(GtkScheduler())
                                           .subscribe(on_next=self._handle_set_overclock_result,
                                                      on_error=self._handle_set_overclock_result)
                                           )

    def on_menu_settings_clicked(self, *_: Any) -> None:
        self._preferences_presenter.show()

    def on_menu_changelog_clicked(self, *_: Any) -> None:
        open_uri(self._get_changelog_uri())

    def on_menu_about_clicked(self, *_: Any) -> None:
        self.main_view.show_about_dialog()

    def on_fan_profile_selected(self, widget: Any, *_: Any) -> None:
        active = widget.get_active()
        if active >= 0:
            profile_id = widget.get_model()[active][0]
            self._select_fan_profile(profile_id)

    def on_overclock_profile_selected(self, widget: Any, *_: Any) -> None:
        active = widget.get_active()
        if active >= 0:
            profile_id = widget.get_model()[active][0]
            self._select_overclock_profile(profile_id)

    @staticmethod
    def on_quit_clicked(*_: Any) -> None:
        get_default_application().quit()

    def on_toggle_app_window_clicked(self, *_: Any) -> None:
        self.main_view.toggle_window_visibility()

    def _register_db_listeners(self) -> None:
        self._speed_step_changed_subject.subscribe(on_next=self._on_speed_step_list_changed,
                                                   on_error=lambda e: LOG.exception(f"Db signal error: {str(e)}"))
        self._fan_profile_changed_subject.subscribe(on_next=self._on_fan_profile_list_changed,
                                                    on_error=lambda e: LOG.exception(f"Db signal error: {str(e)}"))
        self._overclock_profile_changed_subject.subscribe(on_next=self._on_overclock_profile_list_changed,
                                                          on_error=lambda e: LOG.exception(
                                                              f"Db signal error: {str(e)}"))

    def _on_speed_step_list_changed(self, db_change: DbChange) -> None:
        profile = db_change.entry.profile
        if self._fan_profile_selected and self._fan_profile_selected.id == profile.id:
            self.main_view.refresh_chart(profile)

    def _on_fan_profile_list_changed(self, db_change: DbChange) -> None:
        profile = db_change.entry
        if db_change.type == DbChange.DELETE:
            self._refresh_fan_profile_ui()
            self._fan_profile_selected = None
            self._fan_profile_applied = None
        elif db_change.type == DbChange.INSERT or db_change.type == DbChange.UPDATE:
            self._refresh_fan_profile_ui(profile_id=profile.id)

    def _on_overclock_profile_list_changed(self, db_change: DbChange) -> None:
        profile = db_change.entry
        if db_change.type == DbChange.DELETE:
            self._refresh_overclock_profile_ui()
            self._overclock_profile_selected = None
            self._overclock_profile_applied = None
        elif db_change.type == DbChange.INSERT or db_change.type == DbChange.UPDATE:
            self._refresh_overclock_profile_ui(profile_id=profile.id)

    def _start_refresh(self) -> None:
        LOG.debug("start refresh")
        refresh_interval_ms = self._settings_interactor.get_int('settings_refresh_interval') * 1000
        self._composite_disposable \
            .add(Observable
                 .interval(refresh_interval_ms, scheduler=self._scheduler)
                 .start_with(0)
                 .subscribe_on(self._scheduler)
                 .flat_map(lambda _: self._get_status())
                 .observe_on(GtkScheduler())
                 .subscribe(on_next=self._on_status_updated,
                            on_error=lambda e: LOG.exception(f"Refresh error: {str(e)}"))
                 )

    def _on_status_updated(self, status: Optional[Status]) -> None:
        if status is not None:
            was_latest_status_none = self._latest_status is None
            self._latest_status = status
            if was_latest_status_none:
                self._refresh_overclock_profile_ui(True)
            self._update_fan(status)
            self.main_view.refresh_status(status, self._gpu_index)
            self._historical_data_presenter.add_status(status, self._gpu_index)
        else:
            self._set_fan_speed(self._gpu_index, manual_control=False)

    def _update_fan(self, status: Status) -> None:
        fan = status.gpu_status_list[self._gpu_index].fan
        if fan.control_allowed:
            if self._fan_profile_selected is None and not fan.manual_control:
                fan_profile = FanProfile.get(FanProfile.type == FanProfileType.AUTO.value)
                self._fan_profile_applied = fan_profile
                self._refresh_fan_profile_ui(profile_id=fan_profile.id)
            elif self._fan_profile_applied and self._fan_profile_applied.type != FanProfileType.AUTO.value:
                gpu_status = status.gpu_status_list[self._gpu_index]
                if not self._fan_profile_applied.steps:
                    self._set_fan_speed(gpu_status.index, manual_control=False)
                elif gpu_status.temp.gpu:
                    try:
                        speed = round(self._get_fan_duty(self._fan_profile_applied, gpu_status.temp.gpu))
                        if fan.fan_list and fan.fan_list[0][0] != speed:
                            self._set_fan_speed(gpu_status.index, round(speed))
                    except ValueError:
                        LOG.exception(f'Unable to parse temperature {gpu_status.temp.gpu}')

    @staticmethod
    def _get_fan_duty(profile: FanProfile, gpu_temperature: float) -> float:
        p_1 = ([(i.temperature, i.duty) for i in profile.steps if i.temperature <= gpu_temperature] or [None])[-1]
        p_2 = next(((i.temperature, i.duty) for i in profile.steps if i.temperature > gpu_temperature), None)
        duty = 0.0
        if p_1 and p_2:
            duty = ((p_2[1] - p_1[1]) / (p_2[0] - p_1[0])) * (gpu_temperature - p_1[0]) + p_1[1]
        elif p_1:
            duty = float(p_1[1])
        elif p_2:
            duty = float(p_2[1])
        return duty

    def _refresh_fan_profile_ui(self, init: bool = False, profile_id: Optional[int] = None) -> None:
        current: Optional[CurrentFanProfile] = None
        if init and self._settings_interactor.get_bool('settings_load_last_profile'):
            current = CurrentFanProfile.get_or_none()
            if current is not None:
                self._fan_profile_applied = current.profile
        data: List[Tuple[int, str]] = []
        for fan_profile in FanProfile.select():
            if self._fan_profile_applied is not None and self._fan_profile_applied.id == fan_profile.id:
                name = f"<b>{fan_profile.name}</b>"
            else:
                name = fan_profile.name
            data.append((fan_profile.id, name))
        active = None
        if profile_id is not None:
            active = next(i for i, item in enumerate(data) if item[0] == profile_id)
        elif current is not None:
            active = next(i for i, item in enumerate(data) if item[0] == current.profile.id)
        data.append((_ADD_NEW_PROFILE_INDEX, "<span style='italic' alpha='50%'>Add new profile...</span>"))
        self.main_view.refresh_fan_profile_combobox(data, active)

    def _select_fan_profile(self, profile_id: int) -> None:
        if profile_id == _ADD_NEW_PROFILE_INDEX:
            self.main_view.set_apply_fan_profile_button_enabled(False)
            self.main_view.set_edit_fan_profile_button_enabled(False)
            self.main_view.refresh_chart(reset=True)
            self._edit_fan_profile_presenter.show_add()
        else:
            profile: FanProfile = FanProfile.get(id=profile_id)
            self._fan_profile_selected = profile
            if profile.read_only:
                self.main_view.set_edit_fan_profile_button_enabled(False)
            else:
                self.main_view.set_edit_fan_profile_button_enabled(True)
            self.main_view.set_apply_fan_profile_button_enabled(True)
            self.main_view.refresh_chart(profile)

    def _set_fan_speed(self, gpu_index: int, speed: int = 100, manual_control: bool = True) -> None:
        self._composite_disposable \
            .add(self._set_fan_speed_interactor.execute(gpu_index, speed, manual_control)
                 .subscribe_on(self._scheduler)
                 .observe_on(GtkScheduler())
                 .subscribe(on_error=lambda e: (LOG.exception(f"Set cooling error: {str(e)}"),
                                                self.main_view.set_statusbar_text('Error applying fan profile!'))))

    def _update_current_fan_profile(self, profile: FanProfile) -> None:
        current: CurrentFanProfile = CurrentFanProfile.get_or_none()
        if current is None:
            CurrentFanProfile.create(profile=profile)
        else:
            current.profile = profile
            current.save()
        self.main_view.set_statusbar_text(f'{profile.name} fan profile selected')

    def _refresh_overclock_profile_ui(self, init: bool = False, profile_id: Optional[int] = None) -> None:
        current: Optional[CurrentOverclockProfile] = None
        assert self._latest_status is not None
        if init and self._settings_interactor.get_bool('settings_load_last_profile') \
                and self._latest_status.gpu_status_list[self._gpu_index].overclock.available:
            current = CurrentOverclockProfile.get_or_none()
            if current is not None:
                self._overclock_profile_selected = current.profile
                self.on_overclock_apply_button_clicked()
        data: List[Tuple[int, str]] = []
        for overclock_profile in OverclockProfile.select():
            name_with_freqs = "{} ({}, {})".format(overclock_profile.name,
                                                   overclock_profile.gpu,
                                                   overclock_profile.memory)
            if self._overclock_profile_applied is not None \
                    and self._overclock_profile_applied.id == overclock_profile.id:
                name = f"<b>{name_with_freqs}</b>"
            else:
                name = name_with_freqs
            data.append((overclock_profile.id, name))
        active = None
        if profile_id is not None:
            active = next(i for i, item in enumerate(data) if item[0] == profile_id)
        elif current is not None:
            active = next(i for i, item in enumerate(data) if item[0] == current.profile.id)
        data.append((_ADD_NEW_PROFILE_INDEX, "<span style='italic' alpha='50%'>Add new profile...</span>"))
        self.main_view.refresh_overclock_profile_combobox(data, active)

    def _select_overclock_profile(self, profile_id: int) -> None:
        assert self._latest_status is not None
        if profile_id == _ADD_NEW_PROFILE_INDEX:
            self.main_view.set_apply_overclock_profile_button_enabled(False)
            self.main_view.set_edit_overclock_profile_button_enabled(False)
            self._edit_overclock_profile_presenter.show_add(
                self._latest_status.gpu_status_list[self._gpu_index].overclock, self._gpu_index)
        else:
            profile: OverclockProfile = OverclockProfile.get(id=profile_id)
            self._overclock_profile_selected = profile
            if profile.read_only:
                self.main_view.set_edit_overclock_profile_button_enabled(False)
            else:
                self.main_view.set_edit_overclock_profile_button_enabled(True)
            self.main_view.set_apply_overclock_profile_button_enabled(True)

    def _update_current_overclock_profile(self, profile: OverclockProfile) -> None:
        current: CurrentOverclockProfile = CurrentOverclockProfile.get_or_none()
        if current is None:
            CurrentOverclockProfile.create(profile=profile)
        else:
            current.profile = profile
            current.save()
        self.main_view.set_statusbar_text(f'{profile.name} overclock profile selected')

    def _log_exception_return_empty_observable(self, ex: Exception) -> Observable:
        LOG.exception(f"Err = {ex}")
        self.main_view.set_statusbar_text(str(ex))
        return Observable.just(None)

    def _get_status(self) -> Observable:
        return self._get_status_interactor.execute() \
            .catch_exception(self._log_exception_return_empty_observable)

    def _check_new_version(self) -> None:
        self._composite_disposable \
            .add(self._check_new_version_interactor.execute()
                 .subscribe_on(self._scheduler)
                 .observe_on(GtkScheduler())
                 .subscribe(on_next=self._handle_new_version_response,
                            on_error=lambda e: LOG.exception(f"Check new version error: {str(e)}"))
                 )

    def _handle_set_power_limit_result(self, result: Any) -> None:
        self._handle_generic_set_result(result, "power limit")

    def _handle_set_overclock_result(self, result: Any) -> None:
        if self._handle_generic_set_result(result, "overclock"):
            self._update_current_overclock_profile(self._overclock_profile_selected)

    def _handle_generic_set_result(self, result: Any, name: str) -> bool:
        if not isinstance(result, bool):
            LOG.exception(f"Set overclock error: {str(result)}")
            self.main_view.set_statusbar_text(f'Error applying {name}! {str(result)}')
            return False
        if not result:
            self.main_view.set_statusbar_text(f'Error applying {name}!')
            return False
        self.main_view.set_statusbar_text(f'{name.capitalize()} applied')
        return True

    def _handle_new_version_response(self, version: Optional[str]) -> None:
        if version is not None:
            message = f"{APP_NAME} version <b>{version}</b> is available! " \
                f"Click <a href=\"{self._get_changelog_uri(version)}\"><b>here</b></a> to see what's new."
            self.main_view.show_main_infobar_message(message, True)
            message = f"Version {version} is available! " \
                f"Click here to see what's new: {self._get_changelog_uri(version)}"
            show_notification("GWE update available!", message, APP_ID)

    @staticmethod
    def _get_changelog_uri(version: str = APP_VERSION) -> str:
        return f"{APP_SOURCE_URL}/blob/{version}/CHANGELOG.md"
