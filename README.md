# ipydex – **ipy**thon based **de**bugging and **ex**ploring


[![CircleCI](https://circleci.com/gh/cknoll/ipydex/tree/main.svg?style=shield)](https://circleci.com/gh/cknoll/ipydex/tree/main)
[![PyPI version](https://badge.fury.io/py/ipydex.svg)](https://badge.fury.io/py/ipydex)

ipydex helps to find out what is going on inside a running Python program: it drops you into a full
IPython shell exactly where you need it – at an arbitrary line of code, where an exception occurred,
or (new in 0.23.0) at the current position of the graphical debugger in VS Code.

## Installation

```bash
pip install ipydex
```

## Quick Start

```python
from ipydex import IPS

def compute(a, b):
    c = a * b
    IPS()  # opens an IPython shell here: `a`, `b`, `c` are available, exit with CTRL+D
    return c + 1
```

Before the shell opens, `IPS()` prints the list of calling frames, so you see where the shell
"wakes up". Some useful variants:

- `IPS(i == 3)`: only start the shell if the condition is true (e.g. inside a loop)
- run the program with the environment variable `IPS=0` (or `IPS=false`) to skip all `IPS()` calls
  without removing them from the code

## Overview

The package contains two components:

1. **Debugging and exploring functions** for ordinary Python scripts:

    | Name | Purpose |
    |---|---|
    | `IPS()` | start an embedded IPython shell in the calling scope (more robust than `IPython.embed()`, e.g. variables are also available inside list comprehensions and lambdas) |
    | `activate_ips_on_exception()` | start an IPython shell in the scope where an unhandled exception occurred |
    | `set_trace()` | start the IPython debugger (`from ipydex import set_trace`) |
    | `dirsearch(s, obj)` | search (case-insensitive) the attributes of an object or the keys of a dict; useful to explore half-known modules, classes and data structures |
    | `Container` | versatile class for debugging and for the convenient creation of case-specific data structures |

2. **displaytools**: a Jupyter notebook extension (see [below](#displaytools-jupyter-extension)).


## `IPS()` in the Debug Console of VS Code (new in 0.23.0)

Stepping through the code with the graphical debugger and exploring the state with a full IPython
shell can now be combined: while the debugger is paused, type

```python
IPS()
```

into the *Debug Console*. The shell is started in the frame which is currently selected in the
*Call Stack* view (i.e. you can also inspect the callers). Up to version 0.22 this did not work:
the shell ended up in an auxiliary frame of the debugger with a confusing frame list.

How it works in practice:

1. Set a breakpoint and start debugging (F5).
2. Step through the code (F10, F11) until you want to look closer.
3. Type `IPS()` into the Debug Console. The shell appears in the **terminal** of the debugged
   program (`"console": "integratedTerminal"`, the default in `launch.json`), not in the Debug
   Console. The Debug Console waits until the shell is closed.
4. Explore, close the shell (CTRL+D), continue stepping.

Notes:

- `IPS` must be available in the debugged code (`from ipydex import IPS`). Otherwise type
  `__import__("ipydex").IPS()`.
- Assignments to existing variables (e.g. `x = 5`) are written back to the paused frame by the
  debugger after the shell has been closed, i.e. they persist when you continue stepping.
- Calling `IPS()` from the code itself (outside the Debug Console) works as before.
- This relies on internals of pydevd (the debugger engine of debugpy, which is used by VS Code).
  If these change in a future version, `IPS()` falls back to the old behavior. PyCharm uses pydevd
  as well, but this has not been tested.


## IPython Shell on Exceptions

```python
from ipydex import activate_ips_on_exception
activate_ips_on_exception()

# ... code which might raise an exception
```

If an unhandled exception occurs, an IPython shell is started in the frame where it was raised.
Often the cause of an exception lies in a calling frame: set the magic variable `__mu = 1` and
exit the shell (CTRL+D) to move **u**p one level in the frame stack.

The environment variable `NO_IPS_EXCEPTHOOK` (any non-empty value) deactivates this, which is useful
if the program is called from another process (e.g. via `subprocess.run(...)`).

### Usage with pytest

In your test directory add a file `conftest.py`:

```python
# This file enables the ipydex excepthook together with pytest.
# To prevent unwanted dependencies the custom excepthook is only active if the
# environment variable PYTEST_IPS is "True", e.g.:
#
# PYTEST_IPS=True pytest test_foo.py

import os

if os.getenv("PYTEST_IPS") == "True":

    import ipydex

    # This function is just an optional reminder
    def pytest_runtest_setup(item):
        print("This invocation of pytest is customized")

    def pytest_exception_interact(node, call, report):
        # the option `leave_ut=True` causes the excepthook to leave functions
        # from the unittest package. This is a convenience feature such that
        # the shell wakes up in your own test code
        ipydex.ips_excepthook(call.excinfo.type, call.excinfo.value, call.excinfo.tb, leave_ut=True)
```


## Traceback Format After `import ipydex`

Importing ipydex replaces `sys.excepthook` by IPython's colored traceback formatter
(`ultratb.FormattedTB`). The level of detail is controlled by the environment variable
`IPYDEX_TB_MODE`:

| Value | Output |
|---|---|
| `plain` (default) | compact, like the normal Python traceback (but colored) |
| `context` | additionally shows some lines of source code before and after the relevant line of each frame |
| `verbose` | like `context`, plus the values of function arguments and of the variables in the relevant line of each frame |

The values are case-insensitive; `0`, `1`, `2` are accepted as well. An invalid value causes a
warning and the fallback to `plain`.

Note: in `verbose` mode the variable values are printed completely (via `repr`). Large lists or
dicts can make the traceback extremely long, which is especially inefficient for LLM agents
processing the output.

Example:

```bash
IPYDEX_TB_MODE=verbose python my_script.py
```

The mode can also be set from within Python (this overrides the environment variable):

```python
import ipydex
ipydex.color_excepthook(mode="context")  # or ip_syshook(...) (alias)
```

Note: the traceback printed by `activate_ips_on_exception()` before the IPython shell starts is not
affected by this setting.


## `Container` for Non-Intrusive Debugging (e.g. in Jupyter Notebooks)

```python
from ipydex import Container

def func1(x, debug_container=None):
    y = complicated_func1(x)
    res = complicated_func2(x, y)

    # convenient way to non-intrusively gather internal information
    if debug_container is not None:
        debug_container.fetch_locals()
        # now the following attributes exist:
        # debug_container.x, debug_container.y, debug_container.res

    return res

# create debug container
dc = Container()

# call the function which should be debugged, pass the container as keyword argument
res = func1(100, debug_container=dc)

# after the function returned, dc contains new attributes which allow to
# investigate the *internal* behavior of func1
print(dc.x)
print(dc.y)
print(dc.res)
```


## displaytools (Jupyter Extension)

-   load the extension in a notebook: `%load_ext ipydex.displaytools`
-   introduces magic comments (like `##:`, `##:T`, `##:S`) which cause that either the return
    value or the right hand side of an assignment of a line is displayed (`T` means additional
    transposition and `S` means only the `.shape` attribute is displayed)
-   display intermediate results (→ more readable notebooks) without introducing additional
    `print` or `display` statements
-   Example: `x = np.random.rand() ##:`
    -   inserts the line `display("x := {}".format(x))` to the source code of the cell (before its
        execution)
-   see the
    [documentation notebook](https://nbviewer.jupyter.org/github/cknoll/ipydex/blob/main/examples/displaytools-example.ipynb)

**Security advice**: Because the extension manipulates the source code before its execution, it
might cause unwanted and strange behavior.


## Environment Variables

| Variable | Effect |
|---|---|
| `IPS=0` (or `false`) | skip all `IPS()` calls |
| `IPYDEX_TB_MODE` | detail level of tracebacks: `plain`, `context`, `verbose` (see above) |
| `NO_IPS_EXCEPTHOOK` | (any non-empty value) deactivate `activate_ips_on_exception()` |


## Notes

This package has grown over more than a decade. It is only partially covered by unit tests. Its
internals are not exemplary for recommended coding practice. It certainly contains bugs. It is
distributed in the hope that it will be useful, but *without any warranty* (see `LICENSE`, GPLv3).
