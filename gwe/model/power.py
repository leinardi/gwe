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
from typing import Optional


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
