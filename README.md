# ipydex – **ipy**thon based **de**bugging and **ex**ploring


[![CircleCI](https://circleci.com/gh/cknoll/ipydex/tree/main.svg?style=shield)](https://circleci.com/gh/cknoll/ipydex/tree/main)
[![PyPI version](https://badge.fury.io/py/ipydex.svg)](https://badge.fury.io/py/ipydex)


The module contains two main components:

## Component 1: displaytools


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
    [documentation-notebook](http://nbviewer.jupyter.org/github/cknoll/ipydex/blob/main/examples/displaytools-example.ipynb)

**Security advice**: Because the extension manipulates the source code
before its execution, it might cause unwanted and strange behavior.
Thus, this program is distributed in the hope that it will be useful,
*but without any warranty*.

## Component 2: Useful Python functions and classes


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
    -   see below how to make use of in connection with [pytest](https://pypi.org/project/pytest/)
    - set magic variable `__mu` to `1` and exit the shell (CTRL+D) in order to move up one level in the frame stack
        - useful to determine the reason of an exception (which is often not in the same frame as where the exception finally happened)
-   `dirsearch(name, obj)`
    -   search the keys of a dict or the attributes of an object
    -   useful to explore semi known modules, classes and
        data-structures
-   `Container`
    - versatile class for debugging and convenient creation of case-specific data structures

## Notes

This package has grown over more than a decade. It is only partially covered by unittests. Its internals are not exemplary for recommended coding practice. It certainly contains bugs. No warranty for any purpose is given.

Nevertheless it might be useful.

### ipydex Usage in Unittests (Using pytest)

In your test directory add a file `conftest.py`:

```python

# This file enables the ipydex excepthook together with pytest.
# The custom excepthook can be activated by `activate_ips_on_exception()`
# in your test-file.

# To prevent unwanted dependencies the custom excepthook is only active if a
# special environment variable is "True". Use the following command for this:
#
# export PYTEST_IPS=True


import os
if os.getenv("PYTEST_IPS") == "True":

    import ipydex

    # This function is just an optional reminder
    def pytest_runtest_setup(item):
        print("This invocation of pytest is customized")


    def pytest_exception_interact(node, call, report):
        ipydex.ips_excepthook(
            call.excinfo.type, call.excinfo.value, call.excinfo.tb, frame_upcount=0
        )
```


### Use `ipydex.Container` for Debugging e.g. in Jupyter Notebooks

```python
from ipydex import Container

# ...

def func1(x, debug_container=None):
    y = complicated_func1(x)
    res = complicated_func2(x, y)

    # convenient way to non-intrusively gather internal information
    if debug_container is not None:
        debug_container.fetch_locals()
        # now the following attributes exists:
        # debug_container.x
        # debug_container.y
        # debug_container.res

    return res

# create debug container
dc = Container()

# call the function which should be debugged, pass the container
# as keyword argument
res = func1(100, debug_container=dc)

# after the function returned dc contains new attributes which allow to
# investigate *internal* behavior of func1
print(C.x)
print(C.y)
print(C.res)
```
