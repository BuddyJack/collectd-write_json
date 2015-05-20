Collectd write_json plugin
==========================

The ```write_json``` plugin for [collectd](http://collectd.org) sends data 
over the network in [JSON](http://www.json.org/) format. The main purpose
is to be able to send Collectd data to third-party systems in an easily
parseable format.

The plugin is implemented as a 
Collectd [Python plugin](http://collectd.org/documentation/manpages/collectd-python.5.shtml).

Installation
------------
 1. The file write_json.py must be copied to a location that is available through
    ```sys.path```. If necessary adjust the ```ModulePath``` in the configuration.
 2. Configure the plugin (see below).
 3. Restart collectd.

Configuration
-------------
Similar to the [Network plugin](https://collectd.org/documentation/manpages/collectd.conf.5.shtml#plugin_network)
this plugin can send to multiple destinations. In contrast to the network plugin sending 
data is supported and none of the security features have been implemented. 
There is no default UDP port allocation so the port must always be configured explicitly.

When sending to a multicast group one can also configure a TTL and/or outgoing interface.
The outgoing interface can be specified by IP address or name. Specifiying the interface
by name may be more convenient but requires the [netifaces](https://pypi.python.org/pypi/netifaces/) 
to be installed.

Please check the Collectd log output for any warnings in relation to the configuration
of the ```write_json``` plugin. Configuration errors are generally skipped and logged 
as 'notice'. Collectd will start but the ```write_json``` plugin may not behave as
expected.


```
    <LoadPlugin python>
      Globals true
    </LoadPlugin>

    <Plugin python>
      ModulePath "/path/to/directory/containing_write_json"
      Import "write_json"

      <Module write_json>
          # Paths to the types.db files are needed here(!) with any 
          # Collectd version older than November 2014. The built-in
          # defaults are /usr/share/collectd/types.db and
          # /usr/local/share/collectd/types.db.
          TypesDB "/my/custom/types.db"
          TypesDB "/my/other/custom/types.db"
          
          # Send JSON over UDP:
          # UDP "host" "port" "interface" "ttl"
          # UDP "host" "port" "ttl" "interface"
          UDP "host1.example.com" "54321"
          UDP "192.168.9.8" "12345"
          UDP "239.1.2.3" "44444" "eth0" "6"
          UDP "239.9.8.7" "43210" "5" "192.168.2.1"
      </Module>
    </Plugin>
```

JSON format
-----------

The JSON encoding follows the [Collectd JSON](https://collectd.org/wiki/index.php/JSON) structure
(the ````min``` and ```max``` information is not included in the example shown on the
Collectd web site but they could be easily added as additional fields).
```
[
    {
        "dsnames": ['shorttem', 'midterm', 'longterm'],
        "dstypes": ['gauge', 'gauge', 'gauge'],
        "host": "localhost",
        "interval": 5.0,
        "plugin": "load",
        "plugin_instance": "",
        "time": 1432086959.8153536,
        "type": "load",
        "type_instance": "",
        "values": [
            0.0,
            0.01,
            0.050000000000000003
        ]
    }
]
```
Unfortunately only very recent releases of Collectd allow Python
based plugins to retrive the ```dsnames``` and ```dstypes``` fields
(https://github.com/collectd/collectd/issues/771). Earlier
versions will leave those fields empty unless the ```write_json``` configuration
section has ```TypesDB``` entries for the data type.
```
[
    {
        "dsnames": [],
        "dstypes": [],
        "host": "localhost",
        "interval": 5.0,
        "plugin": "load",
        "plugin_instance": "",
        "time": 1432086959.8153536,
        "type": "load",
        "type_instance": "",
        "values": [
            0.0,
            0.01,
            0.050000000000000003
        ]
    }
]
```
Individual JSON structures will be delimited by newline ```\n``` if they are emitted
together.

Future
------

Currently only sending data as UDP packets has been implemented. The plugin could be 
extended to write JSON data by different methods; TCP, files, UNIX sockets, databases,
and so forth.


Requirements
------------
 * collectd 4.9+


Development
-----------

See ```DEVELOPMENT.md``` for details.


Acknowledgements
----------------

Many thanks to the author of the [redis-plugin-for-collectd](http://powdahound.com/2010/06/redis-plugin-for-collectd/).
Reading through the code filled the gaps left by the official [python-plugin](https://collectd.org/documentation/manpages/collectd-python.5.shtml)
plugin.
