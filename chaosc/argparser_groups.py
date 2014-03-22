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
import sys
import socket


def create_arg_parser(progname):
    return argparse.ArgumentParser(prog=progname)


def add_main_group(arg_parser):
    own_group = arg_parser.add_argument_group('main', 'flags relevant for specifying main features and parameters')

    own_group.add_argument('-o', "--own_host", default="::",
        help='my host, defaults to "::"')
    own_group.add_argument('-p', "--own_port", default=8000,
        type=int, help='my port, defaults to 8000')
    return own_group


def add_chaosc_group(arg_parser):
    chaosc_group = arg_parser.add_argument_group('chaosc hub', 'flags relevant for interacting with chaosc')
    chaosc_group.add_argument("-H", '--chaosc_host', default="::",
        type=str, help='host of chaosc instance, defaults to "::"')
    chaosc_group.add_argument("-P", '--chaosc_port', default=7110,
        type=int, help='port of chaosc instance')
    return chaosc_group


def add_subscriber_group(arg_parser, subscriber_name):
    subscriber_group = arg_parser.add_argument_group('subscribing', 'flags relevant for (un-)subscribing. If you use subscription, the tool will automagically unsubscribe on default.')
    subscriber_group.add_argument('-s', '--subscribe', action="store_true",
        help='if True, this dumper subscribes itself to chaosc. If you use this, you should take a look at the other flags in this group...')
    subscriber_group.add_argument('-l', '--subscriber_label', default=subscriber_name,
        help='the string to use for subscription label, default="chaosc_transcoder"')
    subscriber_group.add_argument('-a', '--authenticate', type=str, default="sekret",
        help='token to authorize interaction with chaosc, default="sekret"')
    subscriber_group.add_argument('-k', '--keep-subscribed', action="store_true",
        help='if specified, this tool don\'t unsubscribes on error or exit, default=False')
    return subscriber_group


def add_forward_group(arg_parser):
    forward_group = arg_parser.add_argument_group("forwarding", "everything you need to forward messages to your target")
    forward_group.add_argument("-f", '--forward_host', metavar="HOST", default="localhost",
        type=str, help='host or url where the messages will be sent to')
    forward_group.add_argument("-F", '--forward_port', metavar="PORT",
        type=int, help='port where the messages will be sent to')
    return forward_group


def add_transcoding_group(arg_parser):
    transcoding_group = arg_parser.add_argument_group("transcoding", "everything you need to configure the transcoding toolchain")
    transcoding_group.add_argument('-t', "--transcoding_dir", default="~/.config/chaosc",
        help="config directory where the transcoding config file is located. default = '~/.config/chaosc'")
    transcoding_group.add_argument('-T', "--transcoding_file", default="transcoding_config.py",
        help="the configuration file for transcoders. default = 'transcoding_config'")
    return transcoding_group


def add_filtering_group(arg_parser):
    filtering_group = arg_parser.add_argument_group("filtering", "everything you need to configure the filtering toolchain")
    filtering_group.add_argument('-i', "--filtering_config_dir", default="~/.config/chaosc",
        help="config directory where the filter config files are located. default = '~/.config/chaosc'")
    return filtering_group


def finalize_arg_parser(arg_parser):
    return arg_parser.parse_args(sys.argv[1:])


if __name__ == '__main__':
    a = create_arg_parser("chaosc")
    main_group = add_main_group(a)
    add_chaosc_group(a)
    add_subscriber_group(a)
    add_forward_group(a)
    add_filtering_group(a)
    add_transcoding_group(a)
    args = finalize_arg_parser(a)
    a.print_help()
