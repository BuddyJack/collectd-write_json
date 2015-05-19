# collectd-write_json
#
# The MIT License (MIT)
# 
# Copyright (c) 2015 Markus Juenemann
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Author:
#   Markus Juenemann <markus at juenemann.net>
#
# About this plugin:
#   This plugin uses collectd's Python plugin to send data over the network
#   encoded in JSON format.
#
# collectd:
#   http://collectd.org
# JSON:
#   http://www.json.org
# collectd-python:
#   http://collectd.org/documentation/manpages/collectd-python.5.shtml

import collectd
import socket
import json
import sys

# Enable for debugging only, will print to stderr!!!
#DEBUG = True

WRITERS = []

NAME = 'write_json'

class UDP(object):
    """
    Send JSON inside UDP packet.
    """

    def __init__(self, host, port, interface=None, ttl=None):
        collectd.debug("%s.UDP.__init__: host=%s, port=%s, interface=%s, ttl=%s" % (NAME, host, port, interface, ttl))
        self.host = host
        self.port = port
        self.interface = interface
        self.ttl = ttl
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if interface:
            # Crude test to distinguish between interface names and IP addresses.
            interface_ip = None
            try:
                if socket.gethostbyname(interface) == interface:
                    interface_ip = interface
            except socket.gaierror:
                try:
                    import netifaces
                    interface_ip = netifaces.ifaddresses(interface)[0]['addr']
                except Exception,msg:
                    collectd.notice("%s error setting interface: %s" % (NAME, msg))

            if interface_ip:
                try:
                    self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface_ip))
                except socket.error, msg:
                    collectd.notice("%s error setting interface: %s" % (NAME, msg))
            else:
                # Fudge self.interface to make self.__repr__() look better
                self.interface = '<invalid>'
                

        if ttl:
            try:
                self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
            except socket.error, msg:
                collectd.notice("%s error setting TTL to %d for host %s port %d: %s" % 
                                 (NAME, ttl, self.host, self.port, msg))
                # Fudge self.ttl to make self.__repr__() look better
                self.ttl = '<invalid>'
                
        
    def write(self, message):
        try:
            self.sock.sendto(message, (self.host, self.port))
        except socket.error, msg:
            collectd.warning("%s error sending to host %s port %d: %s" %
                             (NAME, self.host, self.port, msg))

        
    def close(self):
        try:
            self.sock.close()
        except socket.error:
            pass

    
    def __repr__(self):
        return "UDP(host=%s, port=%d, interface=%s, ttl=%s, sock=%s" % (self.host, self.port, self.interface, self.ttl, self.sock) 

def configure_callback(config):
    """Receive configuration block"""

    global WRITERS

    for node in config.children:
        key = node.key.lower()


        # Server "host" "port" "interface" "ttl"
        # Server "host" "port" "ttl" "interface"
        interface = None
        ttl = None

     
        collectd.debug("%s.configure_callback: key=%s values=%s" % (NAME, key, node.values))


        # Server 
        if key != "server":
            collectd.notice("%s configuration error: unknown key %s, should be 'Server'" % (NAME, key))
            continue

           
        # host 
        try:
            host = node.values[0]
        except IndexError:
            collectd.notice("%s configuration error: host missing" % (NAME))
            continue


        # port
        try:
            port = int(node.values[1])
        except IndexError:
            collectd.notice("%s configuration error: port missing for host %s" % (NAME, host))
            continue
        except ValueError:
            collectd.notice("%s configuration error: invalid port for host %s" % (NAME, host))
            continue


        # interface/ttl 
        try:
            ttl = int(node.values[2])
        except ValueError:
            interface = node.values[2]
        except IndexError:
            pass


        # interface/ttl 
        try:
            ttl = int(node.values[3])
        except ValueError:
            interface = node.values[3]
        except IndexError:
            pass


        WRITERS.append(UDP(host, port, interface, ttl))


    collectd.debug("%s.configure_callback: WRITERS=%s" % (NAME, WRITERS))


def shutdown_callback():
    for writer in WRITERS:
        writer.close()


#def write_callback():

# register callbacks
collectd.register_config(configure_callback)
#collectd.register_read(read_callback)
