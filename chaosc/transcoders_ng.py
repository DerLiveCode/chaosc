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
# Copyright (C) 2014 Stefan Kögl


from operator import itemgetter

import re

try:
    from .c_osc_lib import OSCMessage
except ImportError:
    from .osc_lib  import OSCMessage


class ITranscoder(object):
    """Interface for transcoders"""

    def match(self, osc_address):
        raise NotImplementedError()

    def __call__(self, osc_address, typetags, args):
        raise NotImplementedError()


class IConverter(object):
    """Interface for converters"""

    def __call__(self, value):
        raise NotImplementedError()


class IntConverter(IConverter):
    """converts values to int"""

    def __call__(self, value):
        return int(value)


class FloatConverter(IConverter):
    """converts values to float"""

    def __call__(self, value):
        return float(value)


class StringConverter(IConverter):
    """converts values to strings"""

    def __call__(self, value):
        return str(value)


class KeepConverter(IConverter):
    """does not convert, just returns the value as given"""

    def __call__(self, value):
        return value


class IntRange2FloatConverter(IConverter):
    """converts integer values with a given max value to a float between 0.0-1.0"""

    def __init__(self, max_value):
        self.max_value = max_value

    def __call__(self, value):
        return value / float(self.max_value)


class FloatRange2IntConverter(IConverter):
    """converts float values between 0.0 and 1.0 to an integer in the range 0-max value. This is the opposite conversion to IntRange2FloatConverter"""

    def __init__(self, max_value):
        self.max_value = max_value

    def __call__(self, value):
        return int(value * self.max_value)



class AddressTranscoder(ITranscoder):
    """transcodes osc address"""

    def __init__(self, from_addr, to_addr):
        super(AddressTranscoder, self).__init__()
        self.from_addr = from_addr
        self.to_addr = to_addr

    def match(self, osc_address):
        if osc_address == self.from_addr:
            return True
        return False

    def __call__(self, osc_address, typetags, args):
        new_message = OSCMessage(self.to_addr)
        for arg, typetag in zip(args, typetags):
            new_message.appendTypedArg(arg, typetag)
        return new_message


class DampingTranscoder(ITranscoder):
    """transcodes the values of osc messages with a damping factor"""

    def __init__(self, regrex_fmt, factor):
        super(DampingTranscoder, self).__init__()
        self.regrex_fmt = re.compile(regrex_fmt)
        self.factor = factor

    def match(self, osc_address):
        return self.regrex_fmt.match(osc_address) is not None

    def __call__(self, osc_address, typetags, args):
        new_message = OSCMessage(osc_address)
        for arg, typetag in zip(args, typetags):
            new_message.appendTypedArg(arg * self.factor, typetag)
        return new_message


class AddressRegExChanger(ITranscoder):
    """transcodes osc message addresses to a new address representation and uses match group items in the to_addr format"""

    def __init__(self, regrex_fmt, to_addr):
        super(AddressRegExChanger, self).__init__()
        self.regrex_fmt = re.compile(regrex_fmt)
        self.to_addr = to_addr
        self.groups = None

    def match(self, osc_address):
        try:
            self.groups = self.regrex_fmt.match(osc_address).groups()
            return True
        except AttributeError:
            pass
        self.groups = ()
        return False

    def __call__(self, osc_address, typetags, args):
        new_message = OSCMessage(self.to_addr % tuple([int(item) for item in self.groups]))
        for arg, typetag in zip(args, typetags):
            new_message.appendTypedArg(arg, typetag)
        return new_message


class MappingTranscoder(ITranscoder):
    """fine granular transcoding with regular expression for the osc address, and mapping converters for each argument

    you can exactly specify which value grepped from the regular expression groups or arguments should be used for the
    new message
    """

    def __init__(self, regex_fmt, to_fmt, mappers, **kwargs):
        super(MappingTranscoder, self).__init__()
        self.regex = re.compile(regex_fmt)
        self.to_fmt = to_fmt
        self.mappers = mappers
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
        regrex_args = list()
        osc_args = list()
        for src_origin, src_position, dst_origin, dst_position, transcoder in self.mappers:
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
                osc_args.append((dst_position, transcoder(src)))
            elif dst_origin == "format":
                regrex_args.append((dst_position, transcoder(src)))
            else:
                raise Exception("unknown type key")

        regrex_args.sort(key=itemgetter(0))
        osc_args.sort(key=itemgetter(0))

        new_message = OSCMessage(self.to_fmt.format(*[arg[1] for arg in regrex_args]))

        for pos, value in osc_args:
            new_message.append(value)
        return new_message.encode_osc()
