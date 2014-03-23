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




import sys, os, os.path, argparse, re, pickle, time, asyncore, socket, _thread

from threading import Thread, Lock
from chaosc.simpleOSCServer import SimpleOSCServer
import termios, tty

import asyncore, socket

from chaosc.argparser_groups import *

import chaosc._version

class ReplayThread(Thread):
    def __init__(self, recorder):
        super(ReplayThread, self).__init__()
        self.recorder = recorder
        self.playing = True

    def run(self):
        print("Replay started")
        playstart = time.time()
        current_packet = 0
        if not self.recorder.data:
            print("Replay ended")
            self.playing = False
            return

        while self.playing:
            print("pass")
            try:
                timestamp, packet = self.recorder.data[current_packet]
                if time.time() - playstart <= 0.0:
                    self.recorder.socket.sendto(packet, self.recorder.chaosc_address)
                current_packet +=1
            except IndexError as e:
                print("Replay ended")
                self.playing = False

class ControlThread(Thread):
    def __init__(self, recorder):
        super(ControlThread, self).__init__()
        self.recorder = recorder
        self.running = True
        self.fs = None

    def run(self):
        # This is a working function; something akin to the BASIC INKEY$ function...
        # Reference:- http://code.activestate.com/recipes/134892-getch-like-unbuffered-character-reading-from-stdin/
        # Many thanks to Danny Yoo for the above code, modified to suit this program...
        # In THIS FUNCTION some special keys do a "break" similar to the "Esc" key inside the program.
        # Be aware of this...
        # An inkey_buffer value of 0, zero, generates a "" character and carries on instead of waiting for
        # a valid ASCII key press.
        # got from here: http://code.activestate.com/recipes/577728-simpletron3xpy-game-to-demo-xy-drawing-using-the-k/?in=user-4177147
        inkey_buffer=1
        def inkey():
            sys.stdout.write("\033[1G")
            self.fd = sys.stdin.fileno()
            self.remember_attributes = termios.tcgetattr(self.fd)
            try:
                tty.setraw(sys.stdin.fileno())
                character=sys.stdin.read(inkey_buffer)
            finally:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.remember_attributes)
                sys.stdout.write("\033[1G")
            return character

        while self.running:
            time.sleep(0.5)
            char = inkey()
            if char == "p":
                self.recorder.play()
            elif char == "h":
                self.recorder.help()
            elif char == "r":
                self.recorder.record()
            elif char == "b":
                self.recorder.stop()
            elif char == "s":
                try:
                    self.recorder.save()
                except Exception as e:
                    print(e)
            elif char == "q":
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.remember_attributes)
                sys.stdout.write("\033[1G")
                os._exit(0)

class OSCRecorder(SimpleOSCServer):

    def __init__(self, args):
        SimpleOSCServer.__init__(self, args)
        self.args = args
        self.chaosc_address = (args.chaosc_host, args.chaosc_port)
        self.token = args.authenticate
        self.path = args.record_file
        self.mode = 0 # 0=ignore, 1=record, 2 = play
        self.lock = Lock()
        self.thread = None
        self.control = ControlThread(self)
        self.control.start()
        self.log_file = None
        self.help()
        self.stop()


    def modeName(self):
        if self.mode == 0:
            return "stopped"
        elif self.mode == 1:
            return "recording"
        elif self.mode == 2:
            return "playing"


    def help(self):
        print("This is chaosc_recorder.")
        print()
        print("press h to get this help")
        print("press q to quit")
        print("press p to play")
        print("press b for stop")
        print("press r to start record")
        print()
        print("Current mode: %s..." % self.modeName())

    def play(self):
        print("Started replay...")
        self.lock.acquire()
        self.mode = 2
        self.thread = ReplayThread(self)
        self.thread.start()
        self.lock.release()

    def record(self):
        print("Started recording...")
        self.lock.acquire()
        if self.mode == 2:
            self.thread.playing = False
            self.thread.join()
            self.thread = None
        self.log_file = open(self.path, "wb")
        self.mode = 1
        self.rec_start = time.time()
        self.log_file.write("start: %f\n" % self.rec_start)
        self.lock.release()

    def stop(self):
        self.lock.acquire()
        if self.mode == 1:
            self.rec_end = time.time()
            self.log_file.write("end: %f\n" % self.rec_end)
            self.log_file.close()

        if self.mode == 2:
            self.thread.playing = False
            self.thread.join()
            self.thread = None

        self.mode = 0
        print("stopped...")
        self.lock.release()


    def quit(self):
        try:
            self.thread.playing = False
            self.thread.join()
        except AttributeError:
            pass

        sys.exit(0)


    def process_request(self, request, client_address):
        """
        """

        packet = request[0]

        self.lock.acquire()
        if self.mode == 1:
            self.log_file.write("%f: %s\n" % (time.time() - self.rec_start, packet))
        elif self.mode == 2:
            self.socket.sendto(packet, self.chaosc_address)
        self.lock.release()



def main():
    arg_parser = create_arg_parser("chaosc_recorder")
    main_group = add_main_group(arg_parser)
    main_group.add_argument('-r', '--record_file',
        default="chaosc_recorder.chaosc", help='path to store the recorded data')
    add_chaosc_group(arg_parser)
    add_subscriber_group(arg_parser, "chaosc_recorder")
    args = finalize_arg_parser(arg_parser)

    server = OSCRecorder(args)


    server.serve_forever()


if __name__ == '__main__':
    import chaosc
    main()

