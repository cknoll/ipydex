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


# define some test source code

_exit = b"exit\r"
_mu1 = b"__mu = 1; exit\n"

ipy_prompt = r']:'


_sample_embed_ips1 = b"""
from ipydex import IPS

a = 3
b = 14
print(a, '.', b)

IPS()

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
        IPS()
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

from ipydex import TracerFactory

x = 10

def f1():
    a = 7
    b = 8

    return a + b

ST = TracerFactory("NoColor")
ST()


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
            eout1 = b"\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36m<module>\x1b[1;34m\x1b[0m\n\x1b[1;32m---> 37\x1b[1;33m \x1b[0mf3\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0marg\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0m\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf3\x1b[1;34m(x)\x1b[0m\n\x1b[1;32m---> 31\x1b[1;33m     \x1b[0mf2\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0m\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf2\x1b[1;34m(x)\x1b[0m\n\x1b[1;32m---> 23\x1b[1;33m     \x1b[0mf1\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m+\x1b[0m\x1b[1;36m1\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0m\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf1\x1b[1;34m(x)\x1b[0m\n\x1b[1;32m---> 18\x1b[1;33m         \x1b[0mf2\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0m\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf2\x1b[1;34m(x)\x1b[0m\n\x1b[1;32m---> 23\x1b[1;33m     \x1b[0mf1\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m+\x1b[0m\x1b[1;36m1\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0m\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf1\x1b[1;34m(x)\x1b[0m\n\x1b[1;32m---> 18\x1b[1;33m         \x1b[0mf2\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0m\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf2\x1b[1;34m(x)\x1b[0m\n\x1b[1;32m---> 23\x1b[1;33m     \x1b[0mf1\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m+\x1b[0m\x1b[1;36m1\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0m\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf1\x1b[1;34m(x)\x1b[0m\n\x1b[1;32m---> 18\x1b[1;33m         \x1b[0mf2\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0m\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf2\x1b[1;34m(x)\x1b[0m\n\x1b[1;32m---> 23\x1b[1;33m     \x1b[0mf1\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m+\x1b[0m\x1b[1;36m1\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0m\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf1\x1b[1;34m(x)\x1b[0m\n\x1b[0;32m     13\x1b[0m         \x1b[1;36m1\x1b[0m\x1b[1;33m/\x1b[0m\x1b[1;36m0\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0;32m     14\x1b[0m     \x1b[1;32melif\x1b[0m \x1b[0mx\x1b[0m \x1b[1;33m>\x1b[0m \x1b[1;36m4\x1b[0m\x1b[1;33m:\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0;32m     15\x1b[0m         \x1b[1;31m# call interactive IPython\x1b[0m\x1b[1;33m\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[1;32m---> 16\x1b[1;33m         \x1b[0mIPS\x1b[0m\x1b[1;33m(\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0m\x1b[0;32m     17\x1b[0m     \x1b[1;32melse\x1b[0m\x1b[1;33m:\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0;32m     18\x1b[0m         \x1b[0mf2\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\n\x1b[0;32m     19\x1b[0m \x1b[1;33m\x1b[0m\x1b[0m"

            out, err = p.communicate(_exit)

            out_adapted = perform_replacements(out, fname)

            # hotfix for some compatibility problem !!
            self.assertIn(eout1[:140], out_adapted)

            cmd2 = [sys.executable, fname, "1.5"]

            p = pexpect.spawn(sys.executable, [fname, "1.5"], env=env)

            p.expect(ipy_prompt)
            out_a = get_adapted_out(p, fname)

            # this is good to get an overview over calling history
            # print(out_a.decode())

            # here an ZeroDivision error is intentionally raised and provokes an IPython shell to start
            # we test, whether this shell displays all expected informations and behaves as we want

            eout = b'x= 2.5\r\nx= 3.5\r\n\r\n\r\n\x1b[1;31m---------------------------------------------------------------------------\x1b[0m\r\n\x1b[1;31mZeroDivisionError\x1b[0m                         Traceback (most recent call last)\r\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36m<module>\x1b[1;34m\x1b[0m\r\n\x1b[0;32m     35\x1b[0m \x1b[1;31m# arg == 1.0 -> IPS\x1b[0m\x1b[1;33m\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0;32m     36\x1b[0m \x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[1;32m---> 37\x1b[1;33m \x1b[0mf3\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0marg\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0m\x1b[0;32m     38\x1b[0m \x1b[1;33m\x1b[0m\x1b[0m\r\n\r\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf3\x1b[1;34m(x)\x1b[0m\r\n\x1b[0;32m     29\x1b[0m     \x1b[0mb\x1b[0m \x1b[1;33m=\x1b[0m \x1b[1;33m[\x1b[0m\x1b[1;36m1\x1b[0m\x1b[1;33m,\x1b[0m \x1b[1;36m3\x1b[0m\x1b[1;33m]\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0;32m     30\x1b[0m \x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[1;32m---> 31\x1b[1;33m     \x1b[0mf2\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0m\x1b[0;32m     32\x1b[0m \x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0;32m     33\x1b[0m \x1b[0marg\x1b[0m \x1b[1;33m=\x1b[0m \x1b[0mfloat\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0msys\x1b[0m\x1b[1;33m.\x1b[0m\x1b[0margv\x1b[0m\x1b[1;33m[\x1b[0m\x1b[1;36m1\x1b[0m\x1b[1;33m]\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\r\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf2\x1b[1;34m(x)\x1b[0m\r\n\x1b[0;32m     21\x1b[0m \x1b[1;32mdef\x1b[0m \x1b[0mf2\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m:\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0;32m     22\x1b[0m     \x1b[0mname\x1b[0m \x1b[1;33m=\x1b[0m \x1b[1;34m"f2"\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[1;32m---> 23\x1b[1;33m     \x1b[0mf1\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m+\x1b[0m\x1b[1;36m1\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0m\x1b[0;32m     24\x1b[0m \x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0;32m     25\x1b[0m \x1b[1;33m\x1b[0m\x1b[0m\r\n\r\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf1\x1b[1;34m(x)\x1b[0m\r\n\x1b[0;32m     16\x1b[0m         \x1b[0mIPS\x1b[0m\x1b[1;33m(\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0;32m     17\x1b[0m     \x1b[1;32melse\x1b[0m\x1b[1;33m:\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[1;32m---> 18\x1b[1;33m         \x1b[0mf2\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0m\x1b[0;32m     19\x1b[0m \x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0;32m     20\x1b[0m \x1b[1;33m\x1b[0m\x1b[0m\r\n\r\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf2\x1b[1;34m(x)\x1b[0m\r\n\x1b[0;32m     21\x1b[0m \x1b[1;32mdef\x1b[0m \x1b[0mf2\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m:\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0;32m     22\x1b[0m     \x1b[0mname\x1b[0m \x1b[1;33m=\x1b[0m \x1b[1;34m"f2"\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[1;32m---> 23\x1b[1;33m     \x1b[0mf1\x1b[0m\x1b[1;33m(\x1b[0m\x1b[0mx\x1b[0m\x1b[1;33m+\x1b[0m\x1b[1;36m1\x1b[0m\x1b[1;33m)\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0m\x1b[0;32m     24\x1b[0m \x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0;32m     25\x1b[0m \x1b[1;33m\x1b[0m\x1b[0m\r\n\r\n\x1b[1;32m/tmp/tmpdir/filename.py\x1b[0m in \x1b[0;36mf1\x1b[1;34m(x)\x1b[0m\r\n\x1b[0;32m     11\x1b[0m     \x1b[1;32mif\x1b[0m \x1b[0mx\x1b[0m \x1b[1;33m==\x1b[0m \x1b[1;36m3.5\x1b[0m\x1b[1;33m:\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0;32m     12\x1b[0m         \x1b[1;31m# provoke an exception\x1b[0m\x1b[1;33m\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[1;32m---> 13\x1b[1;33m         \x1b[1;36m1\x1b[0m\x1b[1;33m/\x1b[0m\x1b[1;36m0\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0m\x1b[0;32m     14\x1b[0m     \x1b[1;32melif\x1b[0m \x1b[0mx\x1b[0m \x1b[1;33m>\x1b[0m \x1b[1;36m4\x1b[0m\x1b[1;33m:\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\x1b[0;32m     15\x1b[0m         \x1b[1;31m# call interactive IPython\x1b[0m\x1b[1;33m\x1b[0m\x1b[1;33m\x1b[0m\x1b[0m\r\n\r\n\x1b[1;31mZeroDivisionError\x1b[0m: division by zero\r\n'

            # hotfix for some compatibility problem !!
            self.assertIn(eout[:330], out_a)

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

    def test_trac1(self):
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


        eout = f'\x1b[22;0t\x1b]0;IPython: repo/test\x07> {f.name}(17)<module>()\n     15 \n     16 \n---> 17 f1()\n     18 y = 20\n     19 \n\nipdb> Exiting Debugger.\n'

        self.assertEqual(std, eout)



def test_debug():
    from ipydex import TracerFactory

    x = 10

    def f1():
        a = 7
        b = 8

        return a + b

    ST = TracerFactory()
    ST()


    f1()
    y = 20
    exit()


if __name__ == "__main__":

    unittest.main()
    # write_string_to_file_script(_sample_embed_ips2)


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
