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

import argparse
import os, os.path
import socket
import sys
import logging

from collections import defaultdict
from datetime import datetime
from SocketServer import UDPServer, DatagramRequestHandler
from time import time, sleep
from types import FunctionType, MethodType


import chaosc._version

from chaosc.argparser_groups import ArgParser
from chaosc.lib import resolve_host, statlist, logger


try:
    from chaosc.c_osc_lib import (OSCBundle, OSCMessage,
        proxy_decode_osc, OSCError, OSCBundleFound)
except ImportError:
    from chaosc.osc_lib import (OSCBundle, OSCMessage, proxy_decode_osc,
        OSCError, OSCBundleFound)


__all__ = ["main",]


class Chaosc(UDPServer):
    """A multi-unicast osc application level gateway

    Multiplexes osc responses from osc sources to subscribed targets.

    Targets will receive responses after they are subscribed to chaosc. You can
    also use a targets.config file for static subscriptions.
    """

    def __init__(self, args):
        """Instantiate an OSCServer."""
        self.address_family = args.address_family

        self.args = args
        server_address = host, port = resolve_host(args.chaosc_host, args.chaosc_port, self.address_family)

        now = datetime.now().strftime("%x %X")
        logger.info("%s: starting up chaosc-%s...",
            now, chaosc._version.__version__)
        UDPServer.__init__(self, server_address, DatagramRequestHandler)
        logger.info("%s: binding to %s:%r",
            now, self.socket.getsockname()[0], server_address[1])


        self.callbacks = {}

        self.authenticate = args.authenticate

        self.socket.setblocking(0)

        self.targets = dict()
        self.is_pause = False

        self.add_handler('/subscribe', self.__subscription_handler)
        self.add_handler('/unsubscribe', self.__unsubscription_handler)
        self.add_handler('/list', self.__list_handler)
        self.add_handler('/save', self.__save_subscriptions_handler)
        self.add_handler('/pause', self.__toggle_pause_hander)

        if args.subscription_file:
            self.__load_subscriptions()


    def server_bind(self):
        # Override this method to be sure v6only is false: we want to
        # listen to both IPv4 and IPv6!
        #print "v6 only", self.socket.getsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY)
        if not self.args.ipv4_only:
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

        :param msg: the response to send
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
        #print "packet", repr(packet), client_address
        len_packet = len(packet)
        try:
            # using special decoding procedure for speed
            osc_address, typetags, args = proxy_decode_osc(packet, 0, len_packet)
        except OSCBundleFound:
            # by convention we only look for OSCMessages to control chaosc, we
            # can simply forward any bundles found - it's not for us
            self.__proxy_handler(packet, client_address)
        except OSCError, e:
            logger.exception(e)
        else:
            try:
                self.callbacks[osc_address](osc_address, typetags, args,
                    client_address)
            except KeyError:
                if not self.is_pause:
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

    def __toggle_pause_hander(self, addr, typetags, args, client_address):
        self.is_pause = bool(args[0])
        response = OSCMessage("/OK")
        response.appendTypedArg("pause", "s")
        response.appendTypedArg(int(self.is_pause), "i")
        try:
            self.socket.sendto(response.encode_osc(), client_address)
        except socket.error:
            pass
        logger.info("set pause to %r by %r", self.is_pause, client_address)


    def __load_subscriptions(self):
        """Loads predefined subcriptions from a file in given config directory
        """

        now = datetime.now().strftime("%x %X")
        path = os.path.expanduser(self.args.subscription_file)
        try:
            lines = open(path).readlines()
        except IOError, e:
            logger.error("%s: Error:: subscription file %r not found", now, path)
        else:
            for line in lines:
                data = line.strip("\n").split(";")
                args = dict([arg.split("=") for arg in data])
                host = args["host"]
                port = int(args["port"])
                label = args["label"]
                try:
                    self.__subscribe(host, port, label)
                except KeyError, e:
                    logger.error("%s: subscription failed for %s:%d (%s) by config - already subscribed". now, host, port, label)
                else:
                    logger.info("%s: subscription of %s:%d (%s) by config", now, host, port, label)


    def __save_subscriptions(self):
        """Safes active subcriptions to a file in given config directory

        :param path: the directory in which the targets.config file resists
        :type path: str
        """

        try:
            if self.args.subscription_file is None:
                raise Exception("subscription_file == None")
            path = self.args.subscription_file
        except Exception, e:
            logger.exception(e)
            try:
                path = os.path.expanduser("~/.chaosc/targets-{}.conf".format(datetime.now().strftime("%Y%m%d")))
            except Exception, e:
                logger.exception(e)
                return None

        try:
            sub_file = open(path, "w")
        except Exception, e:
            logger.exception(e)
            return None

        for (target_host, target_port), (label, host, port) in self.targets.iteritems():
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
        now = datetime.now().strftime("%x %X")
        try:
            self.__authorize(args[0])
        except ValueError, e:
            logger.error("saving subscription failed - not authorized")
            response = OSCMessage("/Failed")
            response.appendTypedArg("/save", "s")
            response.appendTypedArg("not authorized", "s")
            response.appendTypedArg(host, "s")
            response.appendTypedArg(port, "i")
            self.socket.sendto(response.encode_osc(), client_address)
            return

        result = self.__save_subscriptions()
        if result is None:
            logger.error("saving subscription failed - could not safe to file")
            response = OSCMessage("/Failed")
            response.appendTypedArg("/save", "s")
            response.appendTypedArg("could not save to file", "s")
            self.socket.sendto(response.encode_osc(), client_address)
        else:
            logger.info("saving subscription successful to %r", result)
            response = OSCMessage("/OK")
            response.appendTypedArg("/save", "s")
            response.appendTypedArg(result, "s")
            self.socket.sendto(response.encode_osc(), client_address)


    def __proxy_handler(self, packet, client_address):
        """Sends incoming osc responses to subscribed receivers
        """

        #print repr(packet), client_address
        now = time()

        sendto = self.socket.sendto

        for address in self.targets.iterkeys():
            try:
                sendto(packet, address)
            except socket.error, error:
                logger.exception(error)
                pass


    def __list_handler(self, addr, tags, data, client_address):
        """Sends a osc bundle with subscribed clients."""

        response = OSCBundle()
        for (target_host, target_port), (label, host, port) in self.targets.iteritems():
            message = OSCMessage("/li")
            message.appendTypedArg(target_host, "s")
            message.appendTypedArg(target_port, "i")
            message.appendTypedArg(label, "s")
            response.append(message)

        try:
            self.socket.sendto(response.encode_osc(), client_address)
        except socket.error:
                pass


    def __authorize(self, authenticate):
        if authenticate != self.authenticate:
            raise ValueError("unauthorized access attempt!")


    def __subscribe(self, host, port, label=None):
        try:
            target_host, target_port = resolve_host(host, port, self.address_family)
        except socket.gaierror:
            logger.info("no address associated with hostname %r. using unresolved hostname for subscription", host)
            target_host, target_port = host, port

        if (target_host, target_port) in self.targets:
            raise KeyError("already subscribed")

        self.targets[(target_host, target_port)] = (label is not None and label or "", host, port)


    def __unsubscribe(self, host, port):
        try:
            target_host, target_port = resolve_host(host, port, self.address_family)
        except socket.gaierror:
            logger.info("no address associated with hostname %r. using unresolved hostname for unsubscription", host)
            label = self.targets.pop((host, port))
        else:
            label = self.targets.pop((target_host, target_port))


    def __subscription_handler(self, addr, typetags, args, client_address):
        """handles a target subscription.

        The provided 'typetags' equals ["s", "i", "s", "s"] and
        'args' contains [host, portnumber, authenticate, label]
        or ["s", "i", "s"] and 'args' contains [host, portnumber, authenticate]

        only subscription requests with valid host and authenticate will be granted.
        """

        now = datetime.now().strftime("%x %X")

        host, port = args[:2]
        try:
            self.__authorize(args[2])
        except ValueError, e:
            logger.error("subscription failed of host '%s:%d' - not authorized",
                host, port)
            response = OSCMessage("/Failed")
            response.appendTypedArg("subscribe", "s")
            response.appendTypedArg("not authorized", "s")
            response.appendTypedArg(host, "s")
            response.appendTypedArg(port, "i")
            try:
                self.sendto(response, client_address)
            except socket.error:
                pass
            return

        label = len(args) == 4 and args[3] or None

        try:
            self.__subscribe(host, port, label)
        except KeyError:
            logger.error("subscription of '%s:%d' failed - already subscribed",
                host, port)
            response = OSCMessage("/Failed")
            response.appendTypedArg("subscribe", "s")
            response.appendTypedArg("already subscribed", "s")
            response.appendTypedArg(host, "s")
            response.appendTypedArg(port, "i")
            self.socket.sendto(response.encode_osc(), client_address)
        else:
            response = OSCMessage("/OK")
            response.appendTypedArg("subscribe", "s")
            response.appendTypedArg(host, "s")
            response.appendTypedArg(port, "i")
            try:
                self.socket.sendto(response.encode_osc(), client_address)
            except socket.error:
                pass
            logger.info("subscription of '%s:%d (%s)' by %r",
                host, port, label, client_address)



    def __unsubscription_handler(self, address, typetags, args, client_address):
        """Handle the actual unsubscription

        The provided 'typetags' equals ["s", "i", "s"] and
        'args' contains [host, portnumber, authenticate]

        Only unsubscription requests with valid host and authenticate will be granted.
        """
        now = datetime.now().strftime("%x %X")
        host, port = args[:2]
        try:
            self.__authorize(args[2])
        except ValueError, e:
            logger.error("unsubscription of '%s:%d' failed - already subscribed",
                host, port)
            response = OSCMessage("/Failed")
            response.appendTypedArg("unsubscribe", "s")
            response.appendTypedArg("not authorized", "s")
            response.appendTypedArg(host, "s")
            response.appendTypedArg(port, "i")
            self.socket.sendto(response.encode_osc(), client_address)
            return

        try:
            self.__unsubscribe(host, port)
        except KeyError:
            response = OSCMessage("/Failed")
            response.appendTypedArg("unsubscribe", "s")
            response.appendTypedArg("not subscribed", "s")
            response.appendTypedArg(host, "s")
            response.appendTypedArg(port, "i")
            try:
                self.socket.sendto(response.encode_osc(), client_address)
            except socket.error:
                pass
            logger.error("unsubscription by %r failed of target '%s:%d' - not subscribed",
                client_address, host, port)
        else:
            logger.info("unsubscription of %s:%d by %r",
                host, port, client_address)
            response = OSCMessage("/OK")
            response.appendTypedArg("unsubscribe", "s")
            response.appendTypedArg(host, "s")
            response.appendTypedArg(port, "i")
            try:
                self.socket.sendto(response.encode_osc(), client_address)
            except socket.error:
                pass



def main():
    """configures cli argument parser and starts chaosc"""
    arg_parser = ArgParser("chaosc")
    arg_parser.add_global_group()
    main_group = arg_parser.add_chaosc_group()
    arg_parser.add_argument(main_group, '-S', "--subscription_file",
        help="load subscriptions from the specified file")
    arg_parser.add_argument(main_group, '-a', '--authenticate', type=str, default="sekret",
        help='token to authorize interaction with chaosc, default="sekret"')

    args = arg_parser.finalize()

    server = Chaosc(args)
    server.serve_forever()

