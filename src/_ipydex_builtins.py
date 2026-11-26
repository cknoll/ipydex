"""
Optional builtins for ipydex: `IPS()` and `activate_ips_on_exception()` without import.

Activation (per environment): `ipydex --install-builtins`
    This writes the file `ipydex_builtins.pth` into the site-packages directory of the current
    Python environment. Python executes it at every interpreter start; it imports this module.
Deactivation: `ipydex --uninstall-builtins`

Design goal: no side effects at interpreter start except two additional names in `builtins`.
In particular, this module must NOT import ipydex (or IPython): `import ipydex` replaces
`sys.excepthook` and takes about one second. ipydex is imported only when one of the functions
below is called for the first time. That's why this is a top-level module and not part of the
`ipydex` package (importing `ipydex.<anything>` would execute `ipydex/__init__.py`).

Existing builtins with the same names are not overwritten. Names defined in a module (e.g. by
`from ipydex import IPS`) take precedence over builtins anyway.

IDE and linter warnings
-----------------------

Static analysis tools do not execute `.pth` files and thus report `IPS` as undefined name
(only relevant in source code; in the debug console of VS Code there is no linting). Options:

- Pylance (VS Code) / pyright: create a file `__builtins__.pyi` in the project root:

      def IPS(*args, **kwargs) -> None: ...
      def activate_ips_on_exception(*args, **kwargs) -> None: ...

- ruff: in `pyproject.toml`: `[tool.ruff]` → `builtins = ["IPS", "activate_ips_on_exception"]`
- flake8: in `.flake8` or `setup.cfg`: `builtins = IPS,activate_ips_on_exception`
- alternatively: just write the import explicitly (`from ipydex import IPS`).
"""

import builtins
import sys


def _load_ipydex():
    try:
        import ipydex
    except ImportError as ex:
        msg = (
            "ipydex builtins are active (file `ipydex_builtins.pth` in site-packages) but ipydex "
            "cannot be imported. Reinstall ipydex or delete that file."
        )
        raise ImportError(msg) from ex
    return ipydex


def IPS(*args, **kwargs):
    """Lazy wrapper for `ipydex.IPS` (see there)."""
    ipydex = _load_ipydex()
    # pass the caller's frame such that this wrapper frame is transparent for IPS
    # (relevant for the frame list and the detection of the debug console)
    return ipydex.IPS(*args, _caller_frame=sys._getframe(1), **kwargs)


def activate_ips_on_exception(*args, **kwargs):
    """Lazy wrapper for `ipydex.activate_ips_on_exception` (see there)."""
    return _load_ipydex().activate_ips_on_exception(*args, **kwargs)


def _install():
    for func in (IPS, activate_ips_on_exception):
        if not hasattr(builtins, func.__name__):
            setattr(builtins, func.__name__, func)


_install()
