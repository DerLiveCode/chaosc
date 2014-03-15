# cython: profile=False,infer_types=True
# encoding: utf-8

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

from __future__ import absolute_import

import types, time

from math import ceil, modf
from struct import pack, unpack
from copy import deepcopy
from itertools import izip

__all__ = ["OSCError", "OSCBundleFound", "OSCMessage", "OSCBundle", "decode_osc",
    "proxy_decode_osc", "encode_string"]

class OSCError(Exception):
    """Base Class for all OSC-related errors
    """
    pass


class OSCBundleFound(Exception):
    """Marker Class for OSC Bundles
    """
    pass

float_types = [types.FloatType]

int_types = [types.IntType]

from calendar import timegm
NTP_epoch = timegm((1900, 1, 1, 0, 0, 0)) # NTP time started in 1 Jan 1900
del timegm

NTP_units_per_second = 0x100000000 # about 232 picoseconds

try:
    from numpy import typeDict
    for ftype in ['float32', 'float64', 'float128']:
        try:
            float_types.append(typeDict[ftype])
        except KeyError:
            pass

    for itype in ['int8', 'int16', 'int32', 'int64']:
        try:
            int_types.append(typeDict[itype])
            int_types.append(typeDict['u' + itype])
        except KeyError:
            pass

    del typeDict, ftype, itype
except ImportError:
    pass


cpdef inline str get_type_tag(object argument):
    ta = type(argument)
    if ta in float_types:
        return 'f'
    elif ta in int_types:
        return 'i'
    else:
        return 's'



cpdef inline str encode_string(str argument):
    return pack(">%ds" % int(ceil((len(argument)+1) / 4.0) * 4), argument)


cpdef inline str encode_blob(str argument):
    """Convert a string into an OSC Blob.
    An OSC-Blob is a binary encoded block of data, prepended by a 'size' (int32).
    The size is always a mutiple of 4 bytes.
    The blob ends with 0 to 3 zero-bytes ('\x00')
    """

    if isinstance(argument, basestring):
        length = ceil((len(argument)) / 4.0) * 4
        return pack(">i%ds" % length, length, argument)
    else:
        return ""


cpdef inline str encode_timetag(float timestamp):
    """Convert a time in floating seconds to its
    OSC binary representation
    """
    cdef float fract
    cdef float secs

    if timestamp > 0.:
        fract, secs = modf(time)
        secs = secs - NTP_epoch
        return pack('>LL', long(secs), long(fract * NTP_units_per_second))
    else:
        return pack('>LL', 0L, 1L)


cpdef inline tuple decode_string(str data, int start, int end):
    """Reads the next (null-terminated) block of data
    """
    end = data.find('\0', start)
    nextData = int(ceil(0.25 * (end+1)) * 4)
    return data[start:end], nextData


cpdef inline tuple decode_blob(str data, int start, int end):
    """Reads the next (numbered) block of data
    """

    cdef int blob_start
    cdef int length
    cdef int nextData

    blob_start = start + 4
    length = unpack(">i", data[start:blob_start])[0]
    nextData = blob_start + int(ceil((length) / 4.0) * 4)
    return data[blob_start:nextData], nextData


cpdef inline tuple decode_int(str data, int start, int end):
    """Tries to interpret the next 4 bytes of the data
    as a 32-bit integer. """

    if end - start < 4:
        raise ValueError("Error: too few bytes for int", data, end)

    end = start + 4
    return unpack(">i", data[start:end])[0], end


cpdef inline tuple decode_long(str data, int start, int end):
    """Tries to interpret the next 8 bytes of the data
    as a 64-bit signed integer.
        """

    cdef int big
    cdef int high
    cdef int low

    end = start + 8
    high, low = unpack(">ll", data[start:end])
    big = (long(high) << 32) + low
    return big, end


cpdef inline tuple decode_timetag(str data, int start, int end):
    """Tries to interpret the next 8 bytes of the data
    as a TimeTag.
    """

    cdef int high
    cdef int low

    end = start + 8
    high, low = unpack(">LL", data[start:end])
    if (high == 0) and (low <= 1):
        return 0.0, end
    else:
        return int(NTP_epoch + high) + float(low / NTP_units_per_second), end


cpdef inline tuple decode_float(str data, int start, int end):
    """Tries to interpret the next 4 bytes of the data
    as a 32-bit float.
    """

    if end - start < 4:
        raise ValueError("Error: too few bytes for float", data, end)

    end = start + 4
    return unpack(">f", data[start:end])[0], end


cpdef inline tuple decode_double(str data, int start, int end):
    """Tries to interpret the next 8 bytes of the data
    as a 64-bit float.
    """

    if end - start < 8:
        raise ValueError("Error: too few bytes for double", data, end)

    end = start + 8
    return unpack(">d", data[start:end])[0], end


cpdef tuple decode_osc(str data, int start, int end):
    """Converts a binary OSC message to a Python list.
    """
    #table = _table
    cdef int len_args
    cdef int i

    if end == 0:
        raise OSCError("empty")

    args = list()
    typetags = None
    rest = start
    address, rest = decode_string(data, rest, end)
    if address.startswith(","):
        typetags = address
        address = ""

    if address == "#bundle":
        typetags, rest = decode_timetag(data, rest, end)
        while rest - end:
            length, rest = decode_int(data, rest, end)
            new_end = rest + length
            args.append(decode_osc(data, rest, new_end))
            rest = new_end
    elif rest - end:
        if typetags is None:
            typetags, rest = decode_string(data, rest, end)

        if not typetags.startswith(","):
            raise OSCError("OSCMessage's typetag-string lacks the magic ','")

        typetags = list(typetags[1:])
        len_typetags = len(typetags)

        for i in range(len_typetags):
            typetag = typetags[i]
            if typetag == "i":
                argument, rest = decode_int(data, rest, end)
            elif typetag == "s":
                argument, rest = decode_string(data, rest, end)
            elif typetag == "f":
                argument, rest = decode_float(data, rest, end)
            elif typetag == "b":
                argument, rest = decode_blob(data, rest, end)
            elif typetag == "d":
                argument, rest = decode_double(data, rest, end)
            elif typetag == "t":
                argument, rest = decode_timetag(data, rest, end)
            else:
                raise OSCError("unknown typetag %r" % typetag)
            args.append(argument)

    return address, typetags, args


cpdef tuple proxy_decode_osc(str data, int start, int end):
    """Converts a binary OSC message to a Python list.
    """
    #table = _table
    cdef int len_args
    cdef int i

    if end == 0:
        raise OSCError("empty")

    args = list()
    typetags = None
    rest = start
    address, rest = decode_string(data, rest, end)
    if address.startswith(","):
        typetags = address
        address = ""

    if address == "#bundle":
        raise OSCBundleFound()
    elif rest - end:
        if typetags is None:
            typetags, rest = decode_string(data, rest, end)

        if not typetags.startswith(","):
            raise OSCError("OSCMessage's typetag-string lacks the magic ','")

        typetags = list(typetags[1:])
        len_typetags = len(typetags)

        for i in range(len_typetags):
            typetag = typetags[i]
            if typetag == "i":
                argument, rest = decode_int(data, rest, end)
            elif typetag == "s":
                argument, rest = decode_string(data, rest, end)
            elif typetag == "f":
                argument, rest = decode_float(data, rest, end)
            elif typetag == "b":
                argument, rest = decode_blob(data, rest, end)
            elif typetag == "d":
                argument, rest = decode_double(data, rest, end)
            elif typetag == "t":
                argument, rest = decode_timetag(data, rest, end)
            else:
                raise OSCError("unknown typetag %r" % typetag)
            args.append(argument)

    return address, typetags, args



cdef class OSCMessage(object):
    """ Builds typetagged OSC messages.

    OSCMessage objects are container objects for building OSC-messages.
    On the 'front' end, they behave much like list-objects, and when needed
    they generate a OSC 1.1 spec compliant binary representation.

    OSC-messages consist of an 'address'-string
    (not to be confused with a (host, port) IP-address!), followed by a string
    of 'typetags' which indicates the arguments' types,
    and finally the arguments themselves, encoded in an OSC-specific way.

    On the Python end, OSCMessage are lists of arguments, prepended by the
    message's address. The message contents can be manipulated much like a list:

    >>> msg = OSCMessage("/my/osc/address")
    >>> msg.append('something')
    >>> msg.insert(0, 'something else')
    >>> msg[1] = 'entirely'
    >>> msg.extend([1,2,3.])
    >>> msg.appendTypedArg(4, "i")
    >>> msg += 5
    >>> msg += 6.
    >>> del msg[3:6]
    >>> msg.pop(-2)
    5
    >>> print msg
    /my/osc/address ['something else', 'entirely', 1, 6.0]
    >>> binary = msg.encode_osc()
    >>> print repr(binary)
    '/my/osc/address\\x00,ssif\\x00\\x00\\x00something else\\x00\\x00entirely\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x01@\\xc0\\x00\\x00'
    >>> msg2 = decode_osc(binary, 0, len(binary))
    >>> print repr(msg2)
    ('/my/osc/address', ['s', 's', 'i', 'f'], ['something else', 'entirely', 1, 6.0])

    To construct an 'OSC-bundle' from multiple OSCMessage, see OSCBundle!

    Additional methods exist for retrieving typetags or manipulating items as (typetag, value) tuples.
    """

    cdef public str address
    cdef public list typetags
    cdef public list args

    def __init__(self, address):
        """Instantiate a new OSCMessage.
        The OSC-address can be specified with the 'address' argument.
        The rest of the arguments are appended as data.
        """
        super(OSCMessage, self).__init__()
        self.address = address
        self.typetags = list()
        self.args = list()

    def __repr__(self):
        """Returns a string containing the decode Message
        """
        return "OSCMessage(%r, %r, %r)" % (self.address, self.typetags, self.args)

    def __str__(self):
        """Returns the Message's address and contents as a string.
        """
        return "%s %s" % (self.address, str(self.args))

    def __len__(self):
        """Returns the number of arguments this message contains
        """
        return len(self.typetags)

    def __richcmp__(self, other, cmd):
        if cmd == 2:
            if not isinstance(other, OSCMessage):
                return False

            return (self.address == other.address and
                self.typetags == other.typetags and
                self.args == other.args)

        elif cmd == 3:
            if isinstance(other, OSCMessage):
                return False

            return (self.address != other.address or
                self.typetags != other.typetags or
                self.args != other.args)

    def __add__(self, value):
        """Returns a copy of self, with the 'value'
        """
        msg = deepcopy(self)
        msg.append(value)
        return msg

    def __iadd__(self, arguments):
        """Appends the contents of 'arguments'
        (equivalent to 'extend()', below)
        Returns self
        """
        self.append(arguments)
        return self

    def __contains__(self, arguments):
        """Test if the given value appears in the OSCMessage's arguments
        """
        return arguments in self.args

    def __getitem__(self, index):
        """Returns the indicated argument (or slice)
        """
        return self.args.__getitem__(index)

    def __delitem__(self, i):
        """Removes the indicated argument
        """
        self.args.__delitem__(i)
        self.typetags.__delitem__(i)

    def __delslice__(self, i, j):
        """Removes the indicated slice
        """
        self.args.__delslice__(i, j)
        self.typetags.__delslice__(i, j)

    def __setitem__(self, index, arguments):
        """Set indicatated argument (or slice) to a new value.
        'val' can be a single int/float/string, or a (typehint, value) tuple.
        Or, if 'i' is a slice, a list of these or another OSCMessage.
        """

        self.args.__setitem__(index, arguments)
        self.typetags.__setitem__(index, get_type_tag(arguments))

    def __iter__(self):
        """Returns an iterator of the OSCMessage's arguments
        """
        return self.args.__iter__()

    def __reversed__(self):
        """Returns a reverse iterator of the OSCMessage's arguments
        """
        return self.args.__reversed__()

    def setAddress(self, address):
        """Set or change the OSC-address
        """
        self.address = address

    def clear(self, address=""):
        """clears all attributes to factory state
        """
        self.address  = address
        self.typetags = list()
        self.args  = list()

    def append(self, argument):
        """Appends _one_ argument to the message, updating the typetags based on
        the argument's type. If the argument is a blob (counted
        string) pass in 'b' as typehint.
        """

        self.typetags.append(get_type_tag(argument))
        self.args.append(argument)

    def appendTypedArg(self, argument, str typehint):
        """Appends data to the message, updating the typetags based on
        the argument's type. If the argument is a blob (counted
        string) pass in 'b' as typehint.
        """

        self.typetags.append(typehint)
        self.args.append(argument)

    def values(self):
        """Returns a list of the arguments appended so far
        """
        return self.args

    def tags(self):
        """Returns a list of typetags of the appended arguments
        """
        return self.typetags

    def items(self):
        """Returns a list of (typetag, value) tuples for
        the arguments appended so far
        """
        return zip(self.typetags, self.args)

    def count(self, val):
        """Returns the number of times the given value occurs in the OSCMessage's arguments
        """
        return self.args.count(val)

    def index(self, val):
        """Returns the index of the first occurence of the given value in the OSCMessage's arguments.
        Raises ValueError if val isn't found
        """
        return self.args.index(val)

    def extend(self, arguments):
        """Append the contents of 'arguments' to this OSCMessage.
        'values' a list/tuple of ints/floats/strings
        """
        for argument in arguments:
            self.typetags.append(get_type_tag(argument))
            self.args.append(argument)

    def extendTypedArgs(self, typetags, arguments):
        """Append the contents of 'values' to this OSCMessage.
        'values' a list/tuple of ints/floats/strings
        """

        self.typetags.extend(typetags)
        self.args.extend(arguments)

    def insert(self, i, val, typehint=None):
        """Insert given value (with optional typehint) into the OSCMessage
        at the given index.
        """

        typehint = typehint is None and get_type_tag(val) or typehint
        self.typetags.insert(i, typehint)
        self.args.insert(i, val)

    def popitem(self, int i):
        """Delete the indicated argument from the OSCMessage, and return it
        as a (typetag, value) tuple.
        """
        return (self.typetags.pop(i), self.args.pop(i))

    def pop(self, int i):
        """Delete the indicated argument from the OSCMessage, and return it.
        """
        self.typetags.pop(i)
        return self.args.pop(i)

    def reverse(self):
        """Reverses the arguments of the OSCMessage (in place)
        """
        self.args.reverse()
        self.typetags.reverse()

    def remove(self, val):
        """Removes the first argument with the given value from the OSCMessage.
        Raises ValueError if val isn't found.
        """
        try:
            ix = self.args.index(val)
            self.args.pop(ix)
            self.typetags.pop(ix)
        except IndexError:
            raise ValueError("argument not found")

    cpdef str encode_osc(self):
        """Returns the binary representation of the message
        """

        cdef list tmp
        cdef int len_typetags
        cdef int i

        tmp = []
        len_typetags = len(self.typetags)
        for i in range(len_typetags):
            typetag = self.typetags[i]
            argument = self.args[i]
            if typetag == "s":
                tmp.append(encode_string(argument))
            elif typetag == 'i':
                tmp.append(pack(">i", argument))
            elif typetag == 'f':
                tmp.append(pack(">f", argument))
            elif typetag == 'b':
                tmp.append(encode_blob(argument))
            elif typetag == 'd':
                tmp.append(pack(">d", argument))
            elif typetag == 't':
                tmp.append(encode_timetag(argument))
            else:
                raise TypeError("unknown typetag %r" % typetag)

        return "%s%s%s" % (
            encode_string(self.address),
            encode_string(",%s" % "".join(self.typetags)),
            "".join(tmp))



cdef class OSCBundle(object):
    """Builds a 'bundle' of OSC messages.

    OSCBundle objects are container objects for building OSC-bundles of OSC-messages.
    An OSC-bundle is a special kind of OSC-message which contains a list of OSC-messages
    (And yes, OSC-bundles may contain other OSC-bundles...)

    OSCBundle objects behave much the same as OSCMessage objects, with these exceptions:
        - if an item or items to be appended or inserted are not OSCMessage objects,
        OSCMessage objects are created to encapsulate the item(s)
        - an OSC-bundle does not have an address of its own, only the contained OSC-messages do.
        The OSCBundle's 'address' is inherited by any OSCMessage the OSCBundle object creates.
        - OSC-bundles have a timetag to tell the receiver when the bundle should be processed.
        The default timetag value (0) means 'immediately'
    """

    cdef public float timetag
    cdef public list args

    def __init__(self, timetag=0.0):
        """Instantiate a new OSCBundle.
        The default OSC-address for newly created OSCMessages
        can be specified with the 'address' argument
        The bundle's timetag can be set with the 'time' argument
        """
        self.timetag = timetag
        self.args = list()

    def __str__(self):
        """Returns the Bundle's contents (and timetag, if nonzero) as a string.
        """
        return "#bundle%s [%s]" % (self.timetag > 0. and " %s" % self.getTimeTagStr() or "", self.args)

    def setTimeTag(self, time):
        """Set or change the OSCBundle's TimeTag
        In 'Python Time', that's floating seconds since the Epoch
        """
        if time >= 0.:
            self.timetag = time

    def getTimeTagStr(self):
        """Return the TimeTag as a human-readable string
        """
        fract, secs = modf(self.timetag)
        return "%s%s" % (time.ctime(secs)[11:19], ("%.3f" % fract)[1:])

    def append(self, argument):
        """Appends an OSCMessage
        Any newly created OSCMessage inherits the OSCBundle's address at the time of creation.
        If 'argument' is an iterable, its elements will be encapsuated by a single OSCMessage.
        """

        self.args.append(argument)

    def encode_osc(self):
        """Returns the binary representation of the message
        """

        return "%s%s%s" % (
            encode_string("#bundle"),
            encode_timetag(self.timetag),
            "".join([encode_blob(argument.encode_osc())
                for argument in self.args]))

    def __richcmp__(self, other, cmd):
        if cmd == 2:
            if not isinstance(other, OSCBundle):
                return False

            return (self.address == other.address and
                self.typetags == other.typetags and
                self.args == other.args)

        elif cmd == 3:
            if isinstance(other, OSCBundle):
                return False

        return (self.timetag == other.timetag and
            super(OSCBundle, self).__eq__(other))
