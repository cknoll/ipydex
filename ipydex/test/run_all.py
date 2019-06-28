
import os
import inspect
import unittest
import importlib

# this module enables the command: python -c "from ipydex.test import run_all; run_all()"


def run_all():

    mod_name = __name__.split('.')[0]
    release = importlib.import_module(mod_name+".release")

    print("Running all tests for module `{}` {}.".format(mod_name, release.__version__))

    current_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    loader = unittest.TestLoader()
    suite = loader.discover(current_path)

    runner = unittest.TextTestRunner()
    res = runner.run(suite)

    # cause CI to fail if tests have failed (otherwise this script returns 0 despite of failing tests)
    assert res.wasSuccessful()


if __name__ == '__main__':
    run_all()


