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
# Copyright (C) 2012-2014 Stefan Kögl


from __future__ import absolute_import


import random, socket, time, argparse, sys, math, os.path, re

import numpy

try:
    from chaosc.c_osc_lib import decode_osc
except ImportError, e:
    print e
    from chaosc.osc_lib import decode_osc

from chaosc.argparser_groups import ArgParser
from collections import defaultdict

from operator import itemgetter

class OSCAnalyzer(object):
    def __init__(self, args):
        self.args = args
        self.data = list()
        self.rec_start = None
        self.rec_end = None
        self.annotations = dict()
        self.error_count = 0
        if args.annotation_file:
            for line in open(os.path.expanduser(args.annotation_file)):
                regex, typetags, arg_names = line[:-1].split("; ")
                regex = re.compile(regex)
                typetags = typetags.split(", ")
                arg_names = arg_names.split(", ")
                self.annotations[regex] = (typetags, arg_names)


    def get_annotation(self, osc_address):
        for key, value in self.annotations.iteritems():
            res = key.match(osc_address)
            if res:
                return value
        return None


    def loadFile(self):
        for ix, line in enumerate(open(self.args.record_path, "rb")):
            if line == "\n" or line == "":
                continue
            #print repr(line)
            if line.startswith("start: "):
                self.rec_start = float(line[7:-1])
            elif line.startswith("end: "):
                self.rec_end = float(line[5:-1])
            else:
                try:
                    timestamp, packet = line.split(": ")
                    packet = packet.strip(" ").strip("\n").strip("\r")
                    osc_address, typetags, args = decode_osc(packet, 0, len(packet))
                    self.data.append((time, osc_address, typetags, args))
                except ValueError:
                    self.error_count += 1
                    pass


    def analyze(self):
        per_address = defaultdict(list)
        for time, osc_address, typetags, args in self.data:
            per_address[osc_address].append(args)

        duration = self.rec_end - self.rec_start
        total = len(self.data)
        print "error count", self.error_count
        print "Record Start: ", time.ctime(self.rec_start)
        print "Record End: ", time.ctime(self.rec_end)
        print "Duration: %f s" % (self.rec_end - self.rec_start)
        print "Total OSCMessages: ", total
        print "OSCMessages/s: ", total / duration
        print "Used OSCMessages:"
        for address, args in per_address.iteritems():
            annotation = self.get_annotation(address)
            arg_total = len(args)
            print "    %r:" % address
            print "        Total: %r" % arg_total
            print "OSCMessages/s: ", arg_total / duration
            for i in range(len(args[0])):
                print "        Argument %d:" % i
                if annotation is not None:
                    type_tags, arg_names = annotation
                    print "            Typetag: %r" % type_tags[i]
                    print "            Argument name: %r" % arg_names[i]
                print "            Min: %r" % min(args, key=itemgetter(i))[0]
                print "            Max: %r" % max(args, key=itemgetter(i))[0]
                print "            Mean: %r" % (sum([item[i] for item in args]) / float(arg_total))
                median = numpy.median(numpy.array([item[i] for item in args]))
                print "            Median: %r" % median

def main():
    arg_parser = ArgParser("chaosc_stats")
    arg_parser.add_global_group()
    arg_parser.add_recording_group()
    arg_parser.add_stats_group()
    args = arg_parser.finalize()

    analyzer = OSCAnalyzer(args)
    analyzer.loadFile()
    analyzer.analyze()


if __name__ == '__main__':

    main()

