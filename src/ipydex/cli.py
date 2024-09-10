"""
This module contains the entry points for command line scripts, see pyproject.toml.
"""

import sys
import ipydex

def main():
    print("ipydex running")


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

    if 0:
        ipydex.IPS()
