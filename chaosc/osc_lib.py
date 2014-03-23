# -*- coding: utf-8 -*-
"""
This is a pure python osc lib implementation. This software is based on OSC.py,
but was heavily modified and streamlined. There is also a cython based
implementation, which should be prefered named c_osc_lib.pyx.

Use this import statement to be sure to get the c lib::

    try:
        from chaosc.c_osc_lib import *
    except ImportError:
        from chaosc.osc_lib import *


Usage
_____


To use this library, you should have some basic knowledge how the OSC container
format works. An OSCMessage is like a binary container or a list.
It has a header, and some optional payload of heterogenous data. You can store
arguments in the payload, but not OSCMessages. There also are OSCBundles.
These are defined recursively as a container of OSCBundles and or OSCMessages.
Never put an OSCMessage in an OSCMessage or a raw argument in an OSCBundle.

Supported argument types
________________________

    * 32 bit integer
    * 32-bit float
    * 64-bit long
    * 64-bit double
    * variable length string with length annotation
    * variable length blob with length annotation


"""

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



import types, time

from math import ceil, modf
from struct import pack, unpack
from copy import deepcopy



__all__ = ["OSCError", "OSCBundleFound", "OSCMessage", "OSCBundle",
    "proxy_decode_osc", "encode_string", "decode_osc", "decode_string"]

class OSCError(Exception):
    """Base Class for all OSC-related errors
    """
    pass


class OSCBundleFound(Exception):
    """Marker Class for OSC Bundles
    """
    pass


float_types = [float]

IntTypes = [int]

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
            IntTypes.append(typeDict[itype])
            IntTypes.append(typeDict['u' + itype])
        except KeyError:
            pass

    del typeDict, ftype, itype
except ImportError:
    pass



def get_type_tag(argument):
    """Infers the typetag for an OSCMessage argument

    :param argument: the object to infer

    :rtype: str
    """

    ta = type(argument)
    if ta in float_types:
        return b'f'
    elif ta in IntTypes:
        return b'i'
    else:
        return b's'


def encode_string(argument):
    """Convert a string into a zero-padded OSC String.
    The length of the resulting string is always a multiple of 4 bytes.
    The string ends with 1 to 4 zero-bytes ('\x00')

    :param argument: the string to encode
    :type argument: str

    :rtype: str
    """

    return pack(">%ds" % (ceil((len(argument)+1) / 4.0) * 4), argument)


def encode_blob(argument):
    """Convert a string into an OSC Blob.
    An OSC-Blob is a binary encoded block of data, prepended by a 'size' (int32).
    The size is always a mutiple of 4 bytes.
    The blob ends with 0 to 3 zero-bytes ('\x00')

    :param argument: the blob to encode
    :type argument: str

    :rtype: str
    """

    if isinstance(argument, bytes):
        length = ceil((len(argument)) / 4.0) * 4
        return pack(">i%ds" % length, length, argument)
    else:
        return b""


def encode_timetag(timestamp):
    """Convert a time in floating seconds to its
    OSC binary representation

    :param argument: the time to encode
    :type argument: float

    :rtype: str
    """

    if timestamp > 0:
        fract, secs = modf(timestamp)
        secs = secs - NTP_epoch
        return pack('>LL', int(secs), int(fract * NTP_units_per_second))
    else:
        return pack('>LL', 0, 1)




def decode_string(data, start, end):
    """Reads the next (null-terminated) block of data

    :param data: the binary representation of an osc message
    :type data: str

    :param start: position to start parsing
    :type start: int

    :param end: length of data
    :type end: int

    :returns: the string and the start position of remaining data
    :rtype: str, int
    """
    end = bytearray(data).find(b"\0", start)
    nextData = int(ceil(0.25 * (end+1)) * 4)
    return data[start:end], nextData


def decode_blob(data, start, end):
    """Reads the next (numbered) block of data

    :param data: the binary representation of an osc encoded blob
    :type data: str

    :param start: position to start parsing
    :type start: int

    :param end: length of data
    :type end: int

    :returns: the blob string and the start position of remaining data
    :rtype: str, int
    """

    blob_start = start + 4
    length = unpack(">i", data[start:blob_start])[0]
    nextData = int(blob_start + int(ceil((length) / 4.0) * 4))
    return data[blob_start:nextData], nextData


def decode_int(data, start, end):
    """Tries to interpret the next 4 bytes of the data
    as a 32-bit integer.

    :param data: the binary representation of an osc message
    :type data: str

    :param start: position to start parsing
    :type start: int

    :param end: length of data
    :type end: int

    :returns: the integer and the start position of remaining data
    :rtype: int, int
    """

    if end - start < 4:
        raise ValueError("Error: too few bytes for int", data, end)

    end = start + 4
    return unpack(">i", data[start:end])[0], end


def decode_long(data, start, end):
    """Tries to interpret the next 8 bytes of the data
    as a 64-bit signed integer.

    :param data: the binary representation of an osc message
    :type data: str

    :param start: position to start parsing
    :type start: int

    :param end: length of data
    :type end: int

    :returns: the long integer and the start position of remaining data
    :rtype: long, int
    """

    end = start + 8
    return unpack(">q", data[start:end]), end


def decode_timetag(data, start, end):
    """Tries to interpret the next 8 bytes of the data
    as a TimeTag.

    :param data: the binary representation of an osc message
    :type data: str

    :param start: position to start parsing
    :type start: int

    :param end: length of data
    :type end: int

    :returns: the timetag as a float seconds since epoch and the start position
        of remaining data
    :rtype: float, int
    """

    end = start + 8
    high, low = unpack(">LL", data[start:end])
    if (high == 0) and (low <= 1):
        return 0.0, end
    else:
        return int(NTP_epoch + high) + float(low / NTP_units_per_second), end


def decode_float(data, start, end):
    """Tries to interpret the next 4 bytes of the data
    as a 32-bit float.

    :param data: the binary representation of an osc message
    :type data: str

    :param start: position to start parsing
    :type start: int

    :param end: length of data
    :type end: int

    :returns: the float number and the start position of remaining data
    :rtype: float, int
    """

    if end - start < 4:
        raise ValueError("Error: too few bytes for float", data, end)

    end = start + 4
    return unpack(">f", data[start:end])[0], end


def decode_double(data, start, end):
    """Tries to interpret the next 8 bytes of the data
    as a 64-bit float.

    :param data: the binary representation of an osc message
    :type data: str

    :param start: position to start parsing
    :type start: int

    :param end: length of data
    :type end: int

    :returns: the doube value and the start position of remaining data
    :rtype: double, int
    """

    if end - start < 8:
        raise ValueError("Error: too few bytes for double", data, end)

    end = start + 8
    return unpack(">d", data[start:end])[0], end


def decode_osc(data, start, end):
    """Converts a binary OSC message to a Python list.

    :param data: the binary representation of an osc message
    :type data: str

    :param start: position to start parsing
    :type start: int

    :param end: length of data
    :type end: int

    :returns: osc_address, typetags, args
    :rtype: tuple
    """

    if end == 0:
        raise OSCError("empty")

    args = list()
    typetags = None
    rest = start
    address, rest = decode_string(data, rest, end)
    if address[0:1] == b",":
        typetags = address
        address = ""

    if address == b"#bundle":
        typetags, rest = decode_timetag(data, rest, end)
        while rest - end:
            length, rest = decode_int(data, rest, end)
            new_end = rest + length
            args.append(decode_osc(data, rest, new_end))
            rest = new_end
    elif rest - end:
        if typetags is None:
            typetags, rest = decode_string(data, rest, end)

        print(typetags)
        if typetags[0:1] != b",":
            raise OSCError("OSCMessage's typetag-string lacks the magic ','")

        len_typetags = len(typetags)

        typetags = [typetags[i:i+1] for i in range(1,  len_typetags)]
        print("typetags", typetags)
        len_typetags -= 1
        print("len_typetags", len_typetags)

        for i in range(len_typetags):
            typetag = typetags[i]
            print("typetag", typetag)
            if typetag == b"i":
                print("before i", data, rest, end)
                argument, rest = decode_int(data, rest, end)
                print("argument, rest", argument, rest)
            elif typetag == b"s":
                argument, rest = decode_string(data, rest, end)
            elif typetag == b"f":
                argument, rest = decode_float(data, rest, end)
            elif typetag == b"b":
                argument, rest = decode_blob(data, rest, end)
            elif typetag == b"d":
                argument, rest = decode_double(data, rest, end)
            elif typetag == b"t":
                argument, rest = decode_timetag(data, rest, end)
            else:
                raise OSCError("unknown typetag %r" % typetag)
            args.append(argument)

    return address, typetags, args


def proxy_decode_osc(data, start, end):
    """Converts a binary OSC message to a Python list.
    """

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


class OSCMessage(object):
    """ Builds typetagged OSC messages.

    An OSCMessage is a container object used for construction of osc messages.
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
    >>> msg.appendTypedArg(5, "i")
    >>> msg.append(6.)
    >>> del msg[3:6]
    >>> msg.pop(-2)
    5
    >>> print msg
    /my/osc/address ['something else', 'entirely', 1, 6.0]
    >>> binary = encode_osc(msg)
    >>> print repr(binary)
    '/my/osc/address\\x00,ssif\\x00\\x00\\x00something else\\x00\\x00entirely\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x01@\\xc0\\x00\\x00'
    >>> msg2 = decode_osc(binary, 0, len(binary))
    >>> print repr(msg2)
    ('/my/osc/address', ['s', 's', 'i', 'f'], ['something else', 'entirely', 1, 6.0])

    Additional convenient methods exist for retrieving typetags or manipulating
    items as (typetag, value) tuples.

    It's perfectly ok to directly access the object members, but it's up to you
    to keep typetags and args in sync.

    Best practice for performance is to create your OSCMessage and store the
    binary representation in a variable and reuse it whenever possible. We're
    also played with a simple representation cache, but decided against it.
    It's really simple to implement one with annotations, subclassing or simply
    fork and hack straight into this module.

    .. py:attribute:: address

        string which holds the messages' osc address. This attribute can be
        changed directly.

    .. py:attribute:: typetags

        list which holds the messages' typetags.

    .. py:attribute:: args

        list which holds the messages' arguments.

    To construct a timetagged collection of multiple OSCMessages, see OSCBundle!
    """

    def __init__(self, address):
        """Instantiate a new OSCMessage.
        The OSC-address can be specified with the 'address' argument.
        The rest of the arguments are appended as data.

        :param address: osc address string
        :type address: str
        """
        super(OSCMessage, self).__init__()
        self.address = address
        self.typetags = list()
        self.args = list()

    def __repr__(self):
        """Returns a string containing the decode Message

        :rtype: str
        """
        return "OSCMessage(%r, %r, %r)" % (
            self.address, self.typetags, self.args)

    def __str__(self):
        """Returns the Message's address and contents as a string.

        :rtype: str
        """
        return "%s %s" % (self.address, str(self.args))

    def __len__(self):
        """Returns the number of arguments this message contains

        :rtype: int
        """
        return len(self.typetags)

    def __eq__(self, other):
        """Returns True if two OSCMessages have the same address & content

        :param other: the osc message to compare
        :type other: OSCMessage

        :rtype: bool
        """
        if not isinstance(other, OSCMessage):
            return False

        return (self.address == other.address and
            self.typetags == other.typetags and
            self.args == other.args)

    def __ne__(self, other):
        """Returns True if two OSCMessages have not the same address or content

        :param other: the osc message to compare
        :type other: OSCMessage

        :rtype: bool
        """
        if isinstance(other, OSCMessage):
            return False

        return (self.address != other.address or
            self.typetags != other.typetags or
            self.args != other.args)

    def __contains__(self, argument):
        """Test if the given value appears in the OSCMessage's arguments

        :param argument: the argument to check for presence
        :type argument: str or int or float or double

        :rtype: bool
        """
        return argument in self.args

    def __getitem__(self, index):
        """Returns the indicated argument (or slice)

        :param index: the position
        :type index: int

        :returns: the argument at position 'index'
        :rtype: str or int or float or double
        """
        return self.args.__getitem__(index)

    def __setitem__(self, index, arguments):
        """Set indicatated argument (or slice) to a new value.
        'val' can be a single int/float/string, or a (typehint, value) tuple.
        Or, if 'i' is a slice, a list of these or another OSCMessage.

        :param index: the position
        :type index: int

        :param arguments: the position
        :type arguments: str or int or float or double
        """

        self.args.__setitem__(index, arguments)
        self.typetags.__setitem__(index, get_type_tag(arguments))


    def __delitem__(self, index):
        """Removes the indicated argument

        :param index: the position
        :type index: int
        """
        self.args.__delitem__(index)
        self.typetags.__delitem__(index)


    def __delslice__(self, index, end):
        """Removes the indicated slice

        :param index: the position
        :type index: int

        :param end: the end
        :type end: int
        """
        self.args.__delslice__(index, end)
        self.typetags.__delslice__(index, end)


    def __iter__(self):
        """Returns an iterator of the OSCMessage's arguments

        :rtype: iterator
        """
        return self.args.__iter__()


    def __reversed__(self):
        """Returns a reverse iterator of the OSCMessage's arguments

        :rtype: iterator
        """
        return self.args.__reversed__()

    def clear(self, address=""):
        """clears all attributes to factory state and sets the address

        :param address: osc address
        :type address: str
        """
        self.address  = address
        self.typetags = list()
        self.args  = list()

    def append(self, argument):
        """Appends _one_ argument to the message.

        The typetag is inferred from the argument's type. If the argument is a
        blob (counted string) pass in 'b' as typetag.

        :param argument: a item to store in the message
        :type argument: str or int or float or double
        """

        self.typetags.append(get_type_tag(argument))
        self.args.append(argument)

    def appendTypedArg(self, argument, typetag):
        """Appends a typed argument to the message.

        If the argument is a blob (counted string) pass in 'b' as typetag.
        Prefer this method above :meth:`append`.

        :param argument: the item to store in the message
        :type argument: str or int or float or double

        :param typetag: a 1-char typetag representation defined in osc spec
        :type typetag: str
        """

        self.typetags.append(typetag)
        self.args.append(argument)

    def values(self):
        """Returns a list of the arguments appended so far

        :rtype: list
        """
        return self.args

    def tags(self):
        """Returns a list of typetags of the appended arguments

        :rtype: list of str
        """
        return self.typetags

    def items(self):
        """Returns a list of (typetag, value) tuples for
        the arguments appended so far

        :rtype: list
        """
        return list(zip(self.typetags, self.args))

    def count(self, val):
        """Returns the count a given value occurs in the OSCMessage's arguments

        :rtype: int
        """
        return self.args.count(val)

    def index(self, argument):
        """Returns the index of the first occurence of the given value.

        :param argument: value to find in args
        :type argument: str or int or float or double

        :raises: ValueError if val isn't found
        :rtype: int
        """
        return self.args.index(argument)

    def extend(self, arguments):
        """Append the contents of 'arguments' to this OSCMessage.
        'values' a list/tuple of ints/floats/strings

        :param arguments: the arguments to append
        :type arguments: tuple
        """

        self.args.extend(arguments)
        self.typetags.extend([get_type_tag(argument) for argument in arguments])


    def extendTypedArgs(self, typetags, arguments):
        """Extents this OSCMessage with the given arguments.

        Prefer this method above :meth:`extend`.

        :param typetags: the typetags to append
        :type typetags: tuple

        :param arguments: the arguments to append
        :type arguments: tuple
        """

        self.typetags.extend(typetags)
        self.args.extend(arguments)

    def insert(self, index, argument):
        """Insert given argument into the OSCMessage at the given index.

        The typetag will be inferred.

        :param index: the position
        :type index: int

        :param argument: the argument to insert
        :type argument: str or int or float or double
        """

        typetag = get_type_tag(argument)
        self.typetags.insert(index, typetag)
        self.args.insert(index, argument)

    def insertTypedArg(self, index, argument, typetag):
        """Insert a typed argument at the given index.

        :param index: the position
        :type index: int

        :param argument: the argument to insert
        :type argument: str or int or float or double

        :param typetag: a 1-char typetag representation defined in osc spec
        :type typetag: str
        """

        self.typetags.insert(index, typetag)
        self.args.insert(index, argument)

    def popitem(self, argument):
        """Deletes the given argument from the OSCMessage, and returns it.

        :param argument: the argument to insert
        :type argument: str or int or float or double

        :returns: (typetag, argument)
        :rtype: tuple
        """

        return (self.typetags.pop(argument), self.args.pop(argument))

    def pop(self, argument):
        """Deletes the given argument from the OSCMessage, and returns it.

        :param argument: the argument to insert
        :type argument: str or int or float or double

        :returns: argument
        :rtype: str or int or float or double
        """

        self.typetags.pop(argument)
        return self.args.pop(argument)

    def reverse(self):
        """Reverses the arguments of the OSCMessage (in place)
        """
        self.args.reverse()
        self.typetags.reverse()

    def remove(self, argument):
        """Removes the first argument with the given value from the OSCMessage.

        :param argument: the argument to insert
        :type argument: str or int or float or double

        :rtype: ValueError if argument isn't found.
        """
        try:
            ix = self.args.index(argument)
            self.args.pop(ix)
            self.typetags.pop(ix)
        except IndexError:
            raise ValueError("argument not found")


    def encode_osc(self):
        """Returns the binary representation of the message

        :param self: the OSCMessage to encode
        :type self: OSCMessage

        :rtype: str
        """

        tmp = [encode_string(self.address), encode_string(b"," + b"".join(self.typetags))]
        for typetag, argument in zip(self.typetags, self.args):
            if typetag == b"s":
                tmp.append(encode_string(argument))
            elif typetag == b'i':
                tmp.append(pack(">i", argument))
            elif typetag == b'f':
                tmp.append(pack(">f", argument))
            elif typetag == b'b':
                tmp.append(encode_blob(argument))
            elif typetag == b'd':
                tmp.append(pack(">d", argument))
            elif typetag == b't':
                tmp.append(encode_timetag(argument))
            else:
                raise TypeError("unknown typetag %r" % typetag)

        print("encode_osc tmp:")
        for i in tmp:
            print("    ", i)
        return b"".join(tmp)



class OSCBundle(object):
    """Builds a 'bundle' of OSC messages.

    OSCBundles are list objects for building binary osc containers for more than
    one message or bundle. They are defined recursively, so a bundle can hold
    more bundles or osc messages.

    OSCBundle have some limitations, but there are not enforced!:
        - an argument must be an OSCMessage or an OSCBundle
        - an OSCBundle does not have an address on its own, only the contained
            OSC-messages do.
        - OSC-bundles have a timetag to tell the receiver when the bundle should
            be processed. The default timetag value (0) means 'immediately'.
    """

    def __init__(self, timetag=0.):
        """Instantiate a new OSCBundle.

        :param address: osc address
        :type address: str

        :param time: positive timetag in seconds
        :type time: float
        """
        self.timetag = timetag
        self.args = list()

    def __str__(self):
        """Returns the Bundle's contents (and timetag, if nonzero) as a string.
        """
        return "Bundle(%r, %r)" % (self.timetag > 0. and " %s" % self.getTimeTagStr() or "", self.args)

    def setTimeTag(self, time):
        """Set or change the OSCBundle's TimeTag

        :param time: floating seconds since the Epoch, must be positive
        :type time: float
        """
        if time >= 0.:
            self.timetag = time

    def getTimeTagStr(self):
        """Return the TimeTag as a human-readable string

        :returns: a human readable timetag representation
        :rtype: str
        """

        fract, secs = modf(self.timetag)
        return b"".join([time.ctime(secs)[11:19], bytes("%.3f" % fract)[1:], "ascii"])

    def append(self, osc_message):
        """Appends an OSCMessage

        Any newly created OSCMessage inherits the OSCBundle's address at
        the time of creation.

        :param osc_message: the osc message to append
        :type osc_message: OSCMessage
        """

        self.args.append(osc_message)

    def encode_osc(self):
        """Returns the binary representation of the message

        :returns: the binary representation
        :rtype: str
        """
        message_binaries = [argument.encode_osc()
            for argument in self.args]
        print("message_binaries", message_binaries)

        blobs = [encode_blob(binary) for binary in message_binaries]
        print("blobs", blobs)
        blob_binary = b"".join(blobs)
        tmp = [
            encode_string(b"#bundle"),
            encode_timetag(self.timetag),
            blob_binary]
        print("bundle tmp", tmp)
        return b"".join(tmp)

    def __eq__(self, other):
        """Return True if two OSCBundles have the same timetag & content
        """
        if not isinstance(other, OSCBundle):
            return False

        return self.timetag == other.timetag and super(
            OSCBundle, self).__eq__(other)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
