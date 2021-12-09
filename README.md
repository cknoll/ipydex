ipydex
======

[![CircleCI](https://circleci.com/gh/cknoll/ipydex/tree/master.svg?style=shield)](https://circleci.com/gh/cknoll/ipydex/tree/master)

[![Link to PyPi](https://img.shields.io/pypi/v/ipydex.svg)](https://pypi.python.org/pypi/ipydex)

\"IPython based debugging and exploring\"

The module contains two main parts:

displaytools
------------

-   a jupyter-notebook-extension (`%loadext ipydex.displaytools`)
-   introduces magic comments (like `##:`, `##:T`, `##:S`) which cause
    that either the return value or the right hand side of an assignment
    of a line is displayed (`T` means additional transposition and `S`
    means only `.shape` attribute is displayed)
-   display intermediate results (→ more readable notebooks), without
    introducing additional `print` or `display` statements
-   Example invocation: `x = np.random.rand() ##:`
    -   inserts the line `display("x := {}".format(x))` to the source
        code of the cell (before its execution)
-   see
    [documentation-notebook](http://nbviewer.jupyter.org/github/cknoll/ipydex/blob/master/examples/displaytools-example.ipynb)

**Security advice**: Because the extension manipulates the source code
before its execution, it might cause unwanted and strange behavior.
Thus, this program is distributed in the hope that it will be useful,
*but without any warranty*.

Useful functions
----------------

The following functions are meant to be used in ordinary python-scripts:

-   `IPS()`
    -   start an embedded IPython shell in the calling scope
    -   useful to explore what objects are available and what are their
        abilities
    -   some additional features compared to `IPython.embed()`
-   `ST()`
    -   start the IPython debugger
-   `activate_ips_on_exception()`
    -   activate an embedded IPython shell in the scope where an
        exception occurred
    -   useful to investigate what happened
-   `dirsearch(name, obj)`
    -   search the keys of a dict or the attributes of an object
    -   useful to explore semi known modules, classes and
        data-structures

Notes
=====

This package is not yet as well tested as it would be necessary and it would deserve some refactoring.
Nevertheless it might be useful.
