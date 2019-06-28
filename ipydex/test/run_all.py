
import os
import inspect
import unittest

# this module enables the command: python -c "from ipydex.test import run_all; run_all()"


def run_all():
    current_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    loader = unittest.TestLoader()
    suite = loader.discover(current_path)

    runner = unittest.TextTestRunner()
    res = runner.run(suite)

    # cause CI to fail if tests have failed (otherwise this script returns 0 despite of failing tests)
    assert res.wasSuccessful()


if __name__ == '__main__':
    run_all()


