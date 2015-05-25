Developing ```write_json.py```
==============================

This document contains various notes (mostly to myself) about
developing ```write_json.py```. 


Branching model
---------------

I follow the branching model described in 
[A successful Git branching model](http://nvie.com/posts/a-successful-git-branching-model/)
which is supported through the [gitflow](https://github.com/nvie/gitflow) Git plugin.

* No development occurs on the `master` branch.
* The 'main' branch is `develop` but actual development should happen in 
  feature branches.
* Releases are tagged.


JSON
----

The Collectd web site provides an example of 
[JSON encoded values](https://collectd.org/wiki/index.php/JSON). The problem with 
this example is that it contains information (```dstypes``` and ```dsnames```) that
are not available to a Collectd Python plugin. This information is contained
in the Collectd ```types.db``. For example the entry for system ```load``` looks like
this.
```
load     shortterm:GAUGE:0:5000, midterm:GAUGE:0:5000, longterm:GAUGE:0:5000
```
Plugins in C/C++ 

