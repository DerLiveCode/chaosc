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

import sys, os, os.path, argparse, re, cPickle, time, asyncore, socket, thread

from threading import Thread, Lock
from simpleOSCServer import SimpleOSCServer
import termios, tty

import asyncore, socket

#class AsyncoreServerUDP(asyncore.dispatcher):
    #def __init__(self):
        #asyncore.dispatcher.__init__(self)

        ## Bind to port 5005 on all interfaces
        #self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.bind(('', 5005))

    ## Even though UDP is connectionless this is called when it binds to a port
    #def handle_connect(self):
        #print "Server Started..."

    ## This is called everytime there is something to read
    #def handle_read(self):
        #data, addr = self.recvfrom(2048)
        #print str(addr)+" >> "+data

    ## This is called all the time and causes errors if you leave it out.
    #def handle_write(self):
        #pass

#AsyncoreServerUDP()
#asyncore.loop()


class ReplayThread(Thread):
    def __init__(self, recorder):
        super(ReplayThread, self).__init__()
        self.recorder = recorder
        self.playing = True

    def run(self):
        print "Replay started"
        playstart = time.time()
        current_packet = 0
        if not self.recorder.data:
            print "Replay ended"
            self.playing = False
            return

        while self.playing:
            print "pass"
            try:
                timestamp, packet = self.recorder.data[current_packet]
                if time.time() - playstart <= 0.0:
                    self.recorder.socket.sendto(packet, self.recorder.forward_address)
                current_packet +=1
            except IndexError, e:
                print "Replay ended"
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
                self.recorder.bypass()
            elif char == "s":
                try:
                    self.recorder.save()
                except Exception, e:
                    print e
            elif char == "q":
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.remember_attributes)
                sys.stdout.write("\033[1G")
                os._exit(0)

class OSCRecorder(SimpleOSCServer):

    def __init__(self, filter_address, hub_address, forward_address, token, path):
        SimpleOSCServer.__init__(self, ("0.0.0.0", filter_address[1]))
        self.filter_address = filter_address
        self.hub_address = hub_address
        self.forward_address = forward_address
        self.token = token
        self.path = path
        self.data = list()
        self.mode = 0 # 0=bypass, 1=record, 2 = play
        self.lock = Lock()
        self.thread = None
        self.control = ControlThread(self)
        self.control.start()
        self.loopback = hub_address == forward_address
        self.help()
        if self.loopback:
            print "Detected loopback mode. Deactivating osc message forwarding in modes 'bypass' and 'record'."
        self.subscribe_me(hub_address, filter_address, token)
        self.load()
        self.bypass()

    def modeName(self):
        if self.mode == 0:
            return "bypassed"
        elif self.mode == 1:
            return "recording"
        elif self.mode == 2:
            return "replaying"

    def save(self):
        if self.mode == 1:
            raise Exception("stop recording before saving")

        self.lock.acquire()
        cPickle.dump((self.recstart, self.rec_end, self.data), open(self.path, "w"), 2)
        self.lock.release()

    def load(self):
        self.lock.acquire()
        try:
            self.recstart, self.rec_end, self.data = cPickle.load(open(self.path, "r"))
            print "Loaded osc session from %r with length %rs" % (time.ctime(self.recstart), int(self.rec_end - self.recstart))
        except Exception,e:
            print "No osc session loaded yet"
            pass
        self.lock.release()

    def help(self):
        print "This is chaosc_recorder."
        print
        print "press h to get this help"
        print "press q to quit"
        print "press p for replay"
        print "press b for bypassing"
        print "press r for recording"
        print "press s (in bypass mode) to save your recording to file"
        print
        print "Current mode: %s..." % self.modeName()

    def play(self):
        print "Started replay..."
        self.lock.acquire()
        self.mode = 2
        self.thread = ReplayThread(self)
        self.thread.start()
        self.lock.release()

    def record(self):
        print "Started recording..."
        self.lock.acquire()
        if self.mode == 2:
            self.thread.playing = False
            self.thread.join()
            self.thread = None
        self.mode = 1
        self.recstart = time.time()
        self.data = list()
        self.lock.release()

    def bypass(self):
        self.lock.acquire()
        if self.mode == 1:
            self.rec_end = time.time()
        if self.mode == 2:
            self.thread.playing = False
            self.thread.join()
            self.thread = None

        self.mode = 0
        print "Bypassed..."
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
        #char = packet[1]
        #if char == "p":
            #self.play()
        #elif char == "r":
            #self.record()
        #elif char == "b":
            #self.bypass()
        #elif char == "s":
            #try:
                #self.save()
            #except Exception, e:
                #print e
        #elif char == "q":
            #termios.tcsetattr(self.control.fd, termios.TCSADRAIN, self.control.remember_attributes)
            #sys.stdout.write("\033[1G")
            #os._exit(0)

        self.lock.acquire()
        if self.mode == 1:
            data.append((time.time() - self.recstart, packet))
        elif self.mode <= 1 and not self.loopback:
            self.socket.sendto(packet, self.forward_address)
        self.lock.release()



def main():
    parser = argparse.ArgumentParser(prog='chaosc_recorder')
    parser.add_argument("-H", '--chaosc_host', required=True,
        type=str, help='host of chaosc instance')
    parser.add_argument("-p", '--chaosc_port', required=True,
        type=int, help='port of chaosc instance')
    parser.add_argument('-o', "--own_host", required=True,
        type=str, help='my host')
    parser.add_argument('-r', "--own_port", required=True,
        type=int, help='my port')
    parser.add_argument("-f", '--forward_host', metavar="HOST", required=True,
        type=str, help='host of client the messages will be sento to')
    parser.add_argument("-F", '--forward_port', metavar="PORT", required=True,
        type=int, help='port of client the messages will be sento to')
    parser.add_argument('-t', '--token',
        type=str, default="sekret", help='token to authorize ctl commands, default="sekret"')
    parser.add_argument('-d', '--data', default="chaosc_recorder.pickled",
        type=str, help='path to store the recorded data')
    result = parser.parse_args(sys.argv[1:])

    server = OSCRecorder(
        (result.own_host, result.own_port),
        (result.chaosc_host, result.chaosc_port),
        (result.forward_host, result.forward_port),
        result.token,
        result.data)


    server.serve_forever()
