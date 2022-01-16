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
import pexpect

from IPython import embed as IPS


# define some test source code

_exit = b"exit\r"
_mu1 = b"__mu = 1; exit\n"

ipy_prompt = r']:'


_sample_embed_ips1 = b"""
from ipydex import IPS

a = 3
b = 14
print(a, '.', b)

IPS(color_scheme="nocolor")

print('bye!')

"""

_sample_embed_ips2 = b'''
import sys

from ipydex import IPS, activate_ips_on_exception
activate_ips_on_exception()

def f1(x):
    name = "f1"
    
    print("x=", x)
    if x == 3.5:
        # provoke an exception
        1/0
    elif x > 4:
        # call interactive IPython
        IPS(color_scheme="nocolor")
    else:
        f2(x)


def f2(x):
    name = "f2"
    f1(x+1)


def f3(x):
    name = "f3"
    a = 1
    b = [1, 3]

    f2(x)

arg = float(sys.argv[1])
# arg == 1.5 -> exception
# arg == 1.0 -> IPS  

f3(arg)

'''

_sample_embed_dbg1 = b'''

from ipydex import Pdb_instance, set_trace

x = 10

def f1():
    a = 7
    b = 8

    return a + b

Pdb_instance.set_colors("NoColor")
set_trace()



f1()
y = 20

'''


def write_string_to_file_script(bytearr, fname="tmp.py"):
    """
    Helper function to write the string to a file for better debugging.

    :param bytearr: bytearray (encoded string) containing python code
    :param fname:   filename (optional)
    :return:
    """

    with open(fname, "wb") as f:
        f.write(bytearr)

    print("\n{}\n\n written to {}.".format(bytearr.decode(), fname))


def perform_replacements(out, fname):
    """

    Replace random filename with generic one and fix some compatibility issue with py3.5

    :param out:
    :param fname:
    :return:
    """
    out = out.replace(fname.encode(), b"/tmp/tmpdir/filename.py")

    # fix some compatibility issue with py3.5
    out = out.replace(b'<module>\x1b[1;34m(x)\x1b[0m', b'<module>\x1b[1;34m\x1b[0m')
    out = out.replace(b'<module>\x1b[1;34m()\x1b[0m', b'<module>\x1b[1;34m\x1b[0m')

    return out


def get_adapted_out(spawn_instance, fname):
    """

    :param spawn_instance:  instance of pexpect.spawn(..)
    :param fname:   filename (optional)

    :return: bytearray of .before + .after where the random filename has been replaced

    Note that (https://pexpect.readthedocs.io/en/stable/overview.html):
        After each call to expect() the before and after properties will be set to
        the text printed by child application. The before property will contain all
        text up to the expected string pattern. The after string will contain the
        text that was matched by the expected pattern.
    """

    assert isinstance(spawn_instance, pexpect.pty_spawn.spawn)

    out = spawn_instance.before + spawn_instance.after
    return perform_replacements(out, fname)


def ipy_io(spawn_instance, fname, command):
    """

    :param spawn_instance:
    :param fname:
    :param command:
    :return:
    """

    spawn_instance.send(command)
    spawn_instance.expect(ipy_prompt)
    out_a = get_adapted_out(spawn_instance, fname)

    return out_a


# noinspection PyPep8Naming,PyUnresolvedReferences,PyUnusedLocal
class TestE1(unittest.TestCase):

    def setUp(self):
        pass

    def test_encoding(self):
        # if this fails, other tests must be adapted w.r.t. encode/decode
        self.assertEqual(sys.getdefaultencoding(), "utf-8")

    def test_ipython_embed1(self):
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

    def test_ipython_embed2(self):
        with NamedFileInTemporaryDirectory('file_with_embed.py') as f:
            f.write(_sample_embed_ips2)
            f.flush()
            f.close()  # otherwise msft won't be able to read the file

            fname = f.name

            # run `python file_with_embed.py`
            cmd1 = [sys.executable, fname, "1.0"]
            env = os.environ.copy()
            env['IPY_TEST_SIMPLE_PROMPT'] = '1'

            p = subprocess.Popen(cmd1, env=env, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # expected output (including control chars for colors etc)
            # noinspection PyPep8
            eout1 = b'\x1b[22;0t\x1b]0;IPython: repo/test\x07x= 2.0\nx= 3.0\nx= 4.0\nx= 5.0\nPython 3.8.6 | packaged by conda-forge | (default, Nov 27 2020, 19:31:52) \nType \'copyright\', \'credits\' or \'license\' for more information\nIPython 8.0.0 -- An enhanced Interactive Python. Type \'?\' for help.\n\n\nFile \x1b[1;32m/tmp/tmpdir/filename.py:37\x1b[0m, in \x1b[0;36m<module>\x1b[1;34m\x1b[0m\n\x1b[0;32m     34\x1b[0m \x1b[38;5;66;03m# arg == 1.5 -> exception\x1b[39;00m\n\x1b[0;32m     35\x1b[0m \x1b[38;5;66;03m# arg == 1.0 -> IPS  \x1b[39;00m\n\x1b[1;32m---> 37\x1b[0m f3(arg)\n\nFile \x1b[1;32m/tmp/tmpdir/filename.py:31\x1b[0m, in \x1b[0;36mf3\x1b[1;34m(x)\x1b[0m\n\x1b[0;32m     29\x1b[0m b \x1b[38;5;241m=\x1b[39m [\x1b[38;5;241m1\x1b[39m, \x1b[38;5;241m3\x1b[39m]\n\x1b[1;32m---> 31\x1b[0m f2(x)\n\nFile \x1b[1;32m/tmp/tmpdir/filename.py:23\x1b[0m, in \x1b[0;36mf2\x1b[1;34m(x)\x1b[0m\n\x1b[0;32m     22\x1b[0m name \x1b[38;5;241m=\x1b[39m \x1b[38;5;124m"\x1b[39m\x1b[38;5;124mf2\x1b[39m\x1b[38;5;124m"\x1b[39m\n\x1b[1;32m---> 23\x1b[0m f1(x\x1b[38;5;241m+\x1b[39m\x1b[38;5;241m1\x1b[39m)\n\nFile \x1b[1;32m/tmp/tmpdir/filename.py:18\x1b[0m, in \x1b[0;36mf1\x1b[1;34m(x)\x1b[0m\n\x1b[0;32m     17\x1b[0m \x1b[38;5;28;01melse\x1b[39;00m:\n\x1b[1;32m---> 18\x1b[0m     f2(x)\n\nFile \x1b[1;32m/tmp/tmpdir/filename.py:23\x1b[0m, in \x1b[0;36mf2\x1b[1;34m(x)\x1b[0m\n\x1b[0;32m     22\x1b[0m name \x1b[38;5;241m=\x1b[39m \x1b[38;5;124m"\x1b[39m\x1b[38;5;124mf2\x1b[39m\x1b[38;5;124m"\x1b[39m\n\x1b[1;32m---> 23\x1b[0m f1(x\x1b[38;5;241m+\x1b[39m\x1b[38;5;241m1\x1b[39m)\n\nFile \x1b[1;32m/tmp/tmpdir/filename.py:18\x1b[0m, in \x1b[0;36mf1\x1b[1;34m(x)\x1b[0m\n\x1b[0;32m     17\x1b[0m \x1b[38;5;28;01melse\x1b[39;00m:\n\x1b[1;32m---> 18\x1b[0m     f2(x)\n\nFile \x1b[1;32m/tmp/tmpdir/filename.py:23\x1b[0m, in \x1b[0;36mf2\x1b[1;34m(x)\x1b[0m\n\x1b[0;32m     22\x1b[0m name \x1b[38;5;241m=\x1b[39m \x1b[38;5;124m"\x1b[39m\x1b[38;5;124mf2\x1b[39m\x1b[38;5;124m"\x1b[39m\n\x1b[1;32m---> 23\x1b[0m f1(x\x1b[38;5;241m+\x1b[39m\x1b[38;5;241m1\x1b[39m)\n\nFile \x1b[1;32m/tmp/tmpdir/filename.py:18\x1b[0m, in \x1b[0;36mf1\x1b[1;34m(x)\x1b[0m\n\x1b[0;32m     17\x1b[0m \x1b[38;5;28;01melse\x1b[39;00m:\n\x1b[1;32m---> 18\x1b[0m     f2(x)\n\nFile \x1b[1;32m/tmp/tmpdir/filename.py:23\x1b[0m, in \x1b[0;36mf2\x1b[1;34m(x)\x1b[0m\n\x1b[0;32m     22\x1b[0m name \x1b[38;5;241m=\x1b[39m \x1b[38;5;124m"\x1b[39m\x1b[38;5;124mf2\x1b[39m\x1b[38;5;124m"\x1b[39m\n\x1b[1;32m---> 23\x1b[0m f1(x\x1b[38;5;241m+\x1b[39m\x1b[38;5;241m1\x1b[39m)\n\nFile \x1b[1;32m/tmp/tmpdir/filename.py:16\x1b[0m, in \x1b[0;36mf1\x1b[1;34m(x)\x1b[0m\n\x1b[0;32m     14\x1b[0m \x1b[38;5;28;01melif\x1b[39;00m x \x1b[38;5;241m>\x1b[39m \x1b[38;5;241m4\x1b[39m:\n\x1b[0;32m     15\x1b[0m     \x1b[38;5;66;03m# call interactive IPython\x1b[39;00m\n\x1b[1;32m---> 16\x1b[0m     IPS()\n\n--- Interactive IPython Shell. Type `?`<enter> for help. ----\n\n\nIn [1]: \n'

            out, err = p.communicate(_exit)

            out_adapted = perform_replacements(out, fname)


            IPS()
            1/0


            self.assertIn(eout1, out_adapted)

            cmd2 = [sys.executable, fname, "1.5"]

            p = pexpect.spawn(sys.executable, [fname, "1.5"], env=env)

            p.expect(ipy_prompt)
            out_a = get_adapted_out(p, fname)

            # this is good to get an overview over calling history
            # print(out_a.decode())

            # here an ZeroDivision error is intentionally raised and provokes an IPython shell to start
            # we test, whether this shell displays all expected informations and behaves as we want

            eout = b'\x1b[22;0t\x1b]0;IPython: repo/test\x07x= 2.5\r\nx= 3.5\r\n\r\n\r\n\x1b[1;31m---------------------------------------------------------------------------\x1b[0m\r\n\x1b[1;31mZeroDivisionError\x1b[0m                         Traceback (most recent call last)\r\nFile \x1b[1;32m/tmp/tmpdir/filename.py:37\x1b[0m, in \x1b[0;36m<module>\x1b[1;34m\x1b[0m\r\n\x1b[0;32m     33\x1b[0m arg \x1b[38;5;241m=\x1b[39m \x1b[38;5;28mfloat\x1b[39m(sys\x1b[38;5;241m.\x1b[39margv[\x1b[38;5;241m1\x1b[39m])\r\n\x1b[0;32m     34\x1b[0m \x1b[38;5;66;03m# arg == 1.5 -> exception\x1b[39;00m\r\n\x1b[0;32m     35\x1b[0m \x1b[38;5;66;03m# arg == 1.0 -> IPS  \x1b[39;00m\r\n\x1b[1;32m---> 37\x1b[0m \x1b[43mf3\x1b[49m\x1b[43m(\x1b[49m\x1b[43marg\x1b[49m\x1b[43m)\x1b[49m\r\n\r\nFile \x1b[1;32m/tmp/tmpdir/filename.py:31\x1b[0m, in \x1b[0;36mf3\x1b[1;34m(x)\x1b[0m\r\n\x1b[0;32m     28\x1b[0m a \x1b[38;5;241m=\x1b[39m \x1b[38;5;241m1\x1b[39m\r\n\x1b[0;32m     29\x1b[0m b \x1b[38;5;241m=\x1b[39m [\x1b[38;5;241m1\x1b[39m, \x1b[38;5;241m3\x1b[39m]\r\n\x1b[1;32m---> 31\x1b[0m \x1b[43mf2\x1b[49m\x1b[43m(\x1b[49m\x1b[43mx\x1b[49m\x1b[43m)\x1b[49m\r\n\r\nFile \x1b[1;32m/tmp/tmpdir/filename.py:23\x1b[0m, in \x1b[0;36mf2\x1b[1;34m(x)\x1b[0m\r\n\x1b[0;32m     21\x1b[0m \x1b[38;5;28;01mdef\x1b[39;00m \x1b[38;5;21mf2\x1b[39m(x):\r\n\x1b[0;32m     22\x1b[0m     name \x1b[38;5;241m=\x1b[39m \x1b[38;5;124m"\x1b[39m\x1b[38;5;124mf2\x1b[39m\x1b[38;5;124m"\x1b[39m\r\n\x1b[1;32m---> 23\x1b[0m     \x1b[43mf1\x1b[49m\x1b[43m(\x1b[49m\x1b[43mx\x1b[49m\x1b[38;5;241;43m+\x1b[39;49m\x1b[38;5;241;43m1\x1b[39;49m\x1b[43m)\x1b[49m\r\n\r\nFile \x1b[1;32m/tmp/tmpdir/filename.py:18\x1b[0m, in \x1b[0;36mf1\x1b[1;34m(x)\x1b[0m\r\n\x1b[0;32m     16\x1b[0m     IPS()\r\n\x1b[0;32m     17\x1b[0m \x1b[38;5;28;01melse\x1b[39;00m:\r\n\x1b[1;32m---> 18\x1b[0m     \x1b[43mf2\x1b[49m\x1b[43m(\x1b[49m\x1b[43mx\x1b[49m\x1b[43m)\x1b[49m\r\n\r\nFile \x1b[1;32m/tmp/tmpdir/filename.py:23\x1b[0m, in \x1b[0;36mf2\x1b[1;34m(x)\x1b[0m\r\n\x1b[0;32m     21\x1b[0m \x1b[38;5;28;01mdef\x1b[39;00m \x1b[38;5;21mf2\x1b[39m(x):\r\n\x1b[0;32m     22\x1b[0m     name \x1b[38;5;241m=\x1b[39m \x1b[38;5;124m"\x1b[39m\x1b[38;5;124mf2\x1b[39m\x1b[38;5;124m"\x1b[39m\r\n\x1b[1;32m---> 23\x1b[0m     \x1b[43mf1\x1b[49m\x1b[43m(\x1b[49m\x1b[43mx\x1b[49m\x1b[38;5;241;43m+\x1b[39;49m\x1b[38;5;241;43m1\x1b[39;49m\x1b[43m)\x1b[49m\r\n\r\nFile \x1b[1;32m/tmp/tmpdir/filename.py:13\x1b[0m, in \x1b[0;36mf1\x1b[1;34m(x)\x1b[0m\r\n\x1b[0;32m     10\x1b[0m \x1b[38;5;28mprint\x1b[39m(\x1b[38;5;124m"\x1b[39m\x1b[38;5;124mx=\x1b[39m\x1b[38;5;124m"\x1b[39m, x)\r\n\x1b[0;32m     11\x1b[0m \x1b[38;5;28;01mif\x1b[39;00m x \x1b[38;5;241m==\x1b[39m \x1b[38;5;241m3.5\x1b[39m:\r\n\x1b[0;32m     12\x1b[0m     \x1b[38;5;66;03m# provoke an exception\x1b[39;00m\r\n\x1b[1;32m---> 13\x1b[0m     \x1b[38;5;241;43m1\x1b[39;49m\x1b[38;5;241;43m/\x1b[39;49m\x1b[38;5;241;43m0\x1b[39;49m\r\n\x1b[0;32m     14\x1b[0m \x1b[38;5;28;01melif\x1b[39;00m x \x1b[38;5;241m>\x1b[39m \x1b[38;5;241m4\x1b[39m:\r\n\x1b[0;32m     15\x1b[0m     \x1b[38;5;66;03m# call interactive IPython\x1b[39;00m\r\n\x1b[0;32m     16\x1b[0m     IPS()\r\n\r\n\x1b[1;31mZeroDivisionError\x1b[0m: division by zero\r\n\r\n\r\nPython 3.8.6 | packaged by conda-forge | (default, Nov 27 2020, 19:31:52) \r\nType \'copyright\', \'credits\' or \'license\' for more information\r\nIPython 8.0.0 -- An enhanced Interactive Python. Type \'?\' for help.\r\n\r\nIn [1]:'


            IPS()

            self.assertEqual(eout, out_a)



            out_a = ipy_io(p, fname, "print('func =', name)\n")
            self.assertIn(b"func = f1", out_a)

            out_a = ipy_io(p, fname, "print('x =', x)\n")
            self.assertIn(b"x = 3.5", out_a)

            # test to perform some variable definitions

            ipy_io(p, fname, "y = 23.1\n")
            out_a = ipy_io(p, fname, "print('y =', y)\n")
            self.assertIn(b"y = 23.1", out_a)

            ipy_io(p, fname, "y = -25.1\n")
            out_a = ipy_io(p, fname, "print('y =', y)\n")
            self.assertIn(b"y = -25.1", out_a)

            # move one frame up
            ipy_io(p, fname, "__mu = 1\n")
            out_a = ipy_io(p, fname, "exit()\n")

            out_a = ipy_io(p, fname, "print('func =', name)\n")
            self.assertIn(b"func = f2", out_a)

            out_a = ipy_io(p, fname, "print('x =', x)\n")
            self.assertIn(b"x = 2.5", out_a)

            # move one frame up -> again to f1
            ipy_io(p, fname, "__mu = 1\n")
            out_a = ipy_io(p, fname, "exit()\n")

            out_a = ipy_io(p, fname, "print('func =', name)\n")
            self.assertIn(b"func = f1", out_a)

            ipy_io(p, fname, "z = 789\n")

            # move two frames up
            ipy_io(p, fname, "__mu = 2\n")
            out_a = ipy_io(p, fname, "exit()\n")

            out_a = ipy_io(p, fname, "print('func =', name)\n")
            self.assertIn(b"func = f3", out_a)

            # test of local variable in namespace of f3
            out_a = ipy_io(p, fname, "print('b:', b == [1, 3])\n")
            self.assertIn(b"b: True", out_a)

            # move two frames down -> f1 with x = 2.5
            ipy_io(p, fname, "__mu = -2\n")
            out_a = ipy_io(p, fname, "exit()\n")
            out_a = ipy_io(p, fname, "print('func =', name)\n")
            self.assertIn(b"func = f1", out_a)
            out_a = ipy_io(p, fname, "print('x =', x)\n")
            self.assertIn(b"x = 2.5", out_a)

            # check that this is the namespace which we had already visited above
            out_a = ipy_io(p, fname, "print('z =', z)\n")
            self.assertIn(b"z = 789", out_a)


# noinspection PyPep8Naming,PyUnresolvedReferences,PyUnusedLocal
class TestDBG(unittest.TestCase):

    def test_trace1(self):
        with NamedFileInTemporaryDirectory('file_with_trace.py') as f:
            f.write(_sample_embed_dbg1)
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


        eout = f'{f.name}(18)<module>()\n     16 \n     17 \n---> 18 f1()\n     19 y = 20\n     20 \n\nipdb> '
        self.assertIn(eout, std)



def test_debug():

    from ipydex import Pdb_instance, set_trace, IPS, ultratb
    from IPython import embed as IPS


    IPS()
    exit()



    x = 10

    def f1():
        a = 7
        b = 8

        return a + b

    Pdb_instance.set_colors("NoColor")
    set_trace()


    f1()
    y = 20

    exit()


if __name__ == "__main__":



    # test_debug()

    unittest.main()


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
