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

from __future__ import absolute_import

import sys, os, os.path, re, time, imp, atexit

from datetime import datetime

from chaosc.argparser_groups import *
from chaosc.simpleOSCServer import SimpleOSCServer

import chaosc._version
from chaosc.lib import resolve_host

try:
    from chaosc.c_osc_lib import OSCMessage
except ImportError:
    from chaosc.osc_lib  import OSCMessage


class ChaoscTranscoder(SimpleOSCServer):
    """OSC filtering/transcoding middleware
    """

    def __init__(self, args):
        """ctor for osc transcoder

        loads transcoders.

        :param args: return value of argparse.parse_args
        :type args: namespace object
        """


        print "%s: starting up chaosc_transcoder-%s..." % (datetime.now().strftime("%x %X"), chaosc._version.__version__)
        SimpleOSCServer.__init__(self, args)

        self.forward_address = resolve_host(args.forward_host, args.forward_port)

        basename = os.path.splitext(args.transcoding_file)[0]
        a,b,c = imp.find_module(basename, [args.transcoding_dir,])
        self.transcoders = imp.load_module(
            basename, a, b, c).transcoders


    def add_transcoder(self, handler):
        """Adds a transcoder to chaosc.

        :param handler: an TranscoderBaseHandler implementation
        :type handler: ITranscoderHandler
        """
        self.transcoders.append(handler)


    def dispatchMessage(self, osc_address, typetags, args, packet,
        client_address):
        """Handles transcoding and forwards the result

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
    a = create_arg_parser("chaosc_transcoder")
    add_main_group(a)
    add_chaosc_group(a)
    add_subscriber_group(a, "chaosc_transcoder")
    add_forward_group(a)
    add_transcoding_group(a)

    args = finalize_arg_parser(a)

    if not os.path.isdir(args.transcoding_dir):
        raise ValueError("Error: %r is not a directory" % args.transcoding_dir)
    if not os.path.isfile(os.path.join(args.transcoding_dir, args.transcoding_file)):
        raise ValueError("Error: %r is not a file" % os.path.join(args.transcoding_dir, args.transcoding_file))

    server = ChaoscTranscoder(args)
    atexit.register(server.unsubscribe_me)
    server.serve_forever()

