.. Chaosc documentation master file, created by
   sphinx-quickstart on Tue Jan  8 09:55:34 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. toctree::
   :maxdepth: 2

************************
The chaosc framework 0.1
************************

Introduction
============

Abstract
--------

The chaosc framework was developed for a theatre project called "Der Live-Code".
It consists of several tools and a custom OSC library.

Chaosc itself is a osc hub/proxy, which takes osc messages and delivers them
to subscribed receivers via UDP, written with two goals in mind.

* speed and low forwarding jitter
* easy to use

For the sake of speed, we've completely rewritten the OSC.py lib. The usage is more streamlined,
but also more error prone for using false type-tagged data in arguments,
little type checking is done here. So devs working with the code are on their
own to use the osc classes sanely, but it's bleeding fast. There is a 
version written with cython for c level speed, and a fall-back pure python library.
Below we'll prove, that it's also easy to use.

For now it supports the OSC 1.0 spec, and is optimized for UDP only. TCP is not supported.
Chaosc runs in dualstack mode which have to be ironed out a bit more.


Links and code
--------------

This documentation can be read online here: http://derlivecode.github.com/chaosc.

You can also generate this in a lot of different output formats with sphinx, e.g pdf::

    cd chaosc/docs
    make latexpdf

The source code of the chaosc framework and other used software and sketches are hosted in repositories by github on the DerLiveCode organization site: https://github.com/DerLiveCode/chaosc

Licenses
--------

This documentation is licensed under a Creative Commons Attribution-ShareAlike 3.0 Unported License.

The chaosc framework is licensed under the GPL-3.




Tools overview
==============

chaosc

    The multi unicast osc proxy

chaosc_ctl

    command line tool to control chaosc

chaosc_ts

    test script to create n parallel osc senders

chaosc_tt

    test script to create n parallel osc receivers

chaosc_filter

    tool to filter and transcode osc messages by matching regular expressions on the osc address

chaosc_serial

    tool to transcode data coming from a serial input into osc messages and vis versa.
    Used as a middleware for a gefen 4x4 hdmi video matrix, which sends its state
    back via serial on a routing change and a jazzmutant Lemur.
    The Lemur gefen control sketch can also be retrieved via the 'DerLiveCode'
    organization page on github.

chaosc_serial_input

    tool to test the chaosc_serial client without serial hardware

chaosc_recorder

    tool to record and replay osc messages like an audio recorder. In case that hub_address equals forward_address,
    no data will be forwarded in record or bypass mode.


Additionally there is a simple visual monitoring tool for chaosc written in java/processing.org,
which can be found via https://github.com/DerLiveCode.


Installation
============

Dependencies
------------

Dependencies should be automatically pulled in when installing chaosc. If you
prefer using another installation method for the dependencies, install these
packages.

+ >=python-2.7.3
+ cython
+ pyserial
+ Sphinx

Installation using easy_install or pip
--------------------------------------

easy_install -Z git://github.com/DerLiveCode/chaosc.git

Manual Installation
-------------------

Obtaining the repository::

    git clone git://github.com/DerLiveCode/chaosc.git

Change current directory to your copy of chaosc::

    cd chaosc

Install into system path::

    sudo python setup.py install

or install in developer mode, which uses your working copy and symlinks
chaosc in system path. It's nice since whenever you pull from remote, you're
automagically using the current codebase without reinstallation.::

    sudo python setup.py develop

For more information about setup.py commands::

    python setup.py --help-commands

Usage
=====

Basic Usage
-----------

Let's check which flags our new tools understand::

    chaosc -h
    chaosc_ctl -h
    chaosc_ts -h
    chaosc_tt -h
    chaosc_filter -h
    chaosc_serial -h
    chaosc_serial_input -h


Start your instance with a string token and a port of your choice. The token will be needed later. The right one must be appended to ctl messages to prove you are authorzied to control chaosc.
It's perhaps a good idea to use screen or another terminal multiplexer. After every code snipped you have to detach from the session if you use screen or open another terminal::

    screen -U
    chaosc -p 12345 -t foobar
    # detach from screen session


To get other receivers subscribed, use the chaosc_ctl tool or create an osc
message and send it to chaosc. The ctl commands are explained below in detail.
Fire now up your senders and receivers on your own and skip the next shell code or use the test tools to start e.g 4 receivers beginning from port 13000 to 13003::

    screen -U
    chaosc_tt -H 127.0.0.1 -p 12345 -o 127.0.0.1 -r 13000 -t foobar -s -n 4
    # detach from screen session


Pick another shell and start e.g 4 senders beginning from port 14000 to 14003::

    screen -U
    chaosc_ts -H localhost -p 12345 -n 4
    # detach from screen session

We have created 4 test senders which get every osc message delivered to all 4 test receivers.
Our receivers managed to subscribe to chaosc on their own by using the -s flag.

Now we want to test our serial tools. If you have no real serial device yet, you can create a pts pair.
We'll use socat for that task::

    skoegl@workstation ~ % screen -U
    skoegl@workstation ~ % sudo socat -d -d pty,raw,echo=1 pty,raw,echo=1
    2013/01/22 18:53:26 socat[28831] N PTY is /dev/pts/4
    2013/01/22 18:53:26 socat[28831] N PTY is /dev/pts/5
    2013/01/22 18:53:26 socat[28831] N starting data transfer loop with FDs [3,3] and [5,5]
    # detach from screen session

Use one pts node for the chaosc_filter and one for the chaosc_serial_input.
To test the serial line, we need a running osc receiver or chaosc_tt and then the chaosc_serial tool.
Let's start our serial tool::

    screen -U
    chaosc_serial -i /dev/pts/4 -o localhost -r 11000 -H localhost -p 13000 -c ~/foobar_config
    # detach from screen session


And our serial test tool::

    screen -U
    chaosc_serial_input -o /dev/pts/5
    # detach from screen session


Ways of subcription
-------------------

Up-Front file based configuration
_________________________________

You place your subscriptions in a file called targets.config in your chaosc config directory you specify with
the cli flag "-c path/to/your/cfg_dir". The cli flag -s loads your targets.conf file.

Each line represents one recipient and should be of the form "host=foo;port=bar;label=baz".

Using the command line control client
_____________________________________


Let's use the chaosc_ctl tool to subscribe a Lemur::

    chaosc_ctl 127.0.0.1 12345 -t foobar subscribe 192.168.2.23 9999

Or the same configured up-front in the target.config file::

    host=192.168.2.23;port=9999;label=lemur-1

And after our session we want to be nice users and remove the lemur from chaosc subscription::

    chaosc_ctl -H 127.0.0.1 -p 12345 -t foobar unsubscribe 192.168.2.23 9999

Using OSC messages
__________________

By sending a '(un-)subscribe' osc message. See :ref:`osc-control-label` for more information about
using osc messages to control chaosc.


Advanced usage
==============

Filtering and transcoding osc messages
--------------------------------------

If you want to filter osc messages with regular expressions on the osc addresses, you can do so
with the help of chaosc_filter. You have a white-list and a blacklist. Look into
the example config file 'filter.config'. There you can put a regular expression on each line
prefixed with 'white-list=' or 'black-list='. The filter will load and use them.
The white-list will be evaluated first, then the blacklist. So, if you use a
filter tool, you should not subscribe the receiving client to which filtered messages gets forwarded,
and subscribe your filter instance instead.

You can also transcode or modify osc messages as you like, but this is a bit more tricky.
Look into :file:`transcoders.py` how to implement custom ones.
We have also implemented some transcoders for our tasks. e.g to change the osc address
for a osc2midi device, extracting some integer data from the osc address,
map all floating point arguments to the midi value space from 0-127, and finally
use some of the matched data as new arguments. The configuration takes place in
a real python file located at config/transcoding_config.py.

Also the filtering client can dump messages for monitoring purposes. If you provide
the dump_only flag, it will not forward anything, just dumps the receiving messages.

Here is an example to start chaosc_filter::

    screen -U
    chaosc_filter -H 127.0.0.1 -p 12345 -o 127.0.0.1 -r 14000 -f 127.0.0.1 -F 12000 -t foobar -d -c ~/foobar_config
    # detach from screen session


MidiChanger
-----------

The mapper attribute
____________________


You want to have full control, which data will be used for the new OSCMessage.
So we need a parameterized way to reference arguments in the old message,
groups from the regular expression match, transcoder members.

The 'regex' parameter holds the string used to match against the osc address.
Groups you match can be used in the mapper.

'to_fmt' is the string format template used by str.format

The mapper is an iterable of iterables aka a mapping clause with 5 items.
Each mapping clause has the form ["from_directive", "from_value", "to_directive", "to_value", "format_directive"]

Here are the from_directives:

member
    transcoder object member. The from_value must be object member name string

regex
    must be a usable regular expression. The from_value must be a index in the match group

osc_arg
    The from_value must be a index in the old osc message args list

And the to_directives:

osc_arg
    the data mapped should be in the new osc message as arg at position 'to_value'

format
    the data mapped should be in the new osc address as format arg at position 'to_value'

The from_value and to_value kann be a string as used as an attribute name usable by getattr or an integer used as an positional index.

The format_directive has to be an registered function in transcoders:converters:

    * midi
    * int
    * float
    * str
    * unicode


.. _osc-control-label:

OSC control interface
=====================

You can use custom OSCMessages to control chaosc or to get operational stats.

Subscribe
---------

The last typetagged argument "label' is optional.

Osc address
    /subscribe

typetags
    "siss"

args
    host to subscribe, port to subscribe, chaosc token, label

response
    No response is send by chaosc

Unsubscribe
-----------

Osc address
    /unsubscribe

typetags
    "sis"

args
    subcribed host, subcribed port, chaosc token

response
    No response is send by chaosc


Statistics
----------

Osc address
    /stats

typetags
    "sis"

args
    response host, response port, chaosc token

response
    A OSCBundle with a list of OSCMessages.

    1. a set of subscribed clients aka targets
        * osc address "/st"
        * typetags "sid"
        * args (host, subscription label, msg_count, timestamp of last hit)
    2. a set of senders aka sources
        * osc address "/ss"
        * typetags "sid"
        * args (host, msg_count, timestamp of last hit)
    3. a set of routes from sources to targets
        * osc address "/sr"
        * typetags "ssid" and args
        * args (src_host, dst_host, msg_count, timestamp of last hit)
    4. an empty osc message to signal end of stats
        * osc address "/se"

scene
-----

makes chaosc_filter to activate filters for scene id.

Osc address
    /scene

typetags
    "i"

args
    scene id

response
    No response is send by chaosc_filter


forward
-------

makes chaosc_filter to activate filters for the following scene id.

Osc address
    /forward

typetags
    None

args
    None

response
    No response is send by chaosc_filter

back
----

makes chaosc_filter to activate filters for the previous scene id.

Osc address
    /back

typetags
    None

args
    None

response
    No response is send by chaosc_filter



API
===

.. automodule:: chaosc.chaosc
    :members:
    :private-members:
    :special-members:


chaosc.osc_chaosc and chaosc.c_osc_lib
--------------------------------------

.. automodule:: chaosc.osc_lib
    :members:
    :private-members:
    :special-members:


chaosc.simpleOSCServer
----------------------

.. automodule:: chaosc.simpleOSCServer
    :members:
    :private-members:
    :special-members:


chaosc.transcoders
------------------

.. automodule:: chaosc.transcoders
    :members:
    :private-members:
    :special-members:

chaosc.chaosc_filter
--------------------

.. automodule:: chaosc.chaosc_filter
    :members:
    :private-members:
    :special-members:



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
