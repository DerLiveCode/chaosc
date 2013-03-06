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


import sys, os, os.path, argparse
from time import sleep
from multiprocessing import Pool
from simpleOSCServer import SimpleOSCServer

try:
    from c_osc_lib import OSCMessage
except ImportError:
    from osc_lib  import OSCMessage



def main():
    parser = argparse.ArgumentParser(prog='chaosc_cli')
    parser.add_argument("-H", '--chaosc_host', required=True,
        type=str, help='host of chaosc instance to control')
    parser.add_argument("-p", '--chaosc_port', required=True,
        type=int, help='port of chaosc instance to control')
    parser.add_argument('-t', '--token', required=True,
        type=str, default="sekret",
        help='token to authorize ctl commands, default="sekret"')

    subparsers = parser.add_subparsers(dest="subparser_name",
        help='chaosc server commands')

    parser_subscribe = subparsers.add_parser('subscribe',
        help='subscribe a target')
    parser_subscribe.add_argument('host', metavar="url",
        type=str, help='hostname')
    parser_subscribe.add_argument('port', metavar="port",
        type=int, help='port number')

    parser_unsubscribe = subparsers.add_parser('unsubscribe',
        help='unsubscribe a target')
    parser_unsubscribe.add_argument('host', metavar="url", type=str,
        help='hostname')
    parser_unsubscribe.add_argument('port', metavar="port", type=int,
        help='port number')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    result = parser.parse_args(sys.argv[1:])

    client = SimpleOSCServer(("", 7777))

    if "unsubscribe" == result.subparser_name:
        msg = OSCMessage("/unsubscribe")
        msg.appendTypedArg(result.host, "s")
        msg.appendTypedArg(result.port, "i")
        msg.appendTypedArg(result.token, "s")
        client.connect((result.chaosc_host, result.chaosc_port))
        client.send(msg)
        print "unsubscribe %r:%r from %r:%r" % (
            result.host, result.port, result.chaosc_host, result.chaosc_port)
    elif "subscribe" == result.subparser_name:
        msg = OSCMessage("/subscribe")
        msg.appendTypedArg(result.host, "s")
        msg.appendTypedArg(result.port, "i")
        msg.appendTypedArg(result.token, "s")
        client.connect((result.chaosc_host, result.chaosc_port))
        client.send(msg)
        print "subscribe %r:%r to %r:%r" % (
            result.host, result.port, result.chaosc_host, result.chaosc_port)
    else:
        raise Exception("unknown command")
        sys.exit(1)


if __name__ == '__main__':
    main()

