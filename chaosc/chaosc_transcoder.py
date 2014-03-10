# -*- coding: utf-8 -*-

"""This module implements a standalone osc messsage transcoding tool.

It uses the chaosc osc_lib but does not depend on chaosc features, so it can
be used with other osc compatible gear.

We provide here osc message transcoding based on different transcoding
strategies like python regex defined in a config file but it's up to your python
skills to master them.
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
# Copyright (C) 2012-2014 Stefan Kögl

import sys, os, os.path, argparse, re, time, imp

from operator import itemgetter
from datetime import datetime
from simpleOSCServer import SimpleOSCServer
import _version

try:
    from c_osc_lib import OSCMessage
except ImportError:
    from osc_lib  import OSCMessage


def handle_incoming(address, typetags, args, client_address):
    print "client", address, typetags, args, client_address


class ChaoscTranscoder(SimpleOSCServer):
    """OSC filtering/transcoding middleware
    """

    def __init__(self, args):
        """ctor for filter server

        starts the server, subscribe to chaosc if wished and loads transcoders.

        :param result: return value of argparse.parse_args
        :type result: namespace object
        """

        d = datetime.now().strftime("%x %X")
        print "%s: starting up chaosc_transcoder-%s..." % (d, _version.__version__)
        SimpleOSCServer.__init__(self, (args.own_host, args.own_port))
        self.args = args

        self.chaosc_address = (args.chaosc_host, args.chaosc_port)
        self.forward_address = (args.forward_host, args.forward_port)

        a,b,c = imp.find_module(args.config_file, [args.config_dir,])
        self.transcoders = imp.load_module(
            args.config_file, a, b, c).transcoders

        if args.subscribe:
            self.subscribe_me(self.chaosc_address, self.filter_address,
                args.token, args.subscriber_label)


    def add_transcoder(self, handler):
        """Adds a transcoder to chaosc.

        :param handler: an TranscoderBaseHandler implementation
        :type handler: ITranscoderHandler
        """
        self.transcoders.append(handler)


    def dispatchMessage(self, osc_address, typetags, args, packet,
        client_address):
        """Handles this filtering, transcoding steps and forwards the result

        :param osc_address: the OSC address string.
        :type osc_address: str

        :param typetags: the typetags of args
        :type typetags: list

        :param args: the osc message args
        :type args: list

        :param packet: the binary representation of a osc message
        :type packet: str

        :param client_address: (host, port) of the requesting client
        :type client_address: tuple
        """


        for transcoder in self.transcoders:
            if transcoder.match(osc_address):
                packet = transcoder(osc_address, typetags, args)
                break

        self.socket.sendto(packet, self.forward_address)


def main():
    parser = argparse.ArgumentParser(prog='chaosc_transcoder')
    main_args_group = parser.add_argument_group('main flags', 'flags for chaosc_transcoder')
    chaosc_args_group = parser.add_argument_group('chaosc', 'flags relevant for interacting with chaosc')

    main_args_group.add_argument('-o', "--own_host", required=True,
        type=str, help='my host')
    main_args_group.add_argument('-r', "--own_port", required=True,
        type=int, help='my port')
    main_args_group.add_argument('-c', "--config_dir", default="~/.config/chaosc",
        help="config directory where the transcoding config file is located. default = '~/.config/chaosc'")
    main_args_group.add_argument('-C', "--config_file", default="transcoding_config.py",
        help="the configuration file for transcoders. default = 'transcoding_config.py'")
    main_args_group.add_argument("-f", '--forward_host', metavar="HOST",
        type=str, help='host or url where the messages will be sent to')
    main_args_group.add_argument("-F", '--forward_port', metavar="PORT",
        type=int, help='port where the messages will be sent to')

    chaosc_args_group.add_argument('-s', '--subscribe', action="store_true",
        help='if True, this transcoder subscribes itself to chaosc. If you use this, you need to provide more flags in this group')
    chaosc_args_group.add_argument('-S', '--subscriber_label', type=str, default="chaosc_transcoder",
        help='the string to use for subscription label, default="chaosc_transcoder"')
    chaosc_args_group.add_argument('-t', '--token', type=str, default="sekret",
        help='token to authorize subscription command, default="sekret"')
    chaosc_args_group.add_argument("-H", '--chaosc_host',
        type=str, help='host of chaosc instance')
    chaosc_args_group.add_argument("-p", '--chaosc_port',
        type=int, help='port of chaosc instance')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args(sys.argv[1:])

    server = ChaoscTranscoder(args)
    server.serve_forever()

