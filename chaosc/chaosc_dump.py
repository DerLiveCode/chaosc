# -*- coding: utf-8 -*-

"""This module implements the standalone filtering tool in the chaosc framework.

It uses the chaosc osc_lib but does not depend on chaosc features, so it can
be used with other osc compatible gear.

We provide here osc message filtering based on python regex defined in a file
and a very flexible transcoding toolchain, but it's up to your python skills
to master them. The TranscoderBaseHandler subclasses should be defined in the
appropriate python module you place in the config directory. Please refer for
a howto/examples to our comprehensive docs or look into the provided example
transcoding.py file.
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

from __future__ import absolute_import


import atexit
import sys, argparse

from datetime import datetime
from chaosc.simpleOSCServer import SimpleOSCServer
import chaosc._version


class ChaoscDump(SimpleOSCServer):
    """OSC filtering/transcoding middleware
    """

    def __init__(self, args):
        """ctor for filter server

        starts the server, loads scene filters and transcoders and chooses
        the request handler, which is one of
        forward only, forward and dump, dump only.

        :param result: return value of argparse.parse_args
        :type result: namespace object
        """

        d = datetime.now().strftime("%x %X")
        print "%s: starting up chaosc_dump-%s..." % (d, chaosc._version.__version__)
        SimpleOSCServer.__init__(self, (args.own_host, args.own_port))
        self.args = args
        self.chaosc_address = (args.chaosc_host, args.chaosc_port)

        if args.subscribe:
            self.subscribe_me(self.chaosc_address, (args.own_host, args.own_port),
                args.token, args.subscriber_label)



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

        print "%s: osc_address=%r, typetags=%r, arguments=%r" % (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            osc_address, typetags, args)


    def unsubscribe(self):
        self.unsubscribe_me(self.chaosc_address, (self.args.own_host, self.args.own_port),
            self.args.token)



def main():
    parser = argparse.ArgumentParser(prog='chaosc_filter')
    main_args_group = parser.add_argument_group('main flags', 'flags for chaosc_transcoder')
    chaosc_args_group = parser.add_argument_group('chaosc', 'flags relevant for interacting with chaosc')

    main_args_group.add_argument('-o', "--own_host", required=True,
        type=str, help='my host')
    main_args_group.add_argument('-p', "--own_port", required=True,
        type=int, help='my port')

    chaosc_args_group.add_argument('-s', '--subscribe', action="store_true",
        help='if True, this transcoder subscribes itself to chaosc. If you use this, you need to provide more flags in this group')
    chaosc_args_group.add_argument('-S', '--subscriber_label', type=str, default="chaosc_transcoder",
        help='the string to use for subscription label, default="chaosc_transcoder"')
    chaosc_args_group.add_argument('-t', '--token', type=str, default="sekret",
        help='token to authorize subscription command, default="sekret"')
    chaosc_args_group.add_argument("-H", '--chaosc_host',
        type=str, help='host of chaosc instance')
    chaosc_args_group.add_argument("-P", '--chaosc_port',
        type=int, help='port of chaosc instance')

    server = ChaoscDump(parser.parse_args(sys.argv[1:]))


    atexit.register(server.unsubscribe)
    server.serve_forever()
