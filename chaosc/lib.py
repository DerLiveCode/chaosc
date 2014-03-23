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




__all__ = ["statlist", "resolve_host"]

import socket

def statlist():
    """helper 2-item list factory for defaultdicts

    :rtype: list
    """
    return [0, 0]


def resolve_host(host, port):
    return socket.getaddrinfo(host, port, socket.AF_INET6, socket.SOCK_DGRAM, 0, socket.AI_V4MAPPED | socket.AI_ALL | socket.AI_CANONNAME | socket.AI_ADDRCONFIG)[-1][4][:2]
