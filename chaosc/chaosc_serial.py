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


import sys, argparse, re, socket, serial, time, os.path
from .simpleOSCServer import SimpleOSCServer
from threading import Thread, Lock
from datetime import datetime
from . import _version


try:
    from .c_osc_lib import *
except ImportError:
    from .osc_lib  import *


def serial_input_representation(src, dst):
    return "123456789abcdefg"[(int(dst) - 1) * 4 + int(src) - 1]


def create_msg_for_serial(inputs):
    """creates 4 msgs, one to activate the active src pad, the other 3 to
    mute"""

    result = OSCBundle("/foo")
    tmp = set(range(1,5))
    for dst, src in enumerate(inputs, 1):
        src = int(src)
        src_to_unmute = OSCMessage("/source%d/out%d" % (src, dst))
        src_to_unmute.appendTypedArg(1, "i")
        indices_to_mute = tmp.difference(set((src,)))
        result.append(src_to_unmute)
        for i in indices_to_mute:
            src_to_mute = OSCMessage("/source%d/out%d" % (i, dst))
            src_to_mute.appendTypedArg(0, "i")
            result.append(src_to_mute)
    return result


class SerialOSCServer(SimpleOSCServer):
    def __init__(self, result):
        d = datetime.now().strftime("%x %X")
        print("%s: starting up chaosc_serial-%s..." % (d, _version.__version__))
        self.result = result

        self.output_address = (result.host, result.port)
        self.serial_socket = serial.Serial(result.input, 19200, timeout=1)
        #self.lock = Lock()
        self.regex = re.compile("/source(\d+)/out(\d+)")
        self.load_config()
        SimpleOSCServer.__init__(self, (result.own_host, result.own_port))
        print("%s: binding to %s:%r" % (d, result.own_host, result.own_port))
        self.subscribe_me((result.chaosc_host, result.chaosc_port), (result.own_host, result.own_port), result.token,  "chaosc_serial")
        self.thread = SerialPollingThread(self)


    def load_config(self):
        d = datetime.now().strftime("%x %X")
        print("%s: loading config..." % (d))
        try:
            data = open(os.path.join(self.result.config_dir,
                "chaosc_serial.config"), "r").readlines()
        except IOError:
            sys.stderr.write("Error: could not found a config directory with " \
                "a valid 'chaosc_serial.config'. Check your path!\n")
            sys.exit(-1)
        self.config = dict([foo.strip().strip("\n").split("=")
            for foo in data])

        #t = "".join([serial_input_representation(src, dst + 1)
        #    for dst, src in enumerate(self.config["initial_setting"])])
        #self.serial_socket.write(t)


    def process_request(self, request, client_address):
        """
        """

        def foo():
            #print "found osc msg", osc_address
            src, dst = m.groups()
            self.matrix = args
            si = serial_input_representation(src, dst)
            #self.lock.acquire()
            #print "writing %r to serial", si
            self.serial_socket.write("%s" % si)
            #self.serial_socket.flush()
            #self.lock.release()

        packet = request[0]
        osc_address, typetags, args = decodeOSC(packet, 0, len(packet))
        m = self.regex.match(osc_address)
        if m:
            foo()
        elif osc_address == "#bundle":
            for osc_address, typetags, args in args:
                print("bundle msg", osc_address, typetags, args)
                m = self.regex.match(osc_address)
                if m:
                    foo()
        self.shutdown_request(request)

class SerialPollingThread(Thread):
    def __init__(self, server):
        super(SerialPollingThread, self).__init__()
        self.server = server
        self.target_send_timeout = 10
        self.config = None


    def run(self):
        typetags = encodeString(",")
        regex = re.compile("Status: (\d+) (\d+) (\d+) (\d+)")
        udp_socket = self.server.socket
        result = self.server.result
        serial_socket = self.server.serial_socket
        output_address = result.host, result.port

        while 1:
            try:
                #self.server.lock.acquire()
                data = serial_socket.readline()
                #print "incoming from serial", repr(data)
                msg = create_msg_for_serial(
                    regex.match(data).groups())
                udp_socket.sendto(msg.encode_osc(), output_address)
            except AttributeError:
                pass
            finally:
                try:
                    #self.server.lock.release()
                    pass
                except Exception as e:
                    pass


def main():
    parser = argparse.ArgumentParser(prog='chaosc_serial')
    parser.add_argument("-H", '--chaosc_host', required=True,
        type=str, help='host of chaosc instance to control')
    parser.add_argument("-p", '--chaosc_port', required=True,
            type=int, help='port of chaosc instance to control')
    parser.add_argument('-o', "--own_host", type=str, help='my host', required=True)
    parser.add_argument('-r', "--own_port", type=int, help='my port', required=True)
    parser.add_argument("-i", "--input", default="/dev/pts/5", type=str, help='device node', required=True)
    parser.add_argument("-f", "--host", type=str, help='host of output', required=True)
    parser.add_argument('-F', "--port", type=int, help='port of output', required=True)
    parser.add_argument('-t', '--token', required=True,
        type=str, default="sekret", help='token to authorize ctl commands, default="sekret"')
    parser.add_argument('-c', "--config_dir", type=str, default="~/.config/chaosc",
        help="config directory")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    result = parser.parse_args(sys.argv[1:])
    server = SerialOSCServer(result)
    server.thread.start()
    server.serve_forever()
