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
from typing import Any

from gi.repository import Gtk
from injector import singleton, inject
from rx.concurrency import GtkScheduler, ThreadPoolScheduler
from rx.concurrency.schedulerbase import SchedulerBase
from rx.disposables import CompositeDisposable

from gwe.interactor import SetOverclockInteractor
from gwe.model import OverclockProfile, Overclock
from gwe.util.view import hide_on_delete

LOG = logging.getLogger(__name__)


class EditOverclockProfileViewInterface:
    def show(self, profile: OverclockProfile, overclock: Overclock) -> None:
        raise NotImplementedError()

    def hide(self) -> None:
        raise NotImplementedError()

    def get_profile_name(self) -> str:
        raise NotImplementedError()

    def get_gpu_offset(self) -> int:
        raise NotImplementedError()

    def get_memory_offset(self) -> int:
        raise NotImplementedError()


@singleton
class EditOverclockProfilePresenter:
    @inject
    def __init__(self,
                 set_overclock_interactor: SetOverclockInteractor,
                 composite_disposable: CompositeDisposable
                 ) -> None:
        LOG.debug("init EditOverclockProfilePresenter")
        self._set_overclock_interactor = set_overclock_interactor
        self._composite_disposable: CompositeDisposable = composite_disposable
        self.view: EditOverclockProfileViewInterface = EditOverclockProfileViewInterface()
        self._profile = OverclockProfile()
        self._overclock = Overclock()
        self._scheduler: SchedulerBase = ThreadPoolScheduler(multiprocessing.cpu_count())

    def show_add(self, overclock: Overclock) -> None:
        profile = OverclockProfile()
        profile.name = 'New profile'
        profile.save()
        self.show_edit(profile, overclock)

    def show_edit(self, profile: OverclockProfile, overclock: Overclock) -> None:
        self._profile = profile
        self._overclock = overclock
        self.view.show(profile, overclock)

    def on_dialog_delete_event(self, widget: Gtk.Widget, *_: Any) -> Any:
        self._save_profile_name()
        return hide_on_delete(widget)

    def on_delete_profile_button_clicked(self, *_: Any) -> None:
        self._profile.delete_instance(recursive=True)
        self.view.hide()

    def on_apply_offsets_button_clicked(self, *_: Any) -> None:
        gpu_index = 0
        self._composite_disposable.add(self._set_overclock_interactor.execute(
            gpu_index, self._overclock.perf_level_max, self.view.get_gpu_offset(), self.view.get_memory_offset())
                                       .subscribe_on(self._scheduler)
                                       .observe_on(GtkScheduler())
                                       .subscribe(on_next=self._handle_set_overclock_result,
                                                  on_error=self._handle_set_overclock_result)
                                       )

    def on_save_offsets_button_clicked(self, *_: Any) -> None:
        self._profile.gpu = self.view.get_gpu_offset()
        self._profile.memory = self.view.get_memory_offset()
        self._profile.name = self.view.get_profile_name()
        self._profile.save()
        self.view.hide()

    def _save_profile_name(self) -> None:
        if self._profile is not None:
            name = self.view.get_profile_name()
            if name != self._profile.name:
                self._profile.name = name
                self._profile.save()

    @staticmethod
    def _handle_set_overclock_result(result: Any) -> bool:
        if not isinstance(result, bool) or not result:
            LOG.exception("Set overclock error: %s", str(result))
            return False
        return True
