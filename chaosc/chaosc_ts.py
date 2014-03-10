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


import random, socket, time, argparse, sys
from copy import copy
try:
    from c_osc_lib import *
except ImportError, e:
    print e
    from osc_lib import *

from multiprocessing import Pool

parser = argparse.ArgumentParser(prog='chaosc-ts')
parser.add_argument("-H", '--chaosc_host', required=True,
    type=str, help='host of chaosc instance to control')
parser.add_argument("-p", '--chaosc_port', required=True,
    type=int, help='port of chaosc instance to control')
parser.add_argument('-n', '--num_processes',
    type=int, default=1, help='number of senders started parallel as process ' \
    '(via multiprocessing.pool). Defaults to 1')

result = parser.parse_args(sys.argv[1:])

def loop(ix):
    global result

    sock = socket.socket(2, 2, 17)
    sock.connect((result.chaosc_host, result.chaosc_port))
    count = 1
    test = False
    while 1:
        m1 = OSCMessage("/uwe/heartbeat")
        m1.appendTypedArg(random.sample((1,245), 1)[0], "i")
        m1.appendTypedArg(random.randint(0,180), "i")
        m1.appendTypedArg(random.randint(0, 100), "i")
        binary = m1.encode_osc()

        try:
            sent = sock.sendall(binary)
        except socket.error, e:
            if e[0] in (7, 65):     # 7 = 'no address associated with nodename',  65 = 'no route to host'
                raise e
            else:
                raise Exception("while sending to %r:%r: %s" % (result.chaosc_host, result.chaosc_port, str(e)))

        time.sleep(0.2)

        count +=1
        if count == 5:
            count = 1


def main():
    global result

    p = Pool(result.num_processes)
    result = p.map(loop, range(result.num_processes))
