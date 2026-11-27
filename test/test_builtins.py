"""Test the optional builtins (`ipydex --install-builtins`, module `_ipydex_builtins`)."""

import builtins
import os
import subprocess
import sys
import tempfile
import unittest

import ipydex
import ipydex.cli


SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))


def run_python(code, site_dir, stdin_text=None):
    """Run code in a fresh interpreter for which `site_dir` is a site directory (-> .pth processing)."""
    full_code = f"import site; site.addsitedir({site_dir!r})\n" + code
    env = dict(os.environ, PYTHONPATH=SRC_DIR, IPYDEX_SUPPRESS_VENV_WARNING="1")
    env.pop("IPS", None)
    res = subprocess.run(
        [sys.executable, "-c", full_code], input=stdin_text, capture_output=True, text=True, env=env, timeout=60
    )
    return res


class TestInstallBuiltins(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.site_dir = self.tmpdir.name

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_install_uninstall(self):
        path = ipydex.cli.install_builtins(self.site_dir)
        self.assertEqual(os.path.basename(path), ipydex.cli.PTH_FNAME)
        self.assertTrue(os.path.isfile(path))

        # idempotent
        ipydex.cli.install_builtins(self.site_dir)
        self.assertEqual(os.listdir(self.site_dir), [ipydex.cli.PTH_FNAME])

        self.assertEqual(ipydex.cli.uninstall_builtins(self.site_dir), path)
        self.assertFalse(os.path.exists(path))
        self.assertIsNone(ipydex.cli.uninstall_builtins(self.site_dir))

    def test_no_side_effects_at_startup(self):
        ipydex.cli.install_builtins(self.site_dir)
        code = (
            "import sys\n"
            "print(IPS.__module__, activate_ips_on_exception.__module__)\n"
            "print('ipydex' in sys.modules, 'IPython' in sys.modules, sys.excepthook is sys.__excepthook__)\n"
        )
        res = run_python(code, self.site_dir)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(res.stdout.split(), ["_ipydex_builtins", "_ipydex_builtins", "False", "False", "True"])

    def test_stale_pth_file_is_silent(self):
        # simulate an uninstalled ipydex: .pth file present, but module `_ipydex_builtins` not importable
        ipydex.cli.install_builtins(self.site_dir)
        env = dict(os.environ, PYTHONNOUSERSITE="1")
        env.pop("PYTHONPATH", None)
        code = (
            "import sys; sys.modules['_ipydex_builtins'] = None\n"  # makes the import fail
            f"import site; site.addsitedir({self.site_dir!r})\n"
            "print('IPS' in dir(__builtins__))\n"
        )
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(res.stdout.strip(), "False")
        self.assertEqual(res.stderr.strip(), "")

    def test_ips_via_builtin(self):
        ipydex.cli.install_builtins(self.site_dir)
        code = (
            "def func_with_shell():\n"
            "    local_var = 42\n"
            "    for i in range(3):\n"
            "        IPS(i == 1)\n"
            "func_with_shell()\n"
        )
        res = run_python(code, self.site_dir, stdin_text="print('RESULT', local_var, i)\nexit\n")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("RESULT 42 1", res.stdout)
        # the shell was entered exactly once
        self.assertEqual(res.stdout.count("RESULT"), 1)
        # the frame list printed by IPS shows the caller but not the wrapper
        self.assertIn("func_with_shell", res.stdout)
        self.assertNotIn("_ipydex_builtins", res.stdout)


class TestBuiltinsWrapper(unittest.TestCase):

    def setUp(self):
        self.saved_builtins = {name: getattr(builtins, name, None) for name in ("IPS", "activate_ips_on_exception")}
        self.original_IPS = ipydex.IPS

    def tearDown(self):
        ipydex.IPS = self.original_IPS
        for name, value in self.saved_builtins.items():
            if value is None:
                if hasattr(builtins, name):
                    delattr(builtins, name)
            else:
                setattr(builtins, name, value)

    def test_wrapper_passes_caller_frame(self):
        import inspect
        import _ipydex_builtins

        calls = []
        ipydex.IPS = lambda *args, **kwargs: calls.append((args, kwargs))

        _ipydex_builtins.IPS(True, print_tb=False)
        self.assertEqual(len(calls), 1)
        args, kwargs = calls[0]
        self.assertEqual(args, (True,))
        self.assertEqual(kwargs["print_tb"], False)
        self.assertIs(kwargs["_caller_frame"], inspect.currentframe())

    def test_existing_builtins_are_not_overwritten(self):
        import _ipydex_builtins

        sentinel = object()
        setattr(builtins, "IPS", sentinel)
        _ipydex_builtins._install()
        self.assertIs(getattr(builtins, "IPS"), sentinel)


if __name__ == "__main__":
    unittest.main()
