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
# Copyright (C) 2012-2013 Stefan Kögl

from __future__ import absolute_import

import socket
import sys
import os, os.path
import argparse
import chaosc._version

from datetime import datetime
from time import time

from collections import defaultdict
from SocketServer import UDPServer, DatagramRequestHandler
from types import FunctionType, MethodType

try:
    from chaosc.c_osc_lib import (OSCBundle, OSCMessage,
        proxy_decode_osc, OSCError, OSCBundleFound)
except ImportError:
    from chaosc.osc_lib import (OSCBundle, OSCMessage, proxy_decode_osc,
        OSCError, OSCBundleFound)


__all__ = ["Chaosc",]


def statlist():
    """helper 2-item list factory for defaultdicts

    :rtype: list
    """
    return [0, 0]

class Chaosc(UDPServer):
    """A multi-unicast osc application level gateway

    Multiplexes osc messages from osc sources to subscribed targets.

    Targets will receive messages after they are subscribed to chaosc. You can
    also use a targets.config file for static subscriptions.
    """

    max_packet_size = 16*2**20
    address_family = socket.AF_INET6

    def __init__(self, args):
        """Instantiate an OSCServer.
        server_address ((host, port) tuple): the local host & UDP-port
        the server listens on

        :param server_address: (host, port) to listen on
        :type server_address: tuple

        :param token: token used to authorize ctl commands
        :type token: str
        """

        server_address = ("", args.port)

        now = datetime.now().strftime("%x %X")
        print "%s: starting up chaosc-%s..." % (
            now, chaosc._version.__version__)
        UDPServer.__init__(self, server_address, DatagramRequestHandler)
        print "%s: binding to %s:%r" % (
            now, self.socket.getsockname()[0], server_address[1])

        self.args = args
        self.callbacks = {}

        self.token = args.token

        self.socket.setsockopt(socket.SOL_SOCKET,
            socket.SO_SNDBUF, self.max_packet_size)
        self.socket.setsockopt(socket.SOL_SOCKET,
            socket.SO_RCVBUF, self.max_packet_size)
        self.socket.setblocking(0)

        self.targets = dict()
        self.source_stats = defaultdict(statlist)
        self.target_stats = defaultdict(statlist)
        self.route_stats = defaultdict(statlist)

        self.add_handler('subscribe', self.__subscription_handler)
        self.add_handler('unsubscribe', self.__unsubscription_handler)
        self.add_handler('/stats', self.__stats_handler)

        if args.subscription_file:
            self.__load_subscriptions()


    def server_bind(self):
        # Override this method to be sure v6only is false: we want to
        # listen to both IPv4 and IPv6!
        print "v6 only", self.socket.getsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY)
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, False)
        UDPServer.server_bind(self)


    def __load_subscriptions(self):
        """Loads predefined subcriptions from a file in given config directory

        :param path: the directory in which the targets.config file resists
        :type path: str
        """
        lines = open(self.args.subscription_file).readlines()
        for line in lines:
            data = line.strip("\n").split(";")
            args = dict([arg.split("=") for arg in data])
            address = (args["host"], int(args["port"]))
            address = socket.getaddrinfo(address[0], address[1], socket.AF_INET6, socket.SOCK_DGRAM, 0, socket.AI_V4MAPPED | socket.AI_ALL)[-1][4]
            self.targets[address] = args["label"]
            print "%s: subscribe %r (%s:%s) by config" % (
                datetime.now().strftime("%x %X"), args["label"],
                address[0], address[1])


    def add_handler(self, address, callback):
        """Registers a handler for an OSC-address

        :param address: the OSC address-string. It should start with '/'
            and may not contain '*'
        :type address: str

        :param callback: is the procedure called for incoming OSCMessages
            that equals `address`.
        :type callback: method or function

        The callback-function must accept four arguments
        (str addr, tuple typetags, tuple args, tuple client_address),
        as returned by decode_osc.
        """
        for chk in '*?,[]{}# ':
            if chk in address:
                raise OSCError("OSC-address string may not contain any" \
                    "characters in '*?,[]{}# '")

        if type(callback) not in (FunctionType, MethodType):
            raise OSCError("Message callback '%s' is not callable" %
                repr(callback))

        if address != 'default':
            address = '/' + address.strip('/')

        self.callbacks[address] = callback


    def remove_handler(self, address):
        """Remove the registered handler for the given OSC-address

        :param address: the OSC address-string. It should start with '/'
            and may not contain '*'
        :type address: str
        """
        del self.callbacks[address]


    def sendto(self, msg, address):
        """Send the given OSCMessage to the specified address.

        :param msg: the message to send
        :type msg: OSCMessage or OSCBundle

        :param address: (host, port) of receiving osc server
        :type address: tuple

        :except: OSCError when timing out while waiting for the socket.
        """

        if not isinstance(msg, OSCMessage):
            raise TypeError(
                "'msg' argument is not an OSCMessage or OSCBundle object")

        binary = msg.encode_osc()
        try:
            while len(binary):
                sent = self.socket.sendto(binary, address)
                binary = binary[sent:]
        except socket.error, error:
            # 7 = 'no address associated with nodename',
            # 65 = 'no route to host'
            if error[0] in (7, 65):
                raise error
            else:
                raise OSCError("while sending to %s: %s" % (str(address),
                    str(error)))


    def __str__(self):
        """Returns a string containing this Server's Class-name,
        software-version and local bound address (if any)
        """

        out = self.__class__.__name__
        out += " v%s.%s-%s" % chaosc._version.__version__
        addr = self.address()
        if addr:
            out += " listening on %r" % addr
        else:
            out += " (unbound)"

        return out

    def address(self):
        """Returns a (host,port) tuple of the local address this server
        is bound to or None if not bound to any address.
        """
        try:
            return self.socket.getsockname()
        except socket.error:
            return None

    def __proxy_handler(self, packet, client_address):
        """Sends incoming osc messages to subscribed receivers
        """

        now = time()

        source_stat = self.source_stats[client_address[0]]
        source_stat[0] += 1
        source_stat[1] = now

        sendto = self.socket.sendto
        serr = socket.error
        target_stats = self.target_stats
        route_stats = self.route_stats

        for address in self.targets.iterkeys():
            binary = packet[:]
            try:
                sendto(binary, address)
                target_stat = target_stats[address[0]]
                target_stat[0] += 1
                target_stat[1] = now

                route_stat = route_stats[(client_address[0], address[0])]
                route_stat[0] += 1
                route_stat[1] = now
            except serr, error:
                print error


    def __stats_handler(self, addr, tags, data, client_address):
        """Sends a osc bundle with subscribed clients and statistical data
        for monitoring and visualization usage.
        """

        reply = OSCBundle("")
        for (host, port), label in self.targets.iteritems():
            tmp = OSCMessage("/st")
            tmp.appendTypedArg(host, "s")
            tmp.appendTypedArg(label, "s")
            stat = self.target_stats[host]
            tmp.appendTypedArg(stat[0], "i")
            tmp.appendTypedArg(stat[1], "d")
            reply.append(tmp)
        for source, stat in self.source_stats.iteritems():
            tmp = OSCMessage("/ss")
            tmp.appendTypedArg(source, "s")
            tmp.appendTypedArg(stat[0], "i")
            tmp.appendTypedArg(stat[1], "d")
            reply.append(tmp)
        for (source, target), stat in self.route_stats.iteritems():
            tmp = OSCMessage("/sr")
            tmp.appendTypedArg(source, "s")
            tmp.appendTypedArg(target, "s")
            tmp.appendTypedArg(stat[0], "i")
            tmp.appendTypedArg(stat[1], "d")
            reply.append(tmp)

        size = OSCMessage("/ne")
        reply.append(size)
        self.sendto(reply, tuple(data[:2]))

    def __subscription_handler(self, addr, typetags, args, client_address):
        """handles a target subscription.

        The provided 'typetags' equals ["s", "i", "s", "s"] and
        'args' contains [host, portnumber, token, label]
        or ["s", "i", "s"] and 'args' contains [host, portnumber, token]

        only subscription requests with valid host and token will be granted.
        """

        try:
            if args[2] != self.token:
                raise IndexError()
        except IndexError:
            print "subscription attempt from %r: token wrong" % client_address
            return
        address = args[:2]
        try:
            r = socket.getaddrinfo(address[0], address[1], socket.AF_INET6, socket.SOCK_DGRAM, 0, socket.AI_V4MAPPED | socket.AI_ALL)
            print "addrinfo", r
            if len(r) == 2:
                address = r[1][4]
            try:
                print "%s: subscribe %r (%s:%d) by %s:%d" % (
                    datetime.now().strftime("%x %X"), args[3], address[0],
                    address[1], client_address[0], client_address[1])
                self.targets[tuple(address)] =  args[3]
            except IndexError:
                self.targets[tuple(address)] =  ""
                print "%s: subscribe (%s:%d) by %s:%d" % (
                    datetime.now().strftime("%x %X"), address[0], address[1],
                    client_address[0], client_address[1])
        except socket.error, error:
            print error
            print "subscription attempt from %r: host %r not usable" % (
                client_address, address[0])


    def __unsubscription_handler(self, address, typetags, args, client_address):
        """Handle the actual unsubscription

        The provided 'typetags' equals ["s", "i", "s"] and
        'args' contains [host, portnumber, token]

        Only unsubscription requests with valid host and token will be granted.
        """
        try:
            if args[2] != self.token:
                raise IndexError()
        except IndexError: # token not sent or wrong token
            print "subscription attempt from %r: token wrong" % client_address
            return

        try:
            address = tuple(args[:2])
            del self.targets[address[0]]
            print "unsubscription: %r, %r from %r" % (
                datetime.now().strftime("%x %X"), repr(address),
                repr(client_address))
        except KeyError:
            pass


    def process_request(self, request, client_address):
        """Handle incoming requests
        """
        packet = request[0]
        print "packet", repr(packet), client_address
        len_packet = len(packet)
        try:
            # using special decoding procedure for speed
            osc_address, typetags, args = proxy_decode_osc(packet, 0, len_packet)
        except OSCError:
            return
        except OSCBundleFound:
            # by convention we only look for OSCMessages to control chaosc, we
            # can simply forward any bundles found - it's not for us
            self.__proxy_handler(packet, client_address)
        else:
            try:
                self.callbacks[osc_address](osc_address, typetags, args,
                    client_address)
            except KeyError:
                self.__proxy_handler(packet, client_address)


def main():
    """configures cli argument parser and starts chaosc"""
    parser = argparse.ArgumentParser(prog='chaosc')
    parser.add_argument('-t', '--token', type=str, default="sekret",
        help='token to authorize ctl commands, default="sekret"')
    parser.add_argument('-p', '--port', type=int, default=7110,
        help='port of chaosc instance, default=7110')
    parser.add_argument('-s', "--subscription_file",
        help="load subscriptions")
    args = parser.parse_args(sys.argv[1:])
    server = Chaosc(args)
    server.serve_forever()
