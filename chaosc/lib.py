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

__all__ = ["logger", "select_family", "resolve_host"]

import logging
import socket
import ConfigParser
import os.path

logger = logging.getLogger('chaosc')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.NullHandler())

fmt = logging.Formatter("%(asctime)s: %(message)s")


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
