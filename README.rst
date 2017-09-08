ipydex
======

.. image:: https://img.shields.io/pypi/v/ipydex.svg
    :target: https://pypi.python.org/pypi/ipydex
    :alt: Link to PyPi


"IPython based debugging and exploring"

The module contains the following functions:

* ``IPS()``

  - start an embedded IPython shell in the calling scope
  
  - useful to explore what objects are available and what are their abilities
  
* ``ST()``

  - start the IPython debugger
  
* ``activate_ips_on_exception()``

  - activate an embedded IPython shell in the scope where an exception occurred
  
  - useful to investigated what happend
  
* ``dirsearch(name, obj)``

  - search the keys of a dict or the attributes of an object
  
  - useful to explore semi known modules, classes and data-structures


Notes
=====
This package is not well tested, would deserve some solid refactoring.
