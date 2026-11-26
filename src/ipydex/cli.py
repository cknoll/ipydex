"""
This module contains the entry points for command line scripts, see pyproject.toml.
"""

import argparse
import os
import sys
import sysconfig

PTH_FNAME = "ipydex_builtins.pth"

# Note: lines of .pth files which start with `import` are executed at interpreter start.
# The try-except prevents error messages at every interpreter start if ipydex was uninstalled
# but the .pth file was left behind (it is not part of the ipydex distribution).
PTH_CONTENT = "import sys; exec('try:\\n    import _ipydex_builtins\\nexcept ImportError:\\n    pass\\n')\n"


def _default_site_dir():
    return sysconfig.get_paths()["purelib"]


def install_builtins(site_dir=None):
    """
    Write the .pth file which makes `IPS` and `activate_ips_on_exception` available as builtins
    for the Python environment of `site_dir` (default: site-packages of the current interpreter).
    See `_ipydex_builtins.py` for details.

    :return:    path of the .pth file
    """
    site_dir = site_dir or _default_site_dir()
    path = os.path.join(site_dir, PTH_FNAME)
    with open(path, "w") as fh:
        fh.write(PTH_CONTENT)
    return path


def uninstall_builtins(site_dir=None):
    """
    Remove the .pth file written by `install_builtins`.

    :return:    path of the removed file or None if there was nothing to remove
    """
    site_dir = site_dir or _default_site_dir()
    path = os.path.join(site_dir, PTH_FNAME)
    if not os.path.isfile(path):
        return None
    os.remove(path)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ipydex", description="IPython based debugging and exploring tool")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--install-builtins",
        action="store_true",
        help="make `IPS()` and `activate_ips_on_exception()` available without import "
        "(for the current Python environment)",
    )
    group.add_argument("--uninstall-builtins", action="store_true", help="undo `--install-builtins`")
    group.add_argument("--version", action="store_true", help="print the version and exit")
    args = parser.parse_args(argv)

    if args.install_builtins:
        path = install_builtins()
        print(f"written: {path}")
        print(f"`IPS()` and `activate_ips_on_exception()` are now builtins for {sys.executable}")
    elif args.uninstall_builtins:
        path = uninstall_builtins()
        print(f"removed: {path}" if path else f"nothing to do: no {PTH_FNAME} in {_default_site_dir()}")
    elif args.version:
        from ipydex.release import __version__

        print(__version__)
    else:
        parser.print_help()


def catch():
    """
    execute a command in the context of an ipython kernel and catch exceptions with the ips_excepthook
    """
    from jupyter_console.app import ZMQTerminalIPythonApp

    sys.argv = [sys.argv[0], "--existing"]
    app = ZMQTerminalIPythonApp.instance()
    app.initialize(None)
    super(ZMQTerminalIPythonApp, app).start()

    code = """
    import ipydex
    import traceback
    try:
        failing_function()
    except Exception as ex:
        value, tb = traceback._parse_value_tb(ex, traceback._sentinel, traceback._sentinel)
        ipydex.ips_excepthook(type(ex), ex, tb)
    """.replace("\n    ", "\n")

    app.shell.run_cell(code)


if __name__ == "__main__":
    main()
