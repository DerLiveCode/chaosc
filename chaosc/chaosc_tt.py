#!/usr/bin/python
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


import sys, argparse
from time import sleep
from multiprocessing import Pool
try:
    from .c_osc_lib import OSCMessage
except ImportError:
    from .osc_lib  import OSCMessage

from .simpleOSCServer import *


parser = argparse.ArgumentParser(prog='chaosc-tt')
parser.add_argument("-H", '--chaosc_host', required=True,
    type=str, help='host of chaosc instance to control')
parser.add_argument("-p", '--chaosc_port', required=True,
    type=int, help='port of chaosc instance to control')
parser.add_argument('-o', "--target_host", required=True,
    type=str, help='my host')
parser.add_argument('-r', "--target_port", required=True,
    type=int, help='my port')
parser.add_argument('-t', '--token',
    type=str, default="sekret",
    help='token to authorize ctl commands, default="sekret"')
parser.add_argument('-s', '--subscribe',
    action="store_true", default=False,
    help='if the clients should be subscribed')
parser.add_argument('-n', '--num_processes', required=True,
    type=int, default=1, help='number of senders started parallel as ' \
    'process (via multiprocessing.pool). Defaults to 1.')
result = parser.parse_args(sys.argv[1:])

class TestOSCServer(SimpleOSCServer):
    def process_request(self, request, client_address):
        print("request", repr(request[0]))


def do(ix):
    global result
    myport = result.target_port + ix
    server = TestOSCServer(("", myport))
    if result.subscribe:
        server.subscribe_me((result.chaosc_host, result.chaosc_port), (result.target_host, myport), result.token, "chaosc_tt%s" % ix)
    server.serve_forever()


def main():
    global result

    #p = Pool(result.num_processes)
    #result = p.map(do, range(result.num_processes))
    do(0)


#if __name__ == '__main__':
    #main()