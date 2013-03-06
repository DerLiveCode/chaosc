# -*- coding: utf-8 -*-

# This file is part of chaosc-
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

from chaosc.c_osc_lib import (OSCMessage as CMessage,
    OSCBundle as CBundle,
    decode_osc as c_decode_osc)
from chaosc.osc_lib import (OSCMessage as PMessage,
    OSCBundle as PBundle,
    decode_osc as p_decode_osc)
import unittest

class TestCOSCMessage(unittest.TestCase):
    def test_osc_message(self):
        msg = CMessage("/my/osc/address")
        msg.append('something')
        msg.insert(0, 'something else')
        msg[1] = 'entirely'
        msg.extend([1,2,3.])
        msg.appendTypedArg(4, "i")
        msg.appendTypedArg(5, "i")
        msg.append(6.)
        del msg[3:6]
        self.assertEqual(msg.pop(-2), 5)
        self.assertEqual(msg.__str__(), "/my/osc/address ['something else', 'entirely', 1, 6.0]")
        binary = msg.encode_osc()
        self.assertEqual(binary, '/my/osc/address\x00,ssif\x00\x00\x00something else\x00\x00entirely\x00\x00\x00\x00\x00\x00\x00\x01@\xc0\x00\x00')
        msg2 = c_decode_osc(binary, 0, len(binary))
        self.assertEqual(msg2.__repr__(), "('/my/osc/address', ['s', 's', 'i', 'f'], ['something else', 'entirely', 1, 6.0])")


class TestCOSCBundle(unittest.TestCase):
    def test_osc_message(self):
        msg = CMessage("/my/osc/address")
        msg.appendTypedArg(4, "i")
        msg.appendTypedArg("foo", "s")
        msg2 = CMessage("/other/address")
        msg.appendTypedArg(4., "f")
        bundle = CBundle()
        bundle.append(msg)
        bundle.append(msg2)
        binary = bundle.encode_osc()
        address, typetags, args = c_decode_osc(binary, 0, len(binary))
        self.assertEqual(typetags, bundle.timetag)
        self.assertEqual(list(args), [
            ('/my/osc/address', ['i', 's', 'f'], [4, 'foo', 4.0]),
            ('/other/address', [], [])]
        )

class TestPythonOSCMessage(unittest.TestCase):
    def test_osc_message(self):
        msg = PMessage("/my/osc/address")
        msg.append('something')
        msg.insert(0, 'something else')
        msg[1] = 'entirely'
        msg.extend([1, 2, 3.])
        msg.appendTypedArg(4, "i")
        msg.appendTypedArg(5, "i")
        msg.append(6.)
        del msg[3:6]
        self.assertEqual(msg.pop(-2), 5)
        self.assertEqual(msg.__str__(), "/my/osc/address ['something else', 'entirely', 1, 6.0]")
        binary = msg.encode_osc()
        self.assertEqual(binary, '/my/osc/address\x00,ssif\x00\x00\x00something else\x00\x00entirely\x00\x00\x00\x00\x00\x00\x00\x01@\xc0\x00\x00')
        msg2 = p_decode_osc(binary, 0, len(binary))
        self.assertEqual(msg2.__repr__(), "('/my/osc/address', ['s', 's', 'i', 'f'], ['something else', 'entirely', 1, 6.0])")


class TestPythonOSCBundle(unittest.TestCase):
    def test_osc_message(self):
        msg = PMessage("/my/osc/address")
        msg.appendTypedArg(4, "i")
        msg.appendTypedArg("foo", "s")
        msg2 = PMessage("/other/address")
        msg.appendTypedArg(4., "f")
        bundle = PBundle()
        bundle.append(msg)
        bundle.append(msg2)
        binary = bundle.encode_osc()
        address, typetags, args = p_decode_osc(binary, 0, len(binary))
        self.assertEqual(typetags, bundle.timetag)
        self.assertEqual(list(args), [
            ('/my/osc/address', ['i', 's', 'f'], [4, 'foo', 4.0]),
            ('/other/address', [], [])]
        )


if __name__ == '__main__':
    unittest.main()
