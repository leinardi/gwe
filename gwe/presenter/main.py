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
from typing import Optional, Any, List, Tuple, Dict, Callable

from injector import inject, singleton
from rx import Observable
from rx.concurrency import GtkScheduler, ThreadPoolScheduler
from rx.concurrency.schedulerbase import SchedulerBase
from rx.disposables import CompositeDisposable

from gwe.conf import SETTINGS_DEFAULTS, APP_NAME, APP_SOURCE_URL
from gwe.di import FanProfileChangedSubject, SpeedStepChangedSubject
from gwe.interactor import GetStatusInteractor, SettingsInteractor, \
    CheckNewVersionInteractor, SetOverclockInteractor, SetPowerLimitInteractor, SetFanSpeedInteractor
from gwe.model import Status, FanProfile, CurrentFanProfile, SpeedStep, DbChange, FanProfileType, GpuStatus
from gwe.presenter.edit_fan_profile import EditFanProfilePresenter
from gwe.presenter.preferences import PreferencesPresenter
from gwe.repository import NOT_AVAILABLE_STRING

LOG = logging.getLogger(__name__)
_ADD_NEW_PROFILE_INDEX = -10


class MainViewInterface:
    def toggle_window_visibility(self) -> None:
        raise NotImplementedError()

    def refresh_status(self, status: Optional[Status]) -> None:
        raise NotImplementedError()

    def refresh_fan_profile_combobox(self, data: List[Tuple[int, str]], active: Optional[int]) -> None:
        raise NotImplementedError()

    def refresh_chart(self, profile: Optional[FanProfile] = None, reset: bool = False) -> None:
        raise NotImplementedError()

    def set_apply_fan_profile_button_enabled(self, enabled: bool) -> None:
        raise NotImplementedError()

    def set_edit_fan_profile_button_enabled(self, enabled: bool) -> None:
        raise NotImplementedError()

    def set_statusbar_text(self, text: str) -> None:
        raise NotImplementedError()

    def show_main_infobar_message(self, message: str, markup: bool = False) -> None:
        raise NotImplementedError()

    def get_power_limit(self) -> Tuple[int, int]:
        raise NotImplementedError()

    def get_overclock_offsets(self) -> Tuple[int, int, int, int]:
        raise NotImplementedError()

    # def show_fixed_fan_profile_popover(self, profile: FanProfile) -> None:
    #     raise NotImplementedError()
    #
    # def dismiss_and_get_value_fixed_speed_popover(self) -> Tuple[int, str]:
    #     raise NotImplementedError()

    def show_about_dialog(self) -> None:
        raise NotImplementedError()


@singleton
class MainPresenter:
    @inject
    def __init__(self,
                 edit_fan_profile_presenter: EditFanProfilePresenter,
                 preferences_presenter: PreferencesPresenter,
                 get_status_interactor: GetStatusInteractor,
                 set_power_limit_interactor: SetPowerLimitInteractor,
                 set_overclock_interactor: SetOverclockInteractor,
                 set_fan_speed_interactor: SetFanSpeedInteractor,
                 settings_interactor: SettingsInteractor,
                 check_new_version_interactor: CheckNewVersionInteractor,
                 fan_profile_changed_subject: FanProfileChangedSubject,
                 speed_step_changed_subject: SpeedStepChangedSubject,
                 composite_disposable: CompositeDisposable,
                 ) -> None:
        LOG.debug("init MainPresenter ")
        self.main_view: MainViewInterface = MainViewInterface()
        self._edit_fan_profile_presenter = edit_fan_profile_presenter
        self._preferences_presenter = preferences_presenter
        self._scheduler: SchedulerBase = ThreadPoolScheduler(multiprocessing.cpu_count())
        self._get_status_interactor: GetStatusInteractor = get_status_interactor
        self._set_power_limit_interactor = set_power_limit_interactor
        self._set_overclock_interactor = set_overclock_interactor
        self._settings_interactor = settings_interactor
        self._check_new_version_interactor = check_new_version_interactor
        self._set_fan_speed_interactor = set_fan_speed_interactor
        self._fan_profile_changed_subject = fan_profile_changed_subject
        self._speed_step_changed_subject = speed_step_changed_subject
        self._composite_disposable: CompositeDisposable = composite_disposable
        self._fan_profile_selected: Optional[FanProfile] = None
        self._fan_profile_applied: Optional[FanProfile] = None
        # self._should_update_fan_speed: bool = False
        self.application_quit: Callable = lambda *args: None  # will be set by the Application

    def on_start(self) -> None:
        self._refresh_fan_profile(True)
        self._register_db_listeners()
        self._start_refresh()
        self._check_new_version()

    def _register_db_listeners(self) -> None:
        self._fan_profile_changed_subject.subscribe(on_next=self._on_fan_profile_list_changed,
                                                    on_error=lambda e: LOG.exception("Db signal error: %s", str(e)))
        self._speed_step_changed_subject.subscribe(on_next=self._on_speed_step_list_changed,
                                                   on_error=lambda e: LOG.exception("Db signal error: %s", str(e)))

    def on_power_limit_apply_button_clicked(self, *_: Any) -> None:
        self._composite_disposable \
            .add(self._set_power_limit_interactor.execute(*self.main_view.get_power_limit())
                 .subscribe_on(self._scheduler)
                 .observe_on(GtkScheduler())
                 .subscribe(on_error=lambda e: LOG.exception("Set overclock error: %s", str(e)))
                 )

    def on_overclock_apply_button_clicked(self, *_: Any) -> None:
        self._composite_disposable \
            .add(self._set_overclock_interactor.execute(*self.main_view.get_overclock_offsets())
                 .subscribe_on(self._scheduler)
                 .observe_on(GtkScheduler())
                 .subscribe(on_error=lambda e: LOG.exception("Set overclock error: %s", str(e)))
                 )

    def _on_fan_profile_list_changed(self, db_change: DbChange) -> None:
        profile = db_change.entry
        if db_change.type == DbChange.DELETE:
            self._refresh_fan_profile()
            self._fan_profile_selected = None
        elif db_change.type == DbChange.INSERT or db_change.type == DbChange.UPDATE:
            self._refresh_fan_profile(profile_id=profile.id)

    def _on_speed_step_list_changed(self, db_change: DbChange) -> None:
        profile = db_change.entry.profile
        if self._fan_profile_selected.id == profile.id:
            self.main_view.refresh_chart(profile)

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
                 .subscribe(on_next=self._update_status,
                            on_error=lambda e: LOG.exception("Refresh error: %s", str(e)))
                 )

    def _update_status(self, status: Optional[Status]) -> None:
        if status is not None:
            gpu_status = status.gpu_status_list[0]
            self._update_fan(gpu_status)
            self.main_view.refresh_status(status)
        else:
            gpu_index = 0
            self._set_fan_speed(gpu_index, manual_control=False)

    def _update_fan(self, gpu_status: GpuStatus) -> None:
        fan = gpu_status.fan
        if fan.control_allowed:
            if self._fan_profile_selected is None and not fan.manual_control:
                self._refresh_fan_profile(
                    profile_id=FanProfile.get(FanProfile.type == FanProfileType.AUTO.value).id)
            elif self._fan_profile_applied and self._fan_profile_applied.type != FanProfileType.AUTO.value:
                if not self._fan_profile_applied.steps:
                    self._set_fan_speed(gpu_status.index, manual_control=False)
                elif NOT_AVAILABLE_STRING not in gpu_status.temp.gpu:
                    temperature = int(gpu_status.temp.gpu.rstrip(' C'))
                    speed = round(self._get_fan_duty(self._fan_profile_applied, temperature))
                    if fan.fan_list and fan.fan_list[0][0] != speed:
                        self._set_fan_speed(gpu_status.index, round(speed))

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

    # def _load_last_profile(self) -> None:
    #     for current in CurrentFanProfile.select():

    def _refresh_fan_profile(self, init: bool = False, profile_id: Optional[int] = None) -> None:
        data = [(p.id, p.name) for p in FanProfile.select()]
        active = None
        if profile_id is not None:
            active = next(i for i, item in enumerate(data) if item[0] == profile_id)
        # elif init and self._settings_interactor.get_bool('settings_load_last_profile'):
        #     self._should_update_fan_speed = True
        #     current: CurrentFanProfile = CurrentFanProfile.get_or_none(channel=channel.value)
        #     if current is not None:
        #         active = next(i for i, item in enumerate(data) if item[0] == current.profile.id)
        #         self._set_fan_profile(current.profile)
        data.append((_ADD_NEW_PROFILE_INDEX, "<span style='italic' alpha='50%'>Add new profile...</span>"))
        self.main_view.refresh_fan_profile_combobox(data, active)

    def on_menu_settings_clicked(self, *_: Any) -> None:
        self._preferences_presenter.show()

    def on_menu_about_clicked(self, *_: Any) -> None:
        self.main_view.show_about_dialog()

    def on_stack_visible_child_changed(self, *_: Any) -> None:
        pass

    def on_fan_profile_selected(self, widget: Any, *_: Any) -> None:
        active = widget.get_active()
        if active >= 0:
            profile_id = widget.get_model()[active][0]
            self._select_fan_profile(profile_id)

    def on_quit_clicked(self, *_: Any) -> None:
        self.application_quit()

    def on_toggle_app_window_clicked(self, *_: Any) -> None:
        self.main_view.toggle_window_visibility()

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

    #
    # @staticmethod
    # def _get_profile_data(profile: FanProfile) -> List[Tuple[int, int]]:
    #     return [(p.temperature, p.duty) for p in profile.steps]
    #
    def on_fan_edit_button_clicked(self, *_: Any) -> None:
        profile = self._fan_profile_selected
        if profile:
            self._edit_fan_profile_presenter.show_edit(profile)
        else:
            LOG.error('Profile is None!')

    #
    # def on_fixed_speed_apply_button_clicked(self, *_: Any) -> None:
    #     value, channel = self.main_view.dismiss_and_get_value_fixed_speed_popover()
    #     profile = self._profile_selected[channel]
    #     speed_step: SpeedStep = profile.steps[0]
    #     speed_step.duty = value
    #     speed_step.save()
    #     if channel == ChannelType.FAN.value:
    #         self._should_update_fan_speed = False
    #     self.main_view.refresh_chart(profile)
    #
    def on_fan_apply_button_clicked(self, *_: Any) -> None:
        gpu_index = 0
        if self._fan_profile_selected:
            self._fan_profile_applied = self._fan_profile_selected
            if self._fan_profile_selected.type == FanProfileType.AUTO.value:
                self._set_fan_speed(gpu_index, manual_control=False)
        self._update_current_fan_profile(self._fan_profile_selected)
        # self._should_update_fan_speed = True

    def _set_fan_speed(self, gpu_index: int, speed: int = 100, manual_control: bool = True) -> None:
        self._composite_disposable \
            .add(self._set_fan_speed_interactor.execute(gpu_index, speed, manual_control)
                 .subscribe_on(self._scheduler)
                 .observe_on(GtkScheduler())
                 .subscribe(on_error=lambda e: (LOG.exception("Set cooling error: %s", str(e)),
                                                self.main_view.set_statusbar_text('Error applying fan profile!'))))

    def _update_current_fan_profile(self, profile: FanProfile) -> None:
        current: CurrentFanProfile = CurrentFanProfile.get_or_none()
        if current is None:
            CurrentFanProfile.create(profile=profile)
        else:
            current.profile = profile
            current.save()
        self.main_view.set_statusbar_text('%s fan profile selected' % profile.name)

    def _log_exception_return_empty_observable(self, ex: Exception) -> Observable:
        LOG.exception("Err = %s", ex)
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
                            on_error=lambda e: LOG.exception("Check new version error: %s", str(e)))
                 )

    def _handle_new_version_response(self, version: Optional[str]) -> None:
        if version is not None:
            message = "%s version <b>%s</b> is available! Click <a href=\"%s/blob/%s/CHANGELOG.md\"><b>here</b></a> " \
                      "to see what's new." % (APP_NAME, version, APP_SOURCE_URL, version)
            self.main_view.show_main_infobar_message(message, True)
