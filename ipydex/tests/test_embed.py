"""Test different ways of embedding IPython via ipydex"""


# Created 2019-06-12 12:04:13 by C. Knoll
# This file ist strongly inspired by
# ipython-master/IPython/terminal/tests/test_embed.py (BSD licensed)
#  Copyright (C) 2013 The IPython Development Team


import os
import subprocess
import sys
import unittest
from IPython.utils.tempdir import NamedFileInTemporaryDirectory


_sample_embed_ips1 = b"""
from ipydex import IPS

a = 3
b = 14
print(a, '.', b)

IPS()

print('bye!')

"""

_exit = b"exit\r"


def write_string_to_file_script(bytearr, fname="tmp.py"):
    """
    Helper function to write the string to a file for better debugging.

    :param bytearr: bytearray (encoded string) containing python code
    :param fname:   filename (optinal)
    :return:
    """

    with open(fname, "wb") as f:
        f.write(bytearr)

    print("\n{}\n\n written to {}.".format(bytearr, fname))


# noinspection PyPep8Naming,PyUnresolvedReferences,PyUnusedLocal
class Tests(unittest.TestCase):

    def setUp(self):
        pass

    def test_ipython_embed(self):
        """test that `IPython.embed()` works"""
        with NamedFileInTemporaryDirectory('file_with_embed.py') as f:
            f.write(_sample_embed_ips1)
            f.flush()
            f.close()  # otherwise msft won't be able to read the file

            # run `python file_with_embed.py`
            cmd = [sys.executable, f.name]
            env = os.environ.copy()
            env['IPY_TEST_SIMPLE_PROMPT'] = '1'

            p = subprocess.Popen(cmd, env=env, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate(_exit)
            std = out.decode('UTF-8')

            self.assertEqual(p.returncode, 0)
            self.assertIn('3 . 14', std)
            self.assertIn('IPython', std)
            self.assertIn('bye!', std)


if __name__ == "__main__":
    write_string_to_file_script(_sample_embed_ips1)


# other usefull techniques:
"""
    import pexpect
    ipy_prompt = r']:' #ansi color codes give problems matching beyond this
    env = os.environ.copy()
    env['IPY_TEST_SIMPLE_PROMPT'] = '1'


    child = pexpect.spawn(sys.executable, ['-m', 'IPython', '--colors=nocolor'],
                          env=env)
    child.timeout = 5 * IPYTHON_TESTING_TIMEOUT_SCALE
    child.expect(ipy_prompt)
    child.sendline("import IPython")
    child.expect(ipy_prompt)
    assert(child.expect(['true\r\n', 'false\r\n']) == 0)
    child.sendline('exit')
    child.close()

"""
