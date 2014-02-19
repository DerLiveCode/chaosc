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


import sys, os, os.path, argparse, re, time, random

from threading import Thread, Lock

import serial
from datetime import datetime
from .simpleOSCServer import SimpleOSCServer
from .config import transcoding_config

try:
    from .c_osc_lib import OSCMessage, encode_osc
except ImportError:
    from .osc_lib  import OSCMessage, encode_osc


status = [1, 1, 1, 1]
status_lock = Lock()
serial_pins = "123456789abcdefg"

class SerialPollingThread(Thread):
    def __init__(self, serial_socket):
        super(SerialPollingThread, self).__init__()
        self.serial_socket = serial_socket

    def run(self):
        while 1:
            selected_src = int(self.serial_socket.read(1, timeout=1), 32)
            if selected_src is not None:
                selected_src_int = (int(source) - 1) * 4 + int(out) - 1
            time.sleep(0.1)

class SerialWritingThread(Thread):
    def __init__(self, serial_socket):
        super(SerialWritingThread, self).__init__()
        self.serial_socket = serial_socket

    def run(self):
        while 1:
            self.serial_socket.write("Status: %d %d %d %d\n" % (1, 1, 1, 1))
            time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser(prog='chaosc_serial_input')
    parser.add_argument("-o", "--output",
        default="/dev/ttyS0",
        type=str, help='device node. default=/dev/ttyS0')

    result = parser.parse_args(sys.argv[1:])
    serial_socket = serial.Serial(result.output, timeout=1)
    poll_thread = SerialPollingThread(serial_socket)
    send_thread = SerialWritingThread(serial_socket)

    poll_thread.start()
    send_thread.start()
