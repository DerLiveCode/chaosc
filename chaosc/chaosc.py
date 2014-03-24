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




import socket
import sys
import os, os.path
import argparse

from datetime import datetime
from time import time

from collections import defaultdict
from socketserver import UDPServer, DatagramRequestHandler
from types import FunctionType, MethodType

import chaosc._version

from chaosc.argparser_groups import *
from chaosc.lib import resolve_host, statlist

try:
    from chaosc.c_osc_lib import (OSCBundle, OSCMessage,
        proxy_decode_osc, OSCError, OSCBundleFound)
except ImportError:
    from chaosc.osc_lib import (OSCBundle, OSCMessage, proxy_decode_osc,
        OSCError, OSCBundleFound)


__all__ = ["main",]


class Chaosc(UDPServer):
    """A multi-unicast osc application level gateway

    Multiplexes osc messages from osc sources to subscribed targets.

    Targets will receive messages after they are subscribed to chaosc. You can
    also use a targets.config file for static subscriptions.
    """

    max_packet_size = 16*2**20
    address_family = socket.AF_INET6

    def __init__(self, args):
        """Instantiate an OSCServer."""

        server_address = host, port = resolve_host(args.chaosc_host, args.chaosc_port)

        now = datetime.now().strftime("%x %X")
        print("%s: starting up chaosc-%s..." % (
            now, chaosc._version.__version__))
        UDPServer.__init__(self, server_address, DatagramRequestHandler)
        print("%s: binding to %s:%r" % (
            now, self.socket.getsockname()[0], server_address[1]))

        self.args = args
        self.callbacks = {}

        self.authenticate = bytes(args.authenticate, "ascii")

        self.socket.setsockopt(socket.SOL_SOCKET,
            socket.SO_SNDBUF, self.max_packet_size)
        self.socket.setsockopt(socket.SOL_SOCKET,
            socket.SO_RCVBUF, self.max_packet_size)
        self.socket.setblocking(0)

        self.targets = dict()
        self.source_stats = defaultdict(statlist)
        self.target_stats = defaultdict(statlist)
        self.route_stats = defaultdict(statlist)

        self.add_handler(b'/subscribe', self.__subscription_handler)
        self.add_handler(b'/unsubscribe', self.__unsubscription_handler)
        self.add_handler(b'/stats', self.__stats_handler)
        self.add_handler(b'/save', self.__save_subscriptions_handler)

        if args.subscription_file:
            self.__load_subscriptions()


    def server_bind(self):
        # Override this method to be sure v6only is false: we want to
        # listen to both IPv4 and IPv6!
        #print "v6 only", self.socket.getsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY)
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, False)
        UDPServer.server_bind(self)


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
        for chk in b'*?,[]{}# ':
            if chk in address:
                raise OSCError("OSC-address string may not contain any" \
                    "characters in '*?,[]{}# '")

        if type(callback) not in (FunctionType, MethodType):
            raise OSCError("Message callback '%s' is not callable" %
                repr(callback))

        if address != b'default':
            address = b'/' + address.strip(b'/')

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
        except socket.error as error:
            # 7 = 'no address associated with nodename',
            # 65 = 'no route to host'
            if error[0] in (7, 65):
                raise error
            else:
                raise OSCError("while sending to %s: %s" % (str(address),
                    str(error)))


    def address(self):
        """Returns a (host,port) tuple of the local address this server
        is bound to or None if not bound to any address.
        """
        try:
            return self.socket.getsockname()
        except socket.error:
            return None


    def process_request(self, request, client_address):
        """Handle incoming requests
        """
        packet = request[0]
        print("packet", repr(packet), client_address)
        len_packet = len(packet)
        try:
            # using special decoding procedure for speed
            osc_address, typetags, args = proxy_decode_osc(packet, 0, len_packet)
        except OSCBundleFound:
            # by convention we only look for OSCMessages to control chaosc, we
            # can simply forward any bundles found - it's not for us
            self.__proxy_handler(packet, client_address)
        except OSCError as e:
            print("%s: OSCError:: %s" % (datetime.now().strftime("%x %X"), e))
        else:
            try:
                self.callbacks[osc_address](osc_address, typetags, args,
                    client_address)
            except KeyError:
                self.__proxy_handler(packet, client_address)


    def __str__(self):
        """Returns a string containing this Server's Class-name,
        software-version and local bound address (if any)
        """

        out = self.__class__.__name__
        out += " v%s.%s-%s" % _version.__version__
        addr = self.address()
        if addr:
            out += " listening on %r" % addr
        else:
            out += " (unbound)"

        return out


    def __load_subscriptions(self):
        """Loads predefined subcriptions from a file in given config directory

        :param path: the directory in which the targets.config file resists
        :type path: str
        """
        lines = open(self.args.subscription_file).readlines()
        for line in lines:
            data = line.strip("\n").split(";")
            args = dict([arg.split("=") for arg in data])
            host = args["host"]
            port = int(args["port"])
            label = args["label"]
            try:
                self.__subscribe(host, port, label, None)
            except socket.gaierror as e:
                print("%s: subscription by config failed of host '%s:%d' - %s" % (
                    datetime.now().strftime("%x %X"), host, port, e))

    def __save_subscriptions(self):
        """Safes active subcriptions to a file in given config directory

        :param path: the directory in which the targets.config file resists
        :type path: str
        """

        print("args file", self.args.subscription_file)
        try:
            if self.args.subscription_file is None:
                raise Exception("file == None")
            path = self.args.subscription_file
        except Exception as e:
            print("first error", e)
            try:
                path = os.path.expanduser("~/.chaosc/targets-{}.conf".format(datetime.now().strftime("%Y%m%d")))
            except Exception as e:
                print("second error", e)
                return None
        print("path", path)
        try:
            sub_file = open(path, "w")
        except Exception as e:
            print(e)
            return None

        for (resolved_host, resolved_port), (label, host, port) in self.targets.items():
            line = "host={};port={};label={}\n".format(host, port, label)
            sub_file.write(line)
        sub_file.close()
        return path


    def __save_subscriptions_handler(self, address, typetags, args, client_address):
        """Makes chaosc to safe subscriptions to file by a OSCMessage command

        The provided 'typetags' equals ["s"] and
        'args' contains [authenticate]

        Only unsubscription requests with valid authenticate will be granted.
        """

        try:
            self.__authorize(args[0])
        except ValueError as e:
            print("%s: saving subscription failed - not authorized" % datetime.now().strftime("%x %X"))
            message = OSCMessage("/Failed")
            message.appendTypedArg("/save", "s")
            message.appendTypedArg("not authorized", "s")
            message.appendTypedArg(host, "s")
            message.appendTypedArg(port, "i")
            self.sendto(message, client_address)
            return

        result = self.__save_subscriptions()
        if result is None:
            print("%s: saving subscription failed - could not safe to file" % datetime.now().strftime("%x %X"))
            message = OSCMessage("/Failed")
            message.appendTypedArg("/save", "s")
            message.appendTypedArg("could not save to file", "s")
            self.sendto(message, client_address)
        else:
            print("%s: saving subscription successful to {}".format(result))
            message = OSCMessage("/OK")
            message.appendTypedArg("/save", "s")
            message.appendTypedArg(result, "s")
            self.sendto(message, client_address)


    def __proxy_handler(self, packet, client_address):
        """Sends incoming osc messages to subscribed receivers
        """

        #print repr(packet), client_address
        now = time()

        source_stat = self.source_stats[client_address[0]]
        source_stat[0] += 1
        source_stat[1] = now

        sendto = self.socket.sendto
        target_stats = self.target_stats
        route_stats = self.route_stats

        for address in self.targets.keys():
            binary = packet[:]
            try:
                sendto(binary, address)
                target_stat = target_stats[address[0]]
                target_stat[0] += 1
                target_stat[1] = now

                route_stat = route_stats[(client_address[0], address[0])]
                route_stat[0] += 1
                route_stat[1] = now
            except serr as error:
                pass


    def __stats_handler(self, addr, tags, data, client_address):
        """Sends a osc bundle with subscribed clients and statistical data
        for monitoring and visualization usage.
        """

        reply = OSCBundle()
        for (resolved_host, resolved_port), (label, host, port) in self.targets.items():
            tmp = OSCMessage(b"/st")
            tmp.appendTypedArg(bytes(host, "ascii"), b"s")
            tmp.appendTypedArg(port, b"i")
            tmp.appendTypedArg(bytes(label, "ascii"), b"s")
            stat = self.target_stats[host]
            tmp.appendTypedArg(stat[0], b"i")
            tmp.appendTypedArg(stat[1], b"d")
            reply.append(tmp)
        for source, stat in self.source_stats.items():
            tmp = OSCMessage(b"/ss")
            tmp.appendTypedArg(bytes(source, "ascii"), b"s")
            tmp.appendTypedArg(stat[0], b"i")
            tmp.appendTypedArg(stat[1], b"d")
            reply.append(tmp)
        for (source, target), stat in self.route_stats.items():
            tmp = OSCMessage(b"/sr")
            tmp.appendTypedArg(bytes(source, "ascii"), b"s")
            tmp.appendTypedArg(bytes(target, "ascii"), b"s")
            tmp.appendTypedArg(stat[0], b"i")
            tmp.appendTypedArg(stat[1], b"d")
            reply.append(tmp)

        size = OSCMessage(b"/ne")
        reply.append(size)
        self.socket.sendto(reply.encode_osc(), client_address)


    def __authorize(self, authenticate):
        if authenticate != self.authenticate:
            raise ValueError("unauthorized access attempt!")


    def __subscribe(self, host, port, label=None, client_address=None):
        if host == "":
            host = client_address[0]

        resolved_host, resolved_port = resolve_host(host, port)
        client_host, client_port = resolve_host(client_address[0], client_address[1])

        if (host, port) in self.targets:
            print("%s: subscription of '%s:%d (%s)' failed - already subscribed" % (
                datetime.now().strftime("%x %X"), host, port, self.targets[(host, port)]))
            message = OSCMessage(b"/Failed")
            message.appendTypedArg(b"subscribe", b"s")
            message.appendTypedArg(b"already subscribed", b"s")
            message.appendTypedArg(host, b"s")
            message.appendTypedArg(port, b"i")
            self.sendto(message, (client_host, client_port))
            return

        self.targets[(host, port)] = (label is not None and label or "", host, port)
        if client_address is not None:
            print("%s: subscription of '%s:%d (%s)' by '%s:%d'" % (
                datetime.now().strftime("%x %X"), host, port, label, client_address[0],
                client_address[1]))

            message = OSCMessage(b"/OK")
            message.appendTypedArg(b"subscribe", b"s")
            message.appendTypedArg(host, b"s")
            message.appendTypedArg(port, b"i")
            self.socket.sendto(message.encode_osc(), (client_host, client_port))
            print("sendto", client_host, client_port)
        else:
            print("%s: subscription of '%s:%d (%s)' by config" % (
                datetime.now().strftime("%x %X"), host, port, label))



    def __unsubscribe(self, host, port, client_address=None):

        client_host, client_port = resolve_host(client_address[0], client_address[1])
        resolved_host, resolved_port = resolve_host(host, port)
        print("resolved_address", resolved_host, resolved_port)

        try:
            label = self.targets.pop((bytes(resolved_host, "ascii"), resolved_port))
        except KeyError as e:
            print("%s: '%s:%d' was not subscribed" % (datetime.now().strftime("%x %X"), host, port))
            message = OSCMessage(b"/Failed")
            message.appendTypedArg(b"unsubscribe", b"s")
            message.appendTypedArg(b"not subscribed", b"s")
            message.appendTypedArg(bytes(host, "ascii"), b"s")
            message.appendTypedArg(port, b"i")
            self.sendto(message, (client_host, client_port))
        else:
            print("%s: unsubscription of '%s:%d (%s)' by '%s:%d'" % (
                datetime.now().strftime("%x %X"), host, port, label, client_host,
                client_port))
            message = OSCMessage(b"/OK")
            message.appendTypedArg(b"unsubscribe", b"s")
            message.appendTypedArg(host, b"s")
            message.appendTypedArg(port, b"i")
            self.sendto(message, (client_host, client_port))


    def __subscription_handler(self, addr, typetags, args, client_address):
        """handles a target subscription.

        The provided 'typetags' equals ["s", "i", "s", "s"] and
        'args' contains [host, portnumber, authenticate, label]
        or ["s", "i", "s"] and 'args' contains [host, portnumber, authenticate]

        only subscription requests with valid host and authenticate will be granted.
        """

        host, port = args[:2]
        try:
            self.__authorize(args[2])
        except ValueError as e:
            print("%s: subscription by config failed of host '%s:%d' - %s" % (
                datetime.now().strftime("%x %X"), host, port, e))
            message = OSCMessage(b"/Failed")
            message.appendTypedArg(b"subscribe", b"s")
            message.appendTypedArg(b"not authorized", b"s")
            message.appendTypedArg(host, "s")
            message.appendTypedArg(port, "i")
            self.sendto(message, client_address)
            return

        label = len(args) == 4 and args[3] or None

        try:
            self.__subscribe(host, port, label, client_address)
        except socket.gaierror as e:
            print("%s: subscription by config failed of host '%s:%d' - %s" % (
                datetime.now().strftime("%x %X"), host, port, e))


    def __unsubscription_handler(self, address, typetags, args, client_address):
        """Handle the actual unsubscription

        The provided 'typetags' equals ["s", "i", "s"] and
        'args' contains [host, portnumber, authenticate]

        Only unsubscription requests with valid host and authenticate will be granted.
        """

        host, port = args[:2]
        try:
            self.__authorize(args[2])
        except ValueError as e:
            print("%s: unsubscription by config failed of host '%s:%d' - %s" % (
                datetime.now().strftime("%x %X"), host, port, e))
            message = OSCMessage("/Failed")
            message.appendTypedArg("unsubscribe", "s")
            message.appendTypedArg("not authorized", "s")
            message.appendTypedArg(host, "s")
            message.appendTypedArg(port, "i")
            self.sendto(message, client_address)
            return

        label = len(args) == 4 and args[3] or None
        try:
            self.__unsubscribe(host, port, client_address)
        except socket.gaierror as e:
            print("%s: subscription by config failed of host '%s:%d' - %s" % (
                datetime.now().strftime("%x %X"), host, port, e))




def main():
    """configures cli argument parser and starts chaosc"""
    arg_parser = create_arg_parser("chaosc")
    main_group = add_chaosc_group(arg_parser)
    main_group.add_argument('-S', "--subscription_file",
        help="load subscriptions from the specified file")
    main_group.add_argument('-a', '--authenticate', type=str, default="sekret",
        help='token to authorize interaction with chaosc, default="sekret"')
    main_group.add_argument('-c', '--config_dir', type=str, default="~/.chaosc",
        help='config directory used as place to read and store e.g subscription files if not userwise specified, default="~./chaosc"')

    args = finalize_arg_parser(arg_parser)

    server = Chaosc(args)
    server.serve_forever()
