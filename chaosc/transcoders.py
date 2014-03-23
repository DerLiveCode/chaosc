# -*- coding: utf-8 -*-

# This file is part of chaosc
#
# chaosc is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# chaosc is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with chaosc.  If not, see <http://www.gnu.org/licenses/>.
# 
# Copyright (C) 2012-2013 Stefan Kögl


from operator import itemgetter

import re

try:
    from .c_osc_lib import OSCMessage
except ImportError:
    from .osc_lib  import OSCMessage


__all__ = ["ITranscoderHandler",
    "AddressChanger",
    "DampValue",
    "AddressRegExChanger",
    "MidiChanger",
    "midi_converter",
]


def midi_converter(transcoder, value):
    return int(value * 127)

def int_converter(transcoder, value):
    return int(value)

def float_converter(transcoder, value):
    return float(value)

def str_converter(transcoder, value):
    return str(value)

def unicode_converter(transcoder, value):
    return str(value)

converters = {
    "midi" : midi_converter,
    "int" : int_converter,
    "float" : float_converter,
    "str" : str_converter,
    "unicode" : unicode_converter}


class ITranscoderHandler(object):

    def match(self, msg):
        raise NotImplementedError()

    def __call__(self, client, msg):
        raise NotImplementedError()


class AddressChanger(ITranscoderHandler):
    def __init__(self, from_addr, to_addr):
        super(AddressChanger, self).__init__()
        self.from_addr = from_addr
        self.to_addr = to_addr

    def match(self, msg):
        if msg.address == self.from_addr:
            return True
        return False

    def __call__(self, client, msg):
        new_message = msg.copy()
        new_message.address = self.to_addr
        return new_message


class DampValue(ITranscoderHandler):
    def __init__(self, fmt, factor):
        super(DampValue, self).__init__()
        self.fmt = re.compile(fmt)
        self.factor = factor

    def match(self, osc_address):
        return self.fmt.match(osc_address) is not None

    def __call__(self, client, msg):
        new_message = OSCMessage(msg.address)
        data = list(msg.items())
        out = list()
        for tag, value in data:
            out.append((tag, value * self.factor))
        new_message.extend(out)
        return new_message


class AddressRegExChanger(ITranscoderHandler):
    def __init__(self, fmt, to):
        super(AddressRegExChanger, self).__init__()
        self.fmt = re.compile(fmt)
        self.to_addr = to
        self.groups = None

    def match(self, osc_):
        try:
            self.groups = self.fmt.match(osc_).groups()
            return True
        except AttributeError:
            pass
        self.groups = ()
        return False

    def __call__(self, client, msg):
        new_message = msg.copy()
        new_message.address = self.to_addr % tuple(map(int, self.groups))
        return new_message


class MidiChanger(ITranscoderHandler):
    def __init__(self, regex, to_fmt, mapper, **kwargs):
        super(MidiChanger, self).__init__()
        self.regex = re.compile(regex)
        self.to_fmt = to_fmt
        self.mapper = mapper
        self.groups = None
        self.members = kwargs

    def match(self, osc_address):
        try:
            self.groups = self.regex.match(osc_address).groups()
            return True
        except AttributeError:
            pass
        self.groups = ()
        return False

    def __call__(self, osc_address, tags, args):
        fmt_args = list()
        osc_args = list()
        for src_origin, src_position, dst_origin, dst_position, converter in self.mapper:
            src = None
            if src_origin == "member":
                src = self.members[src_position]
            elif src_origin == "regex":
                src = self.groups[src_position]
            elif src_origin == "osc_arg":
                src = args[src_position]
            else:
                raise Exception("unknown type key" % src_origin)

            if dst_origin == "osc_arg":
                osc_args.append((dst_position, converters[converter](self, src)))
            elif dst_origin == "format":
                fmt_args.append((dst_position, converters[converter](self, src)))
            else:
                raise Exception("unknown type key")

        fmt_args.sort(key=itemgetter(0))
        osc_args.sort(key=itemgetter(0))

        new_message = OSCMessage(self.to_fmt.format(*list(map(itemgetter(1), fmt_args))))

        for pos, value in osc_args:
            new_message.append(value)
        return new_message.encode_osc()
