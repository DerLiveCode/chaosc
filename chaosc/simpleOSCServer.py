# -*- coding: utf-8 -*-

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
import atexit

from datetime import datetime
from struct import pack
from types import TupleType, IntType, StringTypes, FunctionType, MethodType
from SocketServer import UDPServer, DatagramRequestHandler, ThreadingUDPServer, ForkingUDPServer

from chaosc import _version

try:
    from chaosc.c_osc_lib import *
except ImportError:
    from chaosc.osc_lib import *

from chaosc.lib import resolve_host, fix_host

__all__ = ["SimpleOSCServer",]


class OSCRequestHandler(DatagramRequestHandler):
    """RequestHandler class for the OSCServer
    """
    def setup(self):
        """Prepare RequestHandler.
        Unpacks request as (packet, source socket address)
        Creates an empty list for replies.
        """
        (self.packet, self.socket) = self.request

    def handle(self):
        """Handle incoming OSCMessage
        """
        packet = self.packet
        len_packet = len(packet)
        try:
            osc_address, typetags, args = decode_osc(packet, 0, len_packet)
        except OSCError, e:
            return
        self.server.dispatchMessage(osc_address, typetags, args, packet, self.client_address)

    def finish(self):
        pass



class SimpleOSCServer(UDPServer):
    """A simple osc server/client to build upon our tools.

    Subscribes to chaosc if you want.
    """

    def __init__(self, args):
        """Instantiate an OSCServer.
        server_address ((host, port) tuple): the local host & UDP-port
        the server listens on
        """
        self.address_family = args.address_family

        self.args = args
        self.own_address = client_host, client_port = resolve_host(args.client_host, args.client_port, self.address_family, socket.AI_PASSIVE)
        self.chaosc_address = chaosc_host, chaosc_port = resolve_host(args.chaosc_host, args.chaosc_port, self.address_family)

        print "%s: binding to %s:%r" % (datetime.now().strftime("%x %X"), client_host, client_port)
        UDPServer.__init__(self, self.own_address, OSCRequestHandler)

        self.socket.setblocking(0)
        if hasattr(args, "subscribe") and args.subscribe:
            self.subscribe_me()

        self.callbacks = {}


    def subscribe_me(self):
        """Use this procedure for a quick'n dirty subscription to your chaosc instance.

        :param chaosc_address: (chaosc_host, chaosc_port)
        :type chaosc_address: tuple

        :param receiver_address: (host, port)
        :type receiver_address: tuple

        :param token: token to get authorized for subscription
        :type token: str
        """
        print "%s: subscribing to '%s:%d' with label %r" % (datetime.now().strftime("%x %X"), self.chaosc_address[0], self.chaosc_address[1], self.args.subscriber_label)
        msg = OSCMessage("/subscribe")
        msg.appendTypedArg(self.own_address[0], "s")
        msg.appendTypedArg(self.own_address[1], "i")
        msg.appendTypedArg(self.args.authenticate, "s")
        if self.args.subscriber_label is not None:
            msg.appendTypedArg(self.args.subscriber_label, "s")
        self.sendto(msg, self.chaosc_address)


    def unsubscribe_me(self):
        if self.args.keep_subscribed:
            return

        print "%s: unsubscribing from '%s:%d'" % (datetime.now().strftime("%x %X"), self.chaosc_address[0], self.chaosc_address[1])
        msg = OSCMessage("/unsubscribe")
        msg.appendTypedArg(self.own_address[0], "s")
        msg.appendTypedArg(self.own_address[1], "i")
        msg.appendTypedArg(self.args.authenticate, "s")
        self.sendto(msg, self.chaosc_address)


    def addMsgHandler(self, address, callback):
        """Register a handler for an OSC-address
        - 'address' is the OSC address-string.
        the address-string should start with '/' and may not contain '*'
        - 'callback' is the function called for incoming OSCMessages that match 'address'.
        The callback-function will be called with the same arguments as the 'msgPrinter_handler' below
        """

        if type(callback) not in (FunctionType, MethodType):
            raise OSCError("Message callback '%s' is not callable" % repr(callback))

        if address != 'X':
            address = '/' + address.strip('/')

        self.callbacks[address] = callback


    def delMsgHandler(self, address):
        """Remove the registered handler for the given OSC-address
        """
        del self.callbacks[address]


    def dispatchMessage(self, address, tags, args, packet, client_address):
        """Dispatches messages to a callback or a default msg handler, which
        should be registered with "X" as osc address.

        If you don't need message dispatching, you can also overwrite
        the :meth:`SimpleOSCServer.process_request` inherited from BaseServer
        """

        try:
            self.callbacks[address](address, tags, args, packet, client_address)
        except KeyError:
            self.callbacks["X"](address, tags, args, packet, client_address)


    def close(self):
        """Stops serving requests, closes server (socket), closes used client
        """
        self.server_close()
        self.shutdown()


    def connect(self, address):
        """connects as a sending client to another server
        """
        try:
            self.socket.connect(address)
            self.client_address = address
        except socket.error, e:
            self.client_address = None
            raise OSCError("SocketError: %s" % str(e))


    def send(self, msg):
        """Sends a osc message or bundle the server conntected to by :meth:`connect`
        """
        if not isinstance(msg, OSCMessage):
            raise TypeError("'msg' argument is not an OSCMessage or OSCBundle object")

        try:
            self.socket.sendall(msg.encode_osc())
        except socket.error, e:
            if e[0] in (7, 65):     # 7 = 'no address associated with nodename',  65 = 'no route to host'
                raise e
            else:
                raise OSCError("while sending to %s: %s" % (str(address), str(e)))


    def sendto(self, msg, address):
        """Send the given OSCMessage to the specified address.

        :param msg: the message to send
        :type msg: OSCMessage or OSCBundle

        :param address: (host, port) of receiving osc server
        :type address: tuple

        :except: OSCError when timing out while waiting for the socket.
        """
        if not isinstance(msg, OSCMessage):
            raise TypeError("'msg' argument is not an OSCMessage or OSCBundle object")

        binary = msg.encode_osc()
        try:
            while len(binary):
                sent = self.socket.sendto(binary, address)
                binary = binary[sent:]
        except socket.error, e:
            if e[0] in (7, 65):     # 7 = 'no address associated with nodename',  65 = 'no route to host'
                raise e
            else:
                raise OSCError("while sending to %s: %s" % (str(address), str(e)))


    def __eq__(self, other):
        """Compare function.
        """
        if not isinstance(other, self.__class__):
            return False

        return cmp(self.socket._sock, other.socket._sock)


    def __ne__(self, other):
        """Compare function.
        """
        return not self.__eq__(other)


    def address(self):
        """Returns a (host,port) tuple of the local address this server is bound to,
        or None if not bound to any address.
        """
        try:
            return self.socket.getsockname()
        except socket.error:
            return None


