# -*- coding: utf-8 -*-

'''This module is part of chaosc'''

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
# Copyright (C) 2014 Stefan Kögl


from __future__ import absolute_import

import argparse
import ConfigParser
import os.path
import socket
import sys

from datetime import datetime
from chaosc.lib import fix_host, select_family


class ArgParser(object):
    def __init__(self, prog_name):
        super(ArgParser, self).__init__()
        self.prog_name = prog_name
        self.arg_parser = argparse.ArgumentParser(prog=prog_name)
        self.flags = dict()
        self.defaults = dict()

    def add_argument(self, dest, *args, **kwargs):
        argument = dest.add_argument(*args, **kwargs)
        self.defaults[argument.dest] = argument.default

        if "type" in kwargs:
            _type = kwargs["type"]
        elif "action" in kwargs:
            _type = bool
            action = kwargs["action"]
            if action == "store_true":
                action_default = False
            elif action == "store_false":
                action_default = True
            else:
                raise NotImplementedError("only store_true and store_false actions are implemented yet. Feel free to send patches ;")
            self.defaults[argument.dest] = action_default
        else:
            _type = str
        self.flags[argument.dest] = _type


    def add_argument_group(self, *args, **kwargs):
        return self.arg_parser.add_argument_group(*args, **kwargs)


    def add_client_group(self):
        own_group = self.add_argument_group('client', 'flags relevant for specifying client parameters')

        self.add_argument(own_group, '-o', "--client_host", default="::",
            help='my host, defaults to "::"')
        self.add_argument(own_group, '-p', "--client_port", default=8000,
            type=int, help='my port, defaults to 8000')

        return own_group

    def add_global_group(self):
        global_group = self.add_argument_group('global', 'flags relevant for specifying main features and parameters')
        self.add_argument(global_group, '-d', "--defaults_file", default="~/.chaosc/chaosc.conf",
            help='the tool config file, defaults to "~/.chaosc/chaosc.conf"')
        self.add_argument(global_group, '-4', '--ipv4_only', action="store_true",
            help='select ipv4 sockets, defaults to ipv6"')
        return global_group



    def add_chaosc_group(self):
        chaosc_group = self.add_argument_group('chaosc hub', 'flags relevant for interacting with chaosc')
        self.add_argument(chaosc_group, "-H", '--chaosc_host', default="::",
            help='host of chaosc instance, defaults to "::"')
        self.add_argument(chaosc_group, "-P", '--chaosc_port', default=7110,
            type=int, help='port of chaosc instance')

        return chaosc_group


    def add_subscriber_group(self):
        subscriber_group = self.add_argument_group('subscribing', 'flags relevant for (un-)subscribing. If you use subscription, the tool will automagically unsubscribe on default.')
        self.add_argument(subscriber_group, '-s', '--subscribe', action="store_true",
            help='if True, this dumper subscribes itself to chaosc. If you use this, you should take a look at the other flags in this group...')
        self.add_argument(subscriber_group, '-l', '--subscriber_label', default=self.prog_name,
            help='the string to use for subscription label, default="chaosc_transcoder"')
        self.add_argument(subscriber_group, '-a', '--authenticate', type=str, default="sekret",
            help='token to authorize interaction with chaosc, default="sekret"')
        self.add_argument(subscriber_group, '-k', '--keep_subscribed', action="store_true",
            help='if specified, this tool don\'t unsubscribes on error or exit, default=False')
        return subscriber_group


    def add_forward_group(self):
        forward_group = self.add_argument_group("forwarding", "everything you need to forward messages to your target")
        self.add_argument(forward_group, "-f", '--forward_host', metavar="HOST", default="localhost",
            type=str, help='host or url where the messages will be sent to')
        self.add_argument(forward_group, "-F", '--forward_port', metavar="PORT",
            type=int, help='port where the messages will be sent to')
        return forward_group


    def add_transcoding_group(self):
        transcoding_group = self.add_argument_group("transcoding", "everything you need to configure the transcoding toolchain")
        self.add_argument(transcoding_group, '-t', "--transcoding_dir", default="~/.config/chaosc",
            help="config directory where the transcoding config file is located. default = '~/.config/chaosc'")
        self.add_argument(transcoding_group, '-T', "--transcoding_file", default="transcoding_config.py",
            help="the configuration file for transcoders. default = 'transcoding_config'")
        return transcoding_group


    def add_filtering_group(self):
        filtering_group = self.add_argument_group("filtering", "everything you need to configure the filtering toolchain")
        self.add_argument(filtering_group, '-i', "--filtering_config_dir", default="~/.config/chaosc",
            help="config directory where the filter config files are located. default = '~/.config/chaosc'")

        return filtering_group


    def add_stats_group(self):
        stats_group = self.add_argument_group("stats", "statistics flags")
        self.add_argument(stats_group, '-A', "--annotation_file", default="~/.config/annotations.py",
            help="the file with descriptions with the structure of OSCMessages, default = '~/.chaosc/annotations_config'")
        return stats_group

    def add_recording_group(self):
        recording_group = self.add_argument_group("recording", "record file path and other useful flags")
        self.add_argument(recording_group, '-r', '--record_path',
            default="chaosc_recorder.chaosc", help='path to store the recorded data')
        return recording_group


    def finalize(self):
        self.args = self.arg_parser.parse_args(sys.argv[1:])
        self._load_config_args()

        self._merge_config_with_cli()

        select_family(self.args)


        try:
            self.args.client_host = fix_host(self.args.ipv4_only, self.args.client_host)
        except AttributeError:
            pass

        try:
            self.args.chaosc_host = fix_host(self.args.ipv4_only, self.args.chaosc_host)
        except AttributeError:
            pass

        try:
            self.args.http_host = fix_host(self.args.ipv4_only, self.args.http_host)
        except AttributeError:
            pass

        now = datetime.now().strftime("%x %X")
        print "%s: configuration:" % now
        for item in self.args.__dict__.iteritems():
            print "    %s: %r" % item
        print

        return self.args


    def _load_config_args(self):

        self.config_args = dict()
        config_parser = ConfigParser.ConfigParser()
        path = os.path.expanduser(self.args.defaults_file)
        if not os.path.isfile(path):
            self.add_defaults()
            print self.args
            return
        config_parser.read(path)

        if not config_parser.has_section(self.prog_name):
            return

        for key in config_parser.options(self.prog_name):

            try:
                _type = self.flags[key]
            except KeyError:
                print "Warning: unknown config key/value '{}'".format(key)
                continue

            if _type == bool:
                config_value = config_parser.getboolean(self.prog_name, key)
            elif _type == int:
                config_value = config_parser.getint(self.prog_name, key)
            elif _type == float:
                config_value = config_parser.getfloat(self.prog_name, key)
            else:
                config_value = config_parser.get(self.prog_name, key)

            self.config_args[key] = config_value


    def _merge_config_with_cli(self):
        for key, value in self.args.__dict__.iteritems():

            if not key in self.config_args:
                continue
            if not key in self.defaults:
                continue
            default_value = self.defaults[key]
            conf_value = self.config_args[key]
            if value == default_value and value != conf_value:
                setattr(self.args, key, conf_value)


if __name__ == '__main__':
    a = ArgParser("chaosc")
    a.add_global_group()
    a.add_client_group()
    a.add_chaosc_group()
    a.add_subscriber_group()
    a.add_forward_group()
    a.add_filtering_group()
    a.add_transcoding_group()
    a.add_stats_group()
    a.add_recording_group()
    args = a.finalize()
    a.arg_parser.print_help()
