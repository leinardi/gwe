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

import struct
import socket
import time
from platform import architecture
from typing import Tuple, Any, List, Dict

from gwe.nvidia import xnet

XFORMATBYTES = {'CARD8': 1, 'CARD16': 2, 'INT8': 1, 'INT16': 2,
                 'PAD': 1, 'BYTE': 1, 'CARD32': 4, 'INT32': 4, 'STRING8': 1}

XFORMATS = {'CARD8': 'B', 'CARD16': 'H', 'INT8': 'b', 'INT16': 'h',
             'PAD': 'B', 'BYTE': 'B', 'CARD32': 'I', 'INT32': 'i', 'STRING8': 's0I'}

_ARCHW = architecture()[0]
if _ARCHW.startswith('32bit'):  # adjust struct format strings for 32bit
    XFORMATS['CARD32'] = 'L'
    XFORMATS['INT32'] = 'l'
    XFORMATS['STRING8'] = 's0L'

_XERRORMSG = {1: 'Request error. The major or minor opcode of a request is invalid.',
              2: 'Value error. A request contained a bad argument value.',
              3: 'Window error. A value for a WINDOW argument does not name a defined WINDOW.',
              4: 'Pixmap error. A value for a PIXMAP argument does not name a defined PIXMAP.',
              5: 'Atom error. A value for an ATOM argument does not name a defined ATOM.',
              6: 'Cursor error. A value for a CURSOR argument does not name a defined CURSOR.',
              7: 'Font error. A value for a FONT argument does not name a defined FONT or a value for a FONTABLE '
                 'argument does not name a defined FONT or a defined GCONTEXT.',
              8: 'Match error. InputOnly window used as a DRAWABLE, or GCONTEXT argument does not have the same root '
                 'and depth as the destination DRAWABLE argument, or argument(s) fails to match request requirements.',
              9: 'Drawable error. A value for a DRAWABLE argument does not name a defined WINDOW or PIXMAP.',
              10: 'Access error. Resource access violation or conflict with another client',
              11: 'Alloc error. The server failed to allocate the requested resource.',
              12: 'Colormap error. A value for a COLORMAP argument does not name a defined COLORMAP.',
              13: 'GContext error. A value for a GCONTEXT argument does not name a defined GCONTEXT.',
              14: 'IDChoice error. The value chosen for a resource identifier either is not included in the range '
                  'assigned to the client or is already in use.',
              15: 'Name error. A font or color of the specified name does not exist.',
              16: 'Length error. The length of a request is shorter or longer than that required to minimally contain '
                  'the arguments, or the length of a request exceeds the maximum length accepted by the server.',
              17: 'Implementation error. The server does not implement some aspect of the request.'}

_XServerError_XERRORMSG = _XERRORMSG


class XData:
    """XData is a simple argument container used to avoid the
    pain and errors of indexing"""

    def __init__(self, format: str, size: Any, value: Any) -> None:
        self.format = format
        self.size = size
        self.value = value


def encode(*x_data_args: XData) -> bytearray:
    """encode takes a variable argument list consisting of XData
    types and returns an encoded byte stream ready to send to the X server.
    the XData args are X type, number of elements, and the value(s). the
    order of fields in the resulting byte stream is determined by the order
    of their respective arguments"""

    bytestream = bytearray()

    for x_data in x_data_args:
        structcode = str(XFORMATS[x_data.format])

        if x_data.size == 1:
            try:
                bytestream.extend(struct.pack(structcode, x_data.value))
            except:
                print("mela")
        else:
            if x_data.format.startswith('STRING8'):
                structcode = str(x_data.size) + structcode
                bytestream.extend(
                    struct.pack(structcode,
                                x_data.value.encode('ascii') if isinstance(x_data.value, str) else x_data.value))
            else:
                for i in x_data.value:
                    bytestream.extend(struct.pack(structcode, i))

    return bytestream


def decode(binary: bytes, *arguments: XData) -> Tuple[Dict[str, Any], bytes]:
    """decode takes a byte stream and a variable argument list of XData
    types and returns a dict containing the decoded byte stream.
    the XData args are X type, number of elements, and the key name to
    be associated with the value. the order of arguments determines
    what order the fields will be decoded in"""

    data = binary
    result_dict: Dict[str, Any] = {}

    for arg in arguments:
        structcode = XFORMATS[arg.format]
        format_size = XFORMATBYTES[arg.format]

        if not isinstance(arg.size, str):
            arg_size = arg.size
        else:
            arg_size = result_dict[arg.size]

        size = arg_size * format_size
        # workaround for https://bugs.launchpad.net/disper/+bug/908856
        size = max(size, struct.calcsize(structcode))

        if arg_size == 1:
            result_dict[arg.value] = struct.unpack(structcode, data[:size])[0]
        else:
            structcode = str(arg_size) + structcode
            size = struct.calcsize(structcode)
            if arg.format.startswith('STRING8'):
                result_dict[arg.value] = struct.unpack(structcode, data[:size])[0]

            else:
                result_dict[arg.value] = struct.unpack(structcode, data[:size])
        if isinstance(result_dict[arg.value], bytes):
            result_dict[arg.value] = result_dict[arg.value].decode('utf-8')
        data = data[size:]

    return result_dict, data


###############################################################################
# Exception class for X server errors
#
class XServerError(Exception):
    """XServerError is an Exception class to raise X errors.
    this class decodes the error return and selects the message
    to display. the error messages are copied from the X Protocol
    pdf. see the doc for an explanation of the other_info field,
    which contains extra data for some errors."""

    def __init__(self, encoding: bytes) -> None:
        x_reply, ad = decode(encoding,
                             XData('CARD8', 1, 'Error'),
                             XData('CARD8', 1, 'code'),
                             XData('CARD16', 1, 'sequence_number'),
                             XData('CARD32', 1, 'other_info'),
                             XData('CARD16', 1, 'minor_opcode'),
                             XData('CARD8', 1, 'major_opcode'),
                             XData('PAD', 21, 'unused'))
        self.error_code = x_reply['code']
        self.sequence_number = x_reply['sequence_number']
        self.major_opcode = x_reply['major_opcode']
        self.minor_opcode = x_reply['minor_opcode']
        self.message = _XERRORMSG[self.error_code]
        self.other_info = x_reply['other_info']

    def __str__(self) -> str:
        return 'X Error ' + str(self.error_code) + ': ' + self.message


###############################################################################
# Connection Setup request and replies
#
class XConnectRequest:
    """XConnectRequest encodes the packet needed to connect to the X server"""

    def __init__(self,
                 byte_order,
                 proto_major,
                 proto_minor,
                 auth_name,
                 auth_data) -> None:
        self.encoding = encode(XData('BYTE', 1, byte_order),
                               XData('PAD', 1, 0),
                               XData('CARD16', 1, proto_major),
                               XData('CARD16', 1, proto_minor),
                               XData('CARD16', 1, len(auth_name)),
                               XData('CARD16', 1, len(auth_data)),
                               XData('PAD', 2, [0, 0]),
                               XData('STRING8', len(auth_name), auth_name),
                               XData('STRING8', len(auth_data), auth_data))


class XConnectRefusedReply:
    """X server reply for failed logon attempt"""

    def __init__(self, encoding: bytes) -> None:
        x_reply, n = decode(encoding,
                            XData('BYTE', 1, 'Failed'),
                            XData('BYTE', 1, 'sz_reason'),
                            XData('CARD16', 1, 'protocol_major_version'),
                            XData('CARD16', 1, 'protocol_minor_version'),
                            XData('CARD16', 1, 'sz_additional'),
                            XData('STRING8', 'sz_reason', 'reason'))

        for n, v in x_reply.items():
            setattr(self, n, v)


class XConnectAcceptedReply:
    """the logon reply. contains all the info needed by
    clients to create windows, etc, as well as various
    server info like vendor name"""

    def __init__(self, encoding: bytes) -> None:
        x_reply, ad = decode(encoding,
                             XData('BYTE', 1, 'Success'),
                             XData('PAD', 1, 'unused_1'),
                             XData('CARD16', 1, 'protocol_major_version'),
                             XData('CARD16', 1, 'protocol_minor_version'),
                             XData('CARD16', 1, 'sz_additional'),
                             XData('CARD32', 1, 'release_number'),
                             XData('CARD32', 1, 'resource_id_base'),
                             XData('CARD32', 1, 'resource_id_mask'),
                             XData('CARD32', 1, 'motion_buffer_size'),
                             XData('CARD16', 1, 'sz_vendor'),
                             XData('CARD16', 1, 'maximum_request_length'),
                             XData('CARD8', 1, 'n_SCREENS'),
                             XData('BYTE', 1, 'n_FORMATS'),
                             XData('BYTE', 1, 'image_byte_order'),
                             XData('BYTE', 1, 'bitmap_format_bit_order'),
                             XData('CARD8', 1, 'bitmap_format_scanline_unit'),
                             XData('CARD8', 1, 'bitmap_format_scanline_pad'),
                             XData('CARD8', 1, 'min_keycode'),
                             XData('CARD8', 1, 'max_keycode'),
                             XData('PAD', 4, 'unused_2'),
                             XData('STRING8', 'sz_vendor', 'vendor'))

        self.Success = x_reply['Success']
        self.unused_1 = x_reply['unused_1']
        self.protocol_major_version = x_reply['protocol_major_version']
        self.protocol_minor_version = x_reply['protocol_minor_version']
        self.sz_additional = x_reply['sz_additional']
        self.release_number = x_reply['release_number']
        self.resource_id_base = x_reply['resource_id_base']
        self.resource_id_mask = x_reply['resource_id_mask']
        self.motion_buffer_size = x_reply['motion_buffer_size']
        self.sz_vendor = x_reply['sz_vendor']
        self.maximum_request_length = x_reply['maximum_request_length']
        self.n_SCREENS = x_reply['n_SCREENS']
        self.n_FORMATS = x_reply['n_FORMATS']
        self.image_byte_order = x_reply['image_byte_order']
        self.bitmap_format_bit_order = x_reply['bitmap_format_bit_order']
        self.bitmap_format_scanline_unit = x_reply['bitmap_format_scanline_unit']
        self.bitmap_format_scanline_pad = x_reply['bitmap_format_scanline_pad']
        self.min_keycode = x_reply['min_keycode']
        self.max_keycode = x_reply['max_keycode']
        self.unused_2 = x_reply['unused_2']
        self.vendor = x_reply['vendor']

        self.pixmap_formats = []
        for p in range(self.n_FORMATS):
            pfe, ad = decode(ad, XData('CARD8', 1, 'depth'),
                             XData('CARD8', 1, 'bits_per_pixel'),
                             XData('CARD8', 1, 'scanline_pad'),
                             XData('PAD', 5, 'unused'))
            self.pixmap_formats.append(pfe)

        self.roots = []
        for s in range(self.n_SCREENS):
            se, ad = decode(ad, XData('CARD32', 1, 'root'),
                            XData('CARD32', 1, 'default_colormap'),
                            XData('CARD32', 1, 'white_pixel'),
                            XData('CARD32', 1, 'black_pixel'),
                            XData('CARD32', 1, 'current_input-masks'),
                            XData('CARD16', 1, 'width_in_pixels'),
                            XData('CARD16', 1, 'height_in_pixels'),
                            XData('CARD16', 1, 'width_in_millimeters'),
                            XData('CARD16', 1, 'height_in_millimeters'),
                            XData('CARD16', 1, 'min_installed_maps'),
                            XData('CARD16', 1, 'max_installed_maps'),
                            XData('CARD32', 1, 'root_visual'),
                            XData('CARD8', 1, 'backing_stores'),
                            XData('CARD8', 1, 'save_unders'),
                            XData('CARD8', 1, 'root_depth'),
                            XData('CARD8', 1, 'n_allowed_depths'))

            se['allowed_depths'] = []
            for d in range(se['n_allowed_depths']):
                de, ad = decode(ad, XData('CARD8', 1, 'depth'),
                                XData('PAD', 1, 'unused_1'),
                                XData('CARD16', 1, 'n_VISUALTYPES'),
                                XData('PAD', 4, 'unused_2'))

                de['visuals'] = []
                for v in range(de['n_VISUALTYPES']):
                    ve, ad = decode(ad, XData('CARD32', 1, 'visual_id'),
                                    XData('CARD8', 1, 'class'),
                                    XData('CARD8', 1, 'bits_per_rgb_value'),
                                    XData('CARD16', 1, 'colormap_entries'),
                                    XData('CARD32', 1, 'red_mask'),
                                    XData('CARD32', 1, 'green_mask'),
                                    XData('CARD32', 1, 'blue_mask'),
                                    XData('PAD', 4, 'unused'))

                    de['visuals'].append(ve)
                se['allowed_depths'].append(de)

            self.roots.append(se)


class XConnectAuthenticateReply:
    """reply sent by secured servers to request client authentication.
    authentication procedures are not defined by the X protcol, so the
    way to handle this one is outside an X protocol interface. Should
    probably raise some kind of exception if unhandled"""

    def __init__(self, encoding: bytes) -> None:
        x_reply, ad = decode(encoding,
                             XData('BYTE', 1, 'Authenticate'),
                             XData('PAD', 5, 'unused'),
                             XData('CARD16', 1, 'sz_additional'))

        for n, v in x_reply.items():
            setattr(self, n, v)

        rs, ad = decode(ad,
                        XData('STRING8', self.xdata['sz_additional'] * 4, 'reason'))
        self.reason = rs['reason']


###############################################################################
# QueryExtension request and reply - opcode 98
#
class XQueryExtensionRequest:
    """this class wraps the X Protocol Query Extension request. it
    requires the name of the extension to look for as a constructor arg"""

    def __init__(self, exname):
        self.encoding = encode(XData('CARD8', 1, 98),
                               XData('PAD', 1, 0),
                               XData('CARD16', 1, 2 + ((len(exname) + (len(exname) % 4)) // 4)),
                               XData('CARD16', 1, len(exname)),
                               XData('PAD', 2, [0, 0]),
                               XData('STRING8', len(exname), exname))


class XQueryExtensionReply:
    """the reply to a Query Extension request. if attr present is
    0, the extension isn't there. if present is 1, extension exists
    and the extension opcode, base error, and base event are returned"""

    def __init__(self, encoding: bytes) -> None:
        x_reply, ad = decode(encoding,
                             XData('CARD8', 1, 'reply'),
                             XData('PAD', 1, 'unused_1'),
                             XData('CARD16', 1, 'sequence_number'),
                             XData('CARD32', 1, 'reply_length'),
                             XData('CARD8', 1, 'present'),
                             XData('CARD8', 1, 'major_opcode'),
                             XData('CARD8', 1, 'first_event'),
                             XData('CARD8', 1, 'first_error'),
                             XData('PAD', 20, 'unused_2'))
        self.reply = x_reply['reply']
        self.unused_1 = x_reply['unused_1']
        self.sequence_number = x_reply['sequence_number']
        self.reply_length = x_reply['reply_length']
        self.present = x_reply['present']
        self.major_opcode = x_reply['major_opcode']
        self.first_event = x_reply['first_event']
        self.first_error = x_reply['first_error']
        self.unused_2 = x_reply['unused_2']


###############################################################################
# ListExtensions request and reply - opcode 99
#
class XListExtensionsRequest:
    """this class wraps the X List Extensions request"""

    def __init__(self) -> None:
        self.encoding = encode(XData('CARD8', 1, 99),
                               XData('PAD', 1, 0),
                               XData('CARD16', 1, 1))


class XListExtensionsReply:
    """this class wraps the X List Extensions reply. it contains
    the extensions as a list of strings, as well as the number
    of strings in the list and the sequence number of request"""

    def __init__(self, encoding: bytes) -> None:
        x_reply, ad = decode(encoding,
                             XData('CARD8', 1, 'reply'),
                             XData('CARD8', 1, 'n_STRs'),
                             XData('CARD16', 1, 'sequence_number'),
                             XData('CARD32', 1, 'reply_length'),
                             XData('PAD', 24, 'unused'))

        for n, v in x_reply.items():
            setattr(self, n, v)

        self.names: List[str] = []
        for s in range(x_reply['n_STRs']):
            sz = struct.unpack('B', ad[:1])[0]
            self.names.append(str(ad[1:sz + 1]))
            ad = ad[sz + 1:]


###############################################################################
# Procedures to use the request classes to get info, etc
#
def x_change(x_socket: socket.socket, request: Any) -> bytes:
    try:
        x_socket.send(request.encoding)
        x_reply = x_socket.recv(65535)  # TODO make sure it fits

    except socket.error as err:
        raise xnet.XConnectionError('Network error: %s' % err)

    return x_reply


def x_connect() -> Tuple[socket.socket, Any]:
    name, host, display_number, screen_number = xnet.get_x_display()
    x_socket = xnet.get_x_socket(host, display_number)
    auth_name, auth_data = xnet.get_x_auth(x_socket, host, display_number)
    byte_order = xnet.get_x_byteorder()

    request = XConnectRequest(byte_order, 11, 0, auth_name, auth_data)

    x_reply = x_change(x_socket, request)

    if x_reply[0] == 0:
        repobj = XConnectRefusedReply(x_reply)
        raise xnet.XConnectionError(repobj.reason)

    elif x_reply[0] == 1:
        repobj = XConnectAcceptedReply(x_reply)

    elif x_reply[0] == 2:
        repobj = XConnectAuthenticateReply(x_reply)
        raise xnet.XConnectionError(repobj.reason)
    else:
        raise xnet.XConnectionError('Unknown connection failure')

    return x_socket, repobj


def x_list_extensions(x_sock):
    rq = XListExtensionsRequest()
    binrp = x_change(x_sock, rq)

    if binrp[0] == 0:
        raise XServerError(binrp)
    else:
        return XListExtensionsReply(binrp)


def x_query_extension(x_sock, exname):
    rq = XQueryExtensionRequest(exname)
    binrp = x_change(x_sock, rq)

    if binrp[0] == 0:
        if binrp[1] > 0 and binrp[1] <= 17:
            raise XServerError(binrp)

    return XQueryExtensionReply(binrp)
