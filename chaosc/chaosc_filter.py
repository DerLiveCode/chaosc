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


import sys, os, os.path, re, atexit

from operator import itemgetter
from datetime import datetime
from chaosc.simpleOSCServer import SimpleOSCServer

import chaosc._version
from chaosc.argparser_groups import ArgParser
from chaosc.lib import resolve_host


class FilterOSCServer(SimpleOSCServer):
    """OSC filtering/transcoding middleware
    """

    def __init__(self, args):
        """ctor for filter server

        loads scene filters

        :param args: return value of argparse.parse_args
        :type args: namespace object
        """
        print "%s: starting up chaosc_filter-%s..." % (datetime.now().strftime("%x %X"), chaosc._version.__version__)

        SimpleOSCServer.__init__(self, args)

        self.forward_address = resolve_host(args.forward_host, args.forward_port)

        self.config_dir = args.filtering_config_dir

        self.scene = (list(), list())
        self.scenes = [self.scene,]
        self.scene_id = 0

        self.load_filters()



    def load_filters(self):
        now = datetime.now().strftime("%x %X")
        print "%s: loading filter configs..." % now
        regex = re.compile("filter_(\d+)\.config")
        scene_filters = list()
        for i in os.listdir(self.config_dir):
            regex_res = regex.match(i)
            if (regex_res is not None and
                os.path.isfile(os.path.join(self.config_dir, i))):
                scene_filters.append((regex_res.group(1), i))
        if not scene_filters:
            return

        scene_filters.sort(key=itemgetter(0))
        if scene_filters[0][0] > len(scene_filters):
            print "Warning: some filter config files for scenes are missing. " \
                "Your scene filters will be out of sync!"

        for ix, scene_filter in scene_filters:
            print "%s: loading filter config for scene %s..." % (now, ix)
            lines = open(
                os.path.join(self.config_dir, scene_filter)).readlines()
            for line in lines:
                liste, regex = line.strip("\n").strip().split("=")
                if liste == "blacklist":
                    self.scene[1].append(re.compile(regex))
                else:
                    self.scene[0].append(re.compile(regex))
                print "%s: new %s entry = %r..." % (
                    datetime.now().strftime("%x %X"), liste, regex)
            self.scenes.append((list(), list()))
        print "%s: loaded %d scenes" % (now, len(scene_filters))



    def filter(self, osc_address):
        send = False
        #whitelist checks
        for predicate in self.scene[0]:
            if predicate.match(osc_address):
                send = True
                break
        #blacklist checks
        for predicate in self.scene[1]:
            if predicate.match(osc_address):
                send = False
                break

        return send


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

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if osc_address == "/scene":
            print "%s: switching scene from %d to %d" % (
                now, self.scene_id, args[0])
            self.scene_id = args[0]
            self.scene = self.scenes[self.scene_id]
            return
        elif osc_address == "/forward":
            self.scene_id += 1
            self.scene = self.scenes[self.scene_id]
            print "%s: switching scene forward to %d" % (now, self.scene_id)
            return
        elif osc_address == "/back":
            self.scene_id -= 1
            self.scene = self.scenes[self.scene_id]
            print "%s: switching scene back to %d" % (now, self.scene_id)
            return

        if not self.filter(osc_address):
            return

        self.socket.sendto(packet, self.forward_address)



def main():
    arg_parser = ArgParser("chaosc_filter")
    arg_parser.add_global_group()
    arg_parser.add_client_group()
    arg_parser.add_chaosc_group
    arg_parser.add_subscriber_group()
    arg_parser.add_forward_group
    arg_parser.add_filtering_group
    args = arg_parser.finalize()

    server = FilterOSCServer(args)
    atexit.register(server.unsubscribe_me)
    server.serve_forever()
