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
from __future__ import absolute_import


import sys, os, os.path, argparse
from time import sleep
from multiprocessing import Pool
from chaosc.simpleOSCServer import SimpleOSCServer

try:
    from chaosc.c_osc_lib import OSCMessage
except ImportError:
    from chaosc.osc_lib  import OSCMessage

from chaosc.argparser_groups import *

class OSCCTLServer(SimpleOSCServer):
    def __init__(self, args):
        SimpleOSCServer.__init__(self, args)

        self.addMsgHandler("X", self.stats_handler)

        if "unsubscribe" == args.subparser_name:
            msg = OSCMessage("/unsubscribe")
            msg.appendTypedArg(args.host, "s")
            msg.appendTypedArg(args.port, "i")
            msg.appendTypedArg(args.authenticate, "s")
            self.sendto(msg, self.chaosc_address)
            print "unsubscribe %r:%r from %r:%r" % (
                args.host, args.port, args.chaosc_host, args.chaosc_port)
            sys.exit(0)

        elif "subscribe" == args.subparser_name:
            msg = OSCMessage("/subscribe")
            msg.appendTypedArg(args.host, "s")
            msg.appendTypedArg(args.port, "i")
            msg.appendTypedArg(args.authenticate, "s")
            if args.subscriber_label:
                msg.appendTypedArg(args.subscriber_label, "s")
            self.sendto(msg, self.chaosc_address)
            print "subscribe %r:%r to %r:%r" % (
                args.host, args.port, args.chaosc_host, args.chaosc_port)
            sys.exit(0)

        elif "stats" == args.subparser_name:
            msg = OSCMessage("/stats")
            msg.appendTypedArg(args.own_host, "s")
            msg.appendTypedArg(args.own_port, "i")
            self.sendto(msg, self.chaosc_address)
        else:
            raise Exception("unknown command")
            sys.exit(1)

    def stats_handler(self, name, desc, messages, packet, client_address):
        print "subscribed clients:"
        for osc_address, typetags, args in messages:
            if osc_address == "/st":
                print "    host=%r, port=%r, label=%r, received messages=%r" % (args[0], args[1], args[2], args[3])
        sys.exit(0)

    def handle_error(self, request, client_address):
        """Handle an error gracefully.  May be overridden.

        The default is to print a traceback and continue.

        """
        if sys.exc_type == SystemExit:
            sys.exit(0)



def main():
    arg_parser = create_arg_parser("chaosc_ctl")
    add_main_group(arg_parser)
    chaosc_group = add_chaosc_group(arg_parser)

    subparsers = arg_parser.add_subparsers(dest="subparser_name",
        help='chaosc server commands')

    parser_subscribe = subparsers.add_parser('subscribe',
        help='subscribe a target')

    parser_subscribe.add_argument('host', metavar="url",
        type=str, help='hostname')
    parser_subscribe.add_argument('port', metavar="port",
        type=int, help='port number')
    parser_subscribe.add_argument('-l', '--subscriber_label',
        help='the string to use for subscription label, default="chaosc_transcoder"')
    parser_subscribe.add_argument('-a', '--authenticate', type=str, default="sekret",
        help='token to authorize interaction with chaosc, default="sekret"')


    parser_unsubscribe = subparsers.add_parser('unsubscribe',
        help='unsubscribe a target')
    parser_unsubscribe.add_argument('host', metavar="url", type=str,
        help='hostname')
    parser_unsubscribe.add_argument('port', metavar="port", type=int,
        help='port number')
    parser_unsubscribe.add_argument('-l', '--subscriber_label',
        help='the string to use for subscription label, default="chaosc_transcoder"')
    parser_unsubscribe.add_argument('-a', '--authenticate', type=str, default="sekret",
        help='token to authorize interaction with chaosc, default="sekret"')


    parser_stats = subparsers.add_parser('stats',
        help='retrieve subscribed clients')

    result = arg_parser.parse_args(sys.argv[1:])

    client = OSCCTLServer(result)
    client.serve_forever()


if __name__ == '__main__':
    main()

