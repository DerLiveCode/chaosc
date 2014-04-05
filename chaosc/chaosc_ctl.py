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


import sys
import os
import os.path
import threading

from datetime import datetime
from time import sleep

from chaosc.simpleOSCServer import SimpleOSCServer

try:
    from chaosc.c_osc_lib import OSCMessage
except ImportError:
    from chaosc.osc_lib  import OSCMessage

from chaosc.argparser_groups import ArgParser

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

        elif "list" == args.subparser_name:
            msg = OSCMessage("/list")
            msg.appendTypedArg(args.client_host, "s")
            msg.appendTypedArg(args.client_port, "i")
            self.sendto(msg, self.chaosc_address)
        elif "save" == args.subparser_name:
            msg = OSCMessage("/save")
            msg.appendTypedArg(args.authenticate, "s")
            self.sendto(msg, self.chaosc_address)
        else:
            raise Exception("unknown command")
            sys.exit(1)


    def stats_handler(self, name, desc, messages, packet, client_address):
        if name == "#bundle":
            print "subscribed clients: {}".format(len(messages))
            for osc_address, typetags, args in messages:
                print "    host=%r, port=%r, label=%r" % (args[0], args[1], args[2])
        else:
            print "chaosc returned status {} with args {}".format(name, messages)

        sys.exit(0)

    def handle_error(self, request, client_address):
        """Handle an error gracefully.  May be overridden.

        The default is to print a traceback and continue.

        """
        if sys.exc_info()[0] == SystemExit:
            os._exit(0)
        else:
            print(sys.exc_info())



def main():
    arg_parser = ArgParser("chaosc_ctl")
    arg_parser.add_global_group()
    arg_parser.add_client_group()
    arg_parser.add_chaosc_group()

    subparsers = arg_parser.arg_parser.add_subparsers(dest="subparser_name",
        help='chaosc server commands')

    parser_subscribe = subparsers.add_parser('subscribe',
        help='subscribe a target')

    arg_parser.add_argument(parser_subscribe, 'host', metavar="url",
        type=str, help='hostname')
    arg_parser.add_argument(parser_subscribe, 'port', metavar="port",
        type=int, help='port number')
    arg_parser.add_argument(parser_subscribe, '-l', '--subscriber_label',
        help='the string to use for subscription label, default="chaosc_transcoder"')
    arg_parser.add_argument(parser_subscribe, '-a', '--authenticate', type=str, default="sekret",
        help='token to authorize interaction with chaosc, default="sekret"')


    parser_unsubscribe = subparsers.add_parser('unsubscribe',
        help='unsubscribe a target')
    arg_parser.add_argument(parser_unsubscribe, 'host', metavar="url", type=str,
        help='hostname')
    arg_parser.add_argument(parser_unsubscribe, 'port', metavar="port", type=int,
        help='port number')
    arg_parser.add_argument(parser_unsubscribe, '-l', '--subscriber_label',
        help='the string to use for subscription label, default="chaosc_transcoder"')
    arg_parser.add_argument(parser_unsubscribe, '-a', '--authenticate', type=str, default="sekret",
        help='token to authorize interaction with chaosc, default="sekret"')


    parser_stats = subparsers.add_parser('list',
        help='retrieve subscribed clients')

    parser_save = subparsers.add_parser('save',
        help='make save subscriptions to file')
    arg_parser.add_argument(parser_save, '-a', '--authenticate', type=str, default="sekret",
        help='token to authorize interaction with chaosc, default="sekret"')

    result = arg_parser.finalize()


    def exit():
        print "%s: the command seems to get no response - I'm dying now gracefully" % datetime.now().strftime("%x %X")
        os._exit(-1)

    killit = threading.Timer(6.0, exit)
    killit.start()

    client = OSCCTLServer(result)
    client.serve_forever()


if __name__ == '__main__':
    main()

