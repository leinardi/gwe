##############################################################################
# xnet.py - python versions of Xauth functions
#
# code taken from NvThermometer by Harry Organs, which was based on the code
# for python-xlib, written by Peter Liljenberg
# http://python-xlib.sourceforge.net/
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#        
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License at http://www.gnu.org/licenses/gpl.txt. 
# By using, editing and/or distributing this software you agree to 
# the terms and conditions of this license. 
#
# python procedural-style X protocol utilities
# based on GPL'ed code by Peter Liljenberg
# from python-xlib (http://python-xlib.sourceforge.net)
# i distilled this stuff from the classes in python-xlib
# to produce something a little more c-like.
# many thanks, saved me tons of digging through the
# xlib c code.


import socket
import os
import re
import struct
import string
from typing import Tuple

import fcntl  # python3-lockfile

if hasattr(fcntl, 'F_SETFD'):
    F_SETFD = fcntl.F_SETFD
    if hasattr(fcntl, 'FD_CLOEXEC'):
        FD_CLOEXEC = fcntl.FD_CLOEXEC
        FD_CLOEXEC = 1
else:
    from FCNTL import F_SETFD, FD_CLOEXEC

# protocol family constants from X.h provided by x.org
FamilyInternet = 0
FamilyDECnet = 1
FamilyChaos = 2
FamilyInternet6 = 6

# constant for local hosts
FamilyLocal = 256


###############################################################################
# a simple Exception class to raise X connection errors
#
class XConnectionError(Exception):

    def __init__(self, msg: str) -> None:
        self.msg = 'X CONNECTION ERROR: ' + msg

    def __str__(self) -> str:
        return self.msg


###############################################################################
# get X display info
#
_display_re = re.compile(r'^([-a-zA-Z0-9._]*):([0-9]+)(\.([0-9]+))?$')


def get_x_display(display: str = None) -> Tuple[str, str, int, int]:
    if display is None:
        d = os.environ.get('DISPLAY', '')
    else:
        d = display

    m = _display_re.match(d)
    if not m:
        raise XConnectionError('Bad display name')

    host = m.group(1)
    if host == 'unix':
        host = ''

    display_number = int(m.group(2))

    screen = m.group(4)
    if screen:
        screen_number = int(screen)
    else:
        screen_number = 0

    return d, host, display_number, screen_number


###############################################################################
# return a socket connected to X server port
#
def get_x_socket(host: str, display_number: int) -> socket.socket:
    x_socket = None
    try:
        if host:
            x_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            x_socket.connect((host, 6000 + display_number))
        else:
            x_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            x_socket.connect('/tmp/.X11-unix/X%d' % display_number)
    except socket.error as msg:
        if x_socket is not None:
            x_socket.close()
        raise XConnectionError('Socket error %s' % msg)

    else:
        fcntl.fcntl(x_socket.fileno(), F_SETFD, FD_CLOEXEC)
    x_socket.settimeout(5)
    return x_socket


###############################################################################
# parse .Xauthority file
#
def parse_Xauthority(filename=None):
    if filename is None:
        filename = os.environ.get('XAUTHORITY')

    if filename is None:
        try:
            filename = os.path.join(os.environ['HOME'], '.Xauthority')
        except KeyError:
            raise XConnectionError("$HOME not set, can't find ~/.Xauthority")

    try:
        xaf = open(filename, 'rb')
        raw = xaf.read()
        xaf.close()
    except IOError as err:
        raise XConnectionError("Can't read ~/.Xauthority: %s" % err[1])

    n = 0
    entries = []
    try:
        while n < len(raw):
            family, = struct.unpack('>H', raw[n:n + 2])
            n = n + 2

            length, = struct.unpack('>H', raw[n:n + 2])
            n = n + length + 2
            addr = raw[n - length: n]

            length, = struct.unpack('>H', raw[n:n + 2])
            n = n + length + 2
            num = raw[n - length: n]

            length, = struct.unpack('>H', raw[n:n + 2])
            n = n + length + 2
            name = raw[n - length: n]

            length, = struct.unpack('>H', raw[n:n + 2])
            n = n + length + 2
            data = raw[n - length: n]

            if len(data) != length:
                break

            entries.append((family, addr.decode('utf-8'), num.decode('utf-8'), name.decode('utf-8'), data))

    except struct.error:
        raise XConnectionError('.Xauthority parsing failed')

    if len(entries) == 0:
        raise XConnectionError('No connection authorization available')

    return entries


###############################################################################
# find an authority to connect with
#
def match_X_auth(family, address, dispno, elist, types=("MIT-MAGIC-COOKIE-1",)):
    num = str(dispno)

    matches = {}

    for efam, eaddr, enum, ename, edata in elist:
        if efam == family and eaddr == address and num == enum:
            matches[ename] = edata

    # Ugly workaround for https://superuser.com/questions/1390857/xauthority-is-missing-the-display-number
    if not matches:
        for efam, eaddr, enum, ename, edata in elist:
            if efam == family and eaddr == address:
                matches[ename] = edata
                break

    for t in types:
        try:
            return t, matches[t]
        except KeyError:
            return None


###############################################################################
# return the connection authority
#
def get_x_auth(x_socket: socket.socket, host: str, display_number: int):
    if host:
        family = FamilyInternet
        octets = x_socket.getpeername()[0].split('.')
        addr = string.join(map(lambda x: chr(int(x)), octets), '')
    else:
        family = FamilyLocal
        addr = socket.gethostname()

    al = parse_Xauthority()
    auth = match_X_auth(family, addr, display_number, al)

    if auth is not None:
        return auth
    else:
        if family == FamilyInternet and addr == '\x7f\x00\x00\x01':
            family = FamilyLocal
            addr = socket.gethostname()
            return match_X_auth(family, addr, display_number, al)


###############################################################################
# determine the byte order of architecture
#
def get_x_byteorder() -> int:
    bs = struct.unpack('BB', struct.pack('H', 0x0100))[0]
    if bs:
        order = 0x42
    else:
        order = 0x6c

    return order
