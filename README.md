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
          # Server "host" "port" "interface" "ttl"
          # Server "host" "port" "ttl" "interface"
          Server "host1.example.com" "54321"
          Server "192.168.9.8" "12345"
          Server "239.1.2.3" "44444" "eth0" "6"
          Server "239.9.8.7" "43210" "5" "192.168.2.1"
      </Module>
    </Plugin>
```

JSON format
-----------

The JSON encoding follows the [Collectd JSON](https://collectd.org/wiki/index.php/JSON) structure.
```
[
   {
     "values":  [1901474177],
     "dstypes":  ["counter"],
     "dsnames":    ["value"],
     "time":      1280959128,
     "interval":          10,
     "host":            "leeloo.octo.it",
     "plugin":          "cpu",
     "plugin_instance": "0",
     "type":            "cpu",
     "type_instance":   "idle"
   }
]
```

Future
------

Currently only sending data as UDP packets has been implemented. The plugin could be 
extended to write JSON to other outputs, e.g. files, UNIX sockets, databases,
and so forth.


Requirements
------------
 * collectd 4.9+


Development
-----------

I use the [gitflow](https://github.com/nvie/gitflow) Git plugin so the main development 
branch is ```develop``` and not ```master```.


Acknowledgements
----------------

Many thanks to the author of the [redis-plugin-for-collectd](http://powdahound.com/2010/06/redis-plugin-for-collectd/).
Reading through the code filled the gaps left by the official [python-plugin](https://collectd.org/documentation/manpages/collectd-python.5.shtml)
plugin.
