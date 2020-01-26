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
from typing import Any, Optional

from gi.repository import Gtk, GLib
from injector import singleton, inject
from rx import operators
from rx.disposable import CompositeDisposable
from rx.scheduler import ThreadPoolScheduler
from rx.scheduler.mainloop import GtkScheduler

from gwe.interactor.set_overclock_interactor import SetOverclockInteractor
from gwe.model.overclock_profile import OverclockProfile
from gwe.model.overclock import Overclock
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
        self._scheduler = ThreadPoolScheduler(multiprocessing.cpu_count())
        self._gpu_index: int = 0

    def show_add(self, overclock: Overclock, gpu_index: int) -> None:
        profile = OverclockProfile()
        profile.name = 'New profile'
        profile.save()
        self.show_edit(profile, overclock, gpu_index)

    def show_edit(self, profile: OverclockProfile, overclock: Overclock, gpu_index: int) -> None:
        self._profile = profile
        self._overclock = overclock
        self.view.show(profile, overclock)
        self._gpu_index = gpu_index

    def on_dialog_delete_event(self, widget: Gtk.Widget, *_: Any) -> Any:
        self._save_profile_name()
        return hide_on_delete(widget)

    def on_delete_profile_button_clicked(self, *_: Any) -> None:
        self._profile.delete_instance(recursive=True)
        self.view.hide()

    def on_apply_offsets_button_clicked(self, *_: Any) -> None:
        self._composite_disposable.add(self._set_overclock_interactor.execute(
            self._gpu_index,
            self._overclock.perf_level_max,
            self.view.get_gpu_offset(),
            self.view.get_memory_offset()).pipe(
            operators.subscribe_on(self._scheduler),
            operators.observe_on(GtkScheduler(GLib)),
        ).subscribe(on_next=self._handle_set_overclock_result,
                    on_error=self._handle_set_overclock_result))

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
    def _handle_set_overclock_result(result: Optional[Any]) -> None:
        if not isinstance(result, bool) or not result:
            LOG.exception(f"Set overclock error: {str(result)}")
