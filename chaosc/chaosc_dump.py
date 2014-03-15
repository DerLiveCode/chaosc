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
import sys
import socket


from datetime import datetime
from chaosc.simpleOSCServer import SimpleOSCServer
import chaosc._version

from chaosc.argparser_groups import *

class ChaoscDump(SimpleOSCServer):
    """OSC filtering/transcoding middleware
    """

    def __init__(self, args):
        """ctor for osc message dumper from chaosc"""

        print "%s: starting up chaosc_dump-%s..." % (datetime.now().strftime("%x %X"), chaosc._version.__version__)
        SimpleOSCServer.__init__(self, args)


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



def main():
    a = create_arg_parser("chaosc_dump")
    add_main_group(a)
    add_chaosc_group(a)
    add_subscriber_group(a, "chaosc_dump")
    args = finalize_arg_parser(a)

    server = ChaoscDump(args)
    atexit.register(server.unsubscribe_me)

    server.serve_forever()
