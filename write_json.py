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

NAME = 'write_json'

import collectd
import socket
import json
import time
import re
import threading
import Queue as queue

LOCK = threading.Lock()
"""Lock for synchronising writers."""

TYPES_DB = ['/usr/share/collectd/types.db', '/usr/local/share/collectd/types.db']
"""List of paths to types.db files."""

TYPES = {}
"""Information parsed from all types.db files."""

WRITERS = []
"""List of writers (UdpWriter, ...)."""

# These are re-defined at the end of this file!
#
WRITER_MAP = None
FORMATTER_MAP = None
DEFAULT_FORMATTER = None


class BaseFormatter(object):

    def convert_values_to_dict(self, values_object):
        """
        Convert an instance of `collectd.Values` to a dictionary.

        """

        # The following attributes must always be there.
        #
        try:
            values_dict = {'time': values_object.time,
                           'interval': values_object.interval,
                           'host': values_object.host,
                           'plugin': values_object.plugin,
                           'type': values_object.type,
                           'values': [],
                           'dstype': [],
                           'dsname': [],
                           'dsmin': [],
                           'dsmax': []}
        except AttributeError, msg:
            collectd.notice("%s values=%s: %s" % (NAME, values_object, msg))
            return


        # `plugin_instance` and `type_instance` may be present.
        #
        try:
            values_dict['plugin_instance'] = values_object.plugin_instance
        except AttributeError:
            pass

        try:
            values_dict['type_instance'] = values_object.type_instance
        except AttributeError:
            pass


        # Retrieve the data source name and type. This feature has
        # been added only in October 2014 so it may not be available
        # in official releases (https://github.com/collectd/collectd/issues/771).
        #
        definitions = None
        try:
            definitions = collectd.get_dataset(values_object.type)
        except AttributeError:
            #
            # collectd.get_dataset() is not yet implemented. Try to get
            # the nformation from TYPES which holds the information
            # we read from types.db files.
            #
            try:
                definitions = TYPES[values_object.type]
            except KeyError:
                pass
        except TypeError, msg:
            pass


        # Append the actual values.
        #
        for (i, value) in enumerate(values_object.values):
            values_dict['values'].append(value)


            # File 'dsname' and 'dstype' if available.
            #
            if definitions:
                (dsname, dstype, dsmin, dsmax) = definitions[i]
                values_dict['dsname'].append(dsname)
                values_dict['dstype'].append(dstype)
                values_dict['dsmin'].append(dsmin)
                values_dict['dsmax'].append(dsmax)

        return values_dict


class JsonFormatter(BaseFormatter):
    def format(self, values_objects):
        values_dicts = [self.convert_values_to_dict(values_object) for values_object in values_objects]
        message = json.dumps(values_dicts) + '\n'
        collectd.debug("%s.JsonFormatter.format message=%s" %(NAME, message))
        return message


class KeyvalFormatter(BaseFormatter):
    template = 'time=%s host="%s" plugin="%s" plugin_instance="%s" type="%s" type_instance="%s" interval=%s value=%s dsname="%s" dstype="%s" dsmin=%s dsmax=%s\n'

    def format(self, values_objects):
        values_dicts = [self.convert_values_to_dict(values_object) for values_object in values_objects]

        message = ''
        for values_dict in values_dicts:
            for (i, value) in enumerate(values_dict['values']):
                message += self.template % (values_dict['time'], values_dict['host'],
                           values_dict['plugin'], values_dict['plugin_instance'], values_dict['type'], 
                           values_dict['type_instance'], values_dict['interval'], value, values_dict['dsname'][i],
                           values_dict['dstype'][i], values_dict['dsmin'][i], values_dict['dsmax'][0])

        return message


class BaseWriter(threading.Thread):
    FLUSH_INTERVAL = 1.0
    """The interval in seconds between checking and flushing the output buffer."""

    MAX_BUFFER_SIZE = 1000
    """The maximum size of values in the output buffer."""

    MAX_FLUSH_SIZE = MAX_BUFFER_SIZE
    """The maximum number of values that will be flushed together."""



    def __init__(self, formatter):
        collectd.debug("%s.BaseWriter.__init__: formatter=%s, FLUSH_INTERVAL=%s, MAX_BUFFER_SIZE=%s, MAX_FLUSH_SIZE=%s" % 
                       (NAME, formatter, self.FLUSH_INTERVAL, self.MAX_BUFFER_SIZE, self.MAX_FLUSH_SIZE))

        threading.Thread.__init__(self)

        self.buffer = queue.Queue(maxsize=self.MAX_BUFFER_SIZE)
        self.formatter = formatter


    def shutdown(self):
        """
        `shutdown()` will be called by `run()`.

        This can be overridden by a derived class.
        """
        pass

    
    def flush(self, message):
        """
        `flush()` will be called by `run()` when the write buffer must be flushed.

        :param message: 

        This must be overridden by a derived class.
        """

        pass


    def write(self, item):
        try:
            self.buffer.put_nowait(item)
        except queue.Full:
            collectd.notice("%s %s output buffer full" % (NAME,self))


    def run(self):
        collectd.debug("%s.BaseWriter.run" %(NAME))
        while True:
            collectd.debug("%s.%s sleep(%s)" % (NAME, self, self.FLUSH_INTERVAL))
            time.sleep(self.FLUSH_INTERVAL)

            while True: 
                try:
                    items = []

                    while len(items) < self.MAX_FLUSH_SIZE:
                        item = self.buffer.get_nowait()
                        collectd.debug("%s.%s item=%s" % (NAME, self, item))
                        items.append(item)
                    
                    if items:
                        message = self.formatter.format(items)
                        self.flush(message)

                except queue.Empty:
                    break

            if items:
                message = self.formatter.format(items)
                self.flush(message)


class UdpWriter(BaseWriter):
    """
    Send JSON inside UDP packet.
    """

    FLUSH_INTERVAL = 1.0
    """Collect multiple values."""

    MAX_FLUSH_SIZE = 3
    """Fit MAX_FLUSH_SIZE values into a single 1500 bytes UDP packet."""

    def __init__(self, formatter, *args, **kwargs):
        collectd.debug("%s.UdpWriter.__init__: formatter=%s, *args=%s, **kwargs=%s" % (NAME, formatter, args, kwargs))

        super(UdpWriter, self).__init__(formatter)

        # Server "host" "port" "interface" "ttl"
        # Server "host" "port" "ttl" "interface"
        #
        self.host = None
        self.port = None
        self.interface = None
        self.ttl = None


        # host 
        #
        try:
            self.host = args[0]
        except IndexError:
            collectd.notice("%s configuration error: host missing" % (NAME))
            raise


        # port
        #
        try:
            self.port = int(args[1])
        except IndexError:
            collectd.notice("%s configuration error: port missing for host %s" % (NAME, self.host))
            raise
        except ValueError:
            collectd.notice("%s configuration error: invalid port for host %s" % (NAME, self.host))
            raise


        # interface/ttl 
        #
        try:
            self.ttl = int(args[2])
        except ValueError:
            self.interface = args[2]
        except IndexError:
            pass


        # interface/ttl 
        #
        try:
            self.ttl = int(args[3])
        except ValueError:
            self.interface = args[3]
        except IndexError:
            pass

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if self.interface:
            # Crude test to distinguish between interface names and IP addresses.
            interface_ip = None
            try:
                if socket.gethostbyname(self.interface) == self.interface:
                    interface_ip = self.interface
            except socket.gaierror:
                try:
                    import netifaces
                    interface_ip = netifaces.ifaddresses(self.interface)[0]['addr']
                except (ImportError, OSError, ValueError), msg:
                    collectd.notice("%s error setting interface: %s" % (NAME, msg))

            if interface_ip:
                try:
                    self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface_ip))
                except socket.error, msg:
                    collectd.notice("%s error setting interface: %s" % (NAME, msg))
            else:
                # Fudge self.interface to make self.__repr__() look better
                self.interface = '<invalid>'
                

        if self.ttl:
            try:
                self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.ttl)
            except socket.error, msg:
                collectd.notice("%s error setting TTL to %d for host %s port %s: %s" % 
                                 (NAME, self.ttl, self.host, self.port, msg))
                # Fudge self.ttl to make self.__repr__() look better
                self.ttl = '<invalid>'

    def flush(self, message):
        try:
            collectd.debug("%s.UdpWriter.flush: %s:%s %s" % (NAME, self.host, self.port, message))
            self.sock.sendto(message, (self.host, self.port))
        except (TypeError, socket.error), msg:
            collectd.warning("%s error sending to host %s port %d: %s" %
                             (NAME, self.host, self.port, msg))

        
    def shutdown(self):
        collectd.debug("%s.%s.close()" % (NAME, self))
        try:
            self.sock.close()
        except socket.error:
            pass

    
    def __repr__(self):
        return "UdpWriter(host=%s, port=%s, interface=%s, ttl=%s, sock=%s)" % \
                (self.host, self.port, self.interface, self.ttl, self.sock)


def read_types_db(path_to_typesdb):

    global TYPES

    try:
        with open(path_to_typesdb) as fp:
            for line in fp:
                fields = re.split(r'[,\s]+', line.strip())

                # Skip comments
                if fields[0].startswith('#'):
                    continue

                name = fields[0]

                if len(fields) < 2:
                    collectd.notice("%s configuration error: %s in %s is missing definition" % (NAME, name, path_to_typesdb))
                    continue

                name = fields[0]

                TYPES[name] = []

                for field in fields[1:]:
                    fields2 = field.split(':')

                    if len(fields2) < 4:
                        collectd.notice("%s configuration error: %s %s has wrong format" % (NAME, name, field))
                        continue

                    dsname = fields2[0]
                    dstype = fields2[1].lower()

                    if fields2[2] == 'U':
                        dsmin = None
                    else:
                        dsmin = float(fields2[2])

                    if fields2[3] == 'U':
                        dsmax = None
                    else:
                        dsmax = float(fields2[3])

                    TYPES[name].append((dsname, dstype, dsmin, dsmax))

                collectd.debug("%s.read_types_db: TYPES[%s]=%s" % (NAME, name, TYPES[name]))
                
 
                

    except IOError, msg:
        collectd.notice("%s configuration error: %s - %s" % (NAME, path_to_typesdb, msg))



def configure_callback(config):
    """Receive configuration block"""

    global WRITERS
    global TYPES_DB


    for node in config.children:
        key = node.key.lower()
        collectd.debug("%s.configure_callback: key=%s values=%s" % (NAME, key, node.values))


        # Try to extract format
        #
        try:
            formatter = FORMATTER_MAP[node.values[0].lower()]()
            args = node.values[1:]
        except (KeyError):
            formatter = DEFAULT_FORMATTER()
            args = node.values
        

        if key == 'typesdb':
            try:
                TYPES_DB.append(node.values[0])
            except IndexError:
                collectd.notice("%s configuration error: path to types.db missing" % (NAME))
                continue

        elif key == 'udp':
            try:
                WRITERS.append(UdpWriter(formatter, *args))
            except:
                pass

        else:
            collectd.notice("%s configuration error: unknown key %s" % (NAME, key))
            continue


    collectd.debug("%s.configure_callback: TYPES_DB=%s" % (NAME, TYPES_DB))
    collectd.debug("%s.configure_callback: WRITERS=%s" % (NAME, WRITERS))


    for types_db in TYPES_DB:
        read_types_db(types_db)


def init_callback(*args):
    """
    Start all writer threads.
    """

    for writer in WRITERS:
        writer.daemon = True
        writer.start()


def shutdown_callback():
    collectd.debug("%s.shutdown_callback" % (NAME))

    # Write ``None`` to all writer threads to signal shutdown.
    #
    for writer in WRITERS:
        writer.shutdown()


def write_callback(values_object):
    """
    Pass values_object to all `WRITERS`.

    :param values: Instance of `collectd.Values`.

    An example of `values` is shown below. It may also contain `plugin_instance`
    and `type_instance` attributes. The `dsname`, `dstype`, `dsmin` and
    `dsmax` fields are are not present in `collectd.Values`. They are
    added in the `BaseFormatter.convert_values_to_dict()` method if possible.

      collectd.Values(type='load', plugin='load', host='localhost', time=1432083347.3517618,
                      interval=300.0, values=[0.0, 0.01, 0.050000000000000003])

    """

    collectd.debug('%s.write_callback: values_object=%s' % (NAME, values_object))

    with LOCK:
        for writer in WRITERS:
            writer.write(values_object)
        

# Register callbacks
#
collectd.register_config(configure_callback)
collectd.register_shutdown(shutdown_callback)
collectd.register_write(write_callback)
collectd.register_init(init_callback)


WRITER_MAP = {
    'udp': UdpWriter
}

FORMATTER_MAP = {
    'json': JsonFormatter,
    'keyval': KeyvalFormatter
}

DEFAULT_FORMATTER = JsonFormatter
