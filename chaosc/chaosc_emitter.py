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




import random, socket, time, argparse, sys, math
from copy import copy
try:
    from chaosc.c_osc_lib import *
except ImportError as e:
    print(e)
    from chaosc.osc_lib import *

from chaosc.lib import resolve_host

from multiprocessing import Pool

from chaosc.argparser_groups import *


class Runner(object):
    def __init__(self, args):
        self.running = True
        self.args = args
    def __call__(self):

        sock = socket.socket(10, 2, 17)
        host, port = resolve_host(self.args.chaosc_host, self.args.chaosc_port)
        print(host, port)
        sock.connect((host, port))
        pi = math.pi
        count1 = random.random() * math.pi * 2
        #count2 = random.random() * math.pi * 2
        count2 = 0
        count3 = 0
        step1 = math.pi * 2 // 300.
        #step2 = math.pi * 2 / 300.
        step3 = math.pi * 2 // 400.
        foo = 0

        while self.running:
            #reply = OSCBundle()
            m1 = OSCMessage(b"/uwe/ekg")
            m1.appendTypedArg(int(254 * ((math.e ** (2 * -count1)) * math.cos(count1 * 10 * math.pi) + 1) // 2), b"i")

            m2 = OSCMessage(b"/merle/ekg")
            m2.appendTypedArg(254 - count2, b"i")

            m3 = OSCMessage(b"/bjoern/ekg")
            m3.appendTypedArg(int(254 * (math.cos(count3) + 1) // 2), b"i")

            sent = sock.sendall(m1.encode_osc())
            sent = sock.sendall(m2.encode_osc())
            sent = sock.sendall(m3.encode_osc())

            count1 = (count1 + step1) % (math.pi * 2)
            count2 = (count2 + 1) % 254
            count3 = (count3 + step3) % (math.pi * 2)

            foo +=1
            if foo == 1000:
                m1 = OSCMessage(b"/plot/uwe")
                m1.appendTypedArg(0, b"i")
                m1.appendTypedArg(1, b"i")
                m1.appendTypedArg(1, b"i")
                binary = m1.encode_osc()
                sent = sock.sendall(binary)
            elif foo == 2000:
                m1 = OSCMessage(b"/plot/merle")
                m1.appendTypedArg(0, b"i")
                binary = m1.encode_osc()
                sent = sock.sendall(binary)
            elif foo == 3000:
                m1 = OSCMessage(b"/plot/uwe")
                m1.appendTypedArg(1, b"i")
                binary = m1.encode_osc()
                sent = sock.sendall(binary)

                m1 = OSCMessage(b"/plot/merle")
                m1.appendTypedArg(1, b"i")
                binary = m1.encode_osc()
                sent = sock.sendall(binary)
                foo = 0

            time.sleep(0.005)


def main():
    arg_parser = create_arg_parser("chaosc_ts")
    main_group = add_main_group(arg_parser)
    add_chaosc_group(arg_parser)

    args = finalize_arg_parser(arg_parser)

    runner = Runner(args)
    runner()
