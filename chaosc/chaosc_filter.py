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
# Copyright (C) 2012-2013 Stefan Kögl

from __future__ import absolute_import


import sys, os, os.path, argparse, re, time, imp

from operator import itemgetter
from datetime import datetime
from chaosc.simpleOSCServer import SimpleOSCServer
from chaosc.config import transcoding_config
import chaosc._version

try:
    from chaosc.c_osc_lib import OSCMessage
except ImportError:
    from chaosc.osc_lib  import OSCMessage


def handle_incoming(address, typetags, args, client_address):
    print "client", address, typetags, args, client_address


class FilterOSCServer(SimpleOSCServer):
    """OSC filtering/transcoding middleware
    """

    def __init__(self, result):
        """ctor for filter server

        starts the server, loads scene filters and transcoders and chooses
        the request handler, which is one of
        forward only, forward and dump, dump only.

        :param result: return value of argparse.parse_args
        :type result: namespace object
        """

        d = datetime.now().strftime("%x %X")
        print "%s: starting up chaosc_filter-%s..." % (d, chaosc._version.__version__)
        print "%s: binding to %s:%r" % (d, "0.0.0.0", result.own_port)
        SimpleOSCServer.__init__(self, ("0.0.0.0", result.own_port))
        self.filter_address = (result.own_host, result.own_port)
        self.chaosc_address = (result.chaosc_host, result.chaosc_port)
        self.forward_address = (result.forward_host, result.forward_port)
        self.token = result.token
        self.config_dir = result.config_dir
        self.dump_only = result.dump_only

        a,b,c = imp.find_module("transcoding_config", [result.config_dir,])
        self.transcoders = imp.load_module(
            "transcoding_config", a, b, c).transcoders

        self.triggers = dict()

        self.scene = (list(), list())
        self.scenes = [self.scene,]
        self.scene_id = 0

        self.load_filters()
        self.subscribe_me(self.chaosc_address, self.filter_address,
            result.token, "chaosc_filter")

        if result.dump_only:
            self.handler = self.dump_only_handler
            print "%s: configured verbose=on, filtering and forwarding=off" % d
        elif result.dump:
            self.handler = self.dump_handler
            print "%s: configured verbose=on, filtering and forwarding=on" % d
        else:
            print "%s: configured verbose=off, filtering and forwarding=on" % d


    def load_filters(self):
        d = datetime.now().strftime("%x %X")
        print "%s: loading filter configs..." % d
        m = re.compile("filter_(\d+)\.config")
        scene_filters = list()
        for i in os.listdir(self.config_dir):
            r = m.match(i)
            if (r is not None and
                os.path.isfile(os.path.join(self.config_dir, i))):
                scene_filters.append((r.group(1), i))

        scene_filters.sort(key=itemgetter(0))
        if scene_filters[0][0] > len(scene_filters):
            print "Warning: some filter config files for scenes are missing. " \
                "Your scene filters will be out of sync!"

        for ix, scene_filter in scene_filters:
            print "%s: loading filter config for scene %s..." % (d, ix)
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
        print "%s: loaded %d scenes" % (d, len(scene_filters))


    def add_transcoder(self, handler):
        """Adds a transcoder to chaosc.

        :param handler: an TranscoderBaseHandler implementation
        :type handler: ITranscoderHandler
        """
        self.transcoders.append(handler)


    def transcode(self, osc_address, typetags, args, packet, client_address):
        for transcoder in self.transcoders:
            if transcoder.match(osc_address):
                return transcoder(osc_address, typetags, args)
        return packet


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

        d = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if osc_address == "/scene":
            print "%s: switching scene from %d to %d" % (
                d, self._scene_id, args[0])
            self.scene_id = args[0]
            self.scene = self.scenes[self.scene_id]
            return
        elif osc_address == "/forward":
            self.scene_id += 1
            self.scene = self.scenes[self.scene_id]
            print "%s: switching scene forward to %d" % (d, self._scene_id)
            return
        elif osc_address == "/back":
            self.scene_id -= 1
            self.scene = self.scenes[self.scene_id]
            print "%s: switching scene back to %d" % (d, self._scene_id)
            return

        self.handler(osc_address, typetags, args, packet, client_address)

    def handler(self, osc_address, typetags, args, packet, client_address):
        if not self.filter(osc_address):
            return

        self.socket.sendto(self.transcode(osc_address, typetags, args, packet,
            client_address), self.forward_address)


    def dump_handler(self, osc_address, typetags, args, packet, client_address):
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

        if self.filter(osc_address):
            filtered = True
        else:
            filtered = False

        print "%s: incoming %r, dropped=%r, %r, %r" % (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            osc_address, filtered, typetags, args)

        if filtered:
            return

        self.socket.sendto(
            self.transcode(osc_address, typetags, args, packet, client_address),
            self.forward_address)

    def dump_only_handler(self, osc_address, typetags, args, packet,
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

        print "%s: incoming %r, %r, %r" % (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            osc_address, typetags, args)



def main():
    parser = argparse.ArgumentParser(prog='chaosc_filter')
    parser.add_argument("-H", '--chaosc_host', required=True,
        type=str, help='host of chaosc instance to control')
    parser.add_argument("-p", '--chaosc_port', required=True,
        type=int, help='port of chaosc instance to control')
    parser.add_argument('-o', "--own_host", required=True,
        type=str, help='my host')
    parser.add_argument('-r', "--own_port", required=True,
        type=int, help='my port')
    parser.add_argument('-c', "--config_dir", default="~/.config/chaosc",
        help="config directory. default = '~/.config/chaosc'")

    parser.add_argument("-f", '--forward_host', metavar="HOST",
        type=str, help='host of client where the message will be sento to')
    parser.add_argument("-F", '--forward_port', metavar="PORT",
        type=int, help='port of client where the message will be sento to')
    parser.add_argument('-t', '--token', type=str, default="sekret",
        help='token to authorize ctl commands, default="sekret"')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--dump', action="store_true",
        help='if True, this client dumps all received msgs to stdout')
    group.add_argument('-D', '--dump_only', action="store_true",
        help='if True, this client only dumps but does not filter and forward')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    result = parser.parse_args(sys.argv[1:])

    if (not result.dump_only and (
        not hasattr(result, "forward_host") or
        not hasattr(result, "forward_port"))):
        print "Error: please provide forward host and port"
        sys.exit(-1)

    server = FilterOSCServer(result)
    server.serve_forever()
