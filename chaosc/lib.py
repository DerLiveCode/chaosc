# -*- coding: utf-8 -*-

'''This module implements a osc hub/proxy'''

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

__all__ = ["statlist", "resolve_host"]

import logging
import socket
import ConfigParser
import os.path

logger = logging.getLogger('simple_example')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(os.path.expanduser("~/.chaosc/chaosc.log"))
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


def statlist():
    """helper 2-item list factory for defaultdicts

    :rtype: list
    """
    return [0, 0]

def select_family(args):
    if args.ipv4_only:
        args.address_family = socket.AF_INET
    else:
        args.address_family = socket.AF_INET6


def resolve_host(host, port, family, flags=0):
    flags |= socket.AI_ADDRCONFIG
    if family == socket.AF_INET6:
        flags |= socket.AI_ALL | socket.AI_V4MAPPED
    return socket.getaddrinfo(host, port, family, socket.SOCK_DGRAM, 0, flags)[-1][4][:2]


def fix_host(ipv4_only, name):
    if ipv4_only:
        if name.find(":") != -1:
            if name == "::":
                name = "0.0.0.0"
            elif name == "::1":
                name = "127.0.0.1"
    return name
