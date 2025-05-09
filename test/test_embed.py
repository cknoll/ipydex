"""Test different ways of embedding IPython via ipydex"""


# Created 2019-06-12 12:04:13 by C. Knoll
# This file ist strongly inspired by
# ipython-master/IPython/terminal/tests/test_embed.py (BSD licensed)
#  Copyright (C) 2013 The IPython Development Team


import os
import subprocess
import sys
import unittest
from textwrap import dedent

from IPython.utils.tempdir import NamedFileInTemporaryDirectory
import pexpect
from pexpect.popen_spawn import PopenSpawn

from ipydex import IPS, activate_ips_on_exception
import ipydex.utils


# define some test source code

_exit = b"exit\r"
_mu1 = b"__mu = 1; exit\n"

ipy_prompt = r']:'


_sample_embed_ips1 = b"""
from ipydex import IPS

a = 3
b = 14
print(a, '.', b)

IPS(theme_name="nocolor")

print('bye!')

"""

_sample_embed_ips2 = b'''
import sys

from ipydex import IPS, activate_ips_on_exception
activate_ips_on_exception(theme_name="nocolor")

def f1(x):
    name = "f1"

    print("x=", x)
    if x == 3.5:
        # provoke an exception
        1/0
    elif x > 4:
        # call interactive IPython
        IPS(theme_name="nocolor")
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


# execute IPS inside a method
_sample_embed_ips3 = b'''
from ipydex import IPS

# call IPS without self being present
IPS()

class A:

    def __init__(self):
        IPS()

# call IPS in a method (self is present)
a = A()
'''

_sample_embed_dbg1 = b'''

from ipydex import TracerFactory

x = 10

def f1():
    a = 7
    b = 8

    return a + b

set_trace = TracerFactory(theme_name="nocolor")
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

    assert isinstance(spawn_instance, (PopenSpawn, pexpect.pty_spawn.spawn))

    out = spawn_instance.before + spawn_instance.after
    return perform_replacements(out, fname)


def ipy_io(spawn_instance, fname, command, decode=False):
    """

    :param spawn_instance:
    :param fname:
    :param command:
    :return:
    """

    spawn_instance.send(command)
    spawn_instance.expect(ipy_prompt)
    out_a = get_adapted_out(spawn_instance, fname)

    if decode:
        out_a = out_a.decode("utf8")

    return out_a


# noinspection PyPep8Naming,PyUnresolvedReferences,PyUnusedLocal
class TestE1(unittest.TestCase):

    def setUp(self):
        pass

    def test_encoding(self):
        # if this fails, other tests must be adapted w.r.t. encode/decode
        self.assertEqual(sys.getdefaultencoding(), "utf-8")

    def test_ipython_embed1(self):
        with NamedFileInTemporaryDirectory("file_with_embed.py", "wb") as f:
            f.write(_sample_embed_ips1)
            f.flush()
            f.close()  # otherwise msft won't be able to read the file

            # run `python file_with_embed.py`
            cmd = [sys.executable, f.name]

            std, _, returncode = ipydex.utils.get_out_and_err_of_command(
                cmd, _input=_exit, extra_env={"IPY_TEST_SIMPLE_PROMPT": "1"}, returncode=True,
            )

            self.assertEqual(returncode, 0)
            self.assertIn('3 . 14', std)
            self.assertIn('IPython', std)
            self.assertIn('bye!', std)

    def test_ipython_embed2(self):
        with NamedFileInTemporaryDirectory("file_with_embed.py", "wb") as f:
            f.write(_sample_embed_ips2)
            f.flush()
            f.close()  # otherwise msft won't be able to read the file

            fname = f.name

            # run `python file_with_embed.py`
            cmd1 = [sys.executable, fname, "1.0"]
            std, _ = ipydex.utils.get_out_and_err_of_command(
                cmd1, _input=_exit, extra_env={"IPY_TEST_SIMPLE_PROMPT": "1"}
            )

            # replace python-version specific substring with "__dot_star__"
            expected_output_pattern = 'x= 2.0\nx= 3.0\nx= 4.0\nx= 5.0\nPython 3.__dot_star__\nFile /tmp/tmpdir/filename.py:37\n     34 # arg == 1.5 -> exception\n     35 # arg == 1.0 -> IPS\n---> 37 f3(arg)\n\nFile /tmp/tmpdir/filename.py:31, in f3(x)\n     29 b = [1, 3]\n---> 31 f2(x)\n\nFile /tmp/tmpdir/filename.py:23, in f2(x)\n     22 name = "f2"\n---> 23 f1(x+1)\n\nFile /tmp/tmpdir/filename.py:18, in f1(x)\n     17 else:\n---> 18     f2(x)\n\nFile /tmp/tmpdir/filename.py:23, in f2(x)\n     22 name = "f2"\n---> 23 f1(x+1)\n\nFile /tmp/tmpdir/filename.py:18, in f1(x)\n     17 else:\n---> 18     f2(x)\n\nFile /tmp/tmpdir/filename.py:23, in f2(x)\n     22 name = "f2"\n---> 23 f1(x+1)\n\nFile /tmp/tmpdir/filename.py:18, in f1(x)\n     17 else:\n---> 18     f2(x)\n\nFile /tmp/tmpdir/filename.py:23, in f2(x)\n     22 name = "f2"\n---> 23 f1(x+1)\n\nFile /tmp/tmpdir/filename.py:16, in f1(x)\n     14 elif x > 4:\n     15     # call interactive IPython\n---> 16     IPS(theme_name="nocolor")\n\n--- Interactive IPython Shell. Type `?`<enter> for help. ----\n\n\nIn [1]: \n'

            out_adapted = perform_replacements(std.encode("utf8"), fname).decode("utf8")

            self.assertTrue(ipydex.utils.regex_a_in_b(expected_output_pattern, out_adapted))


            env = os.environ.copy()
            env["IPY_TEST_SIMPLE_PROMPT"] = "1"

            cmd2 = f"{sys.executable} {fname} 1.5"
            p = PopenSpawn(cmd2, env=env)

            p.expect(ipy_prompt)

            # note: this might contain a random tip at the end
            out_a = get_adapted_out(p, fname).decode("utf8")

            # this is good to get an overview over calling history
            # print(out_a.decode())

            # here an ZeroDivision error is intentionally raised and provokes an IPython shell to start
            # we test, whether this shell displays all expected information and behaves as we want

            eout = '''x= 2.5\r\nx= 3.5\r\n\r\n\r\n---------------------------------------------------------------------------\r\nZeroDivisionError                         Traceback (most recent call last)\r\nFile /tmp/tmpdir/filename.py:37\r\n     33 arg = float(sys.argv[1])\r\n     34 # arg == 1.5 -> exception\r\n     35 # arg == 1.0 -> IPS\r\n---> 37 f3(arg)\r\n\r\nFile /tmp/tmpdir/filename.py:31, in f3(x)\r\n     28 a = 1\r\n     29 b = [1, 3]\r\n---> 31 f2(x)\r\n\r\nFile /tmp/tmpdir/filename.py:23, in f2(x)\r\n     21 def f2(x):\r\n     22     name = "f2"\r\n---> 23     f1(x+1)\r\n\r\nFile /tmp/tmpdir/filename.py:18, in f1(x)\r\n     16     IPS(theme_name="nocolor")\r\n     17 else:\r\n---> 18     f2(x)\r\n\r\nFile /tmp/tmpdir/filename.py:23, in f2(x)\r\n     21 def f2(x):\r\n     22     name = "f2"\r\n---> 23     f1(x+1)\r\n\r\nFile /tmp/tmpdir/filename.py:13, in f1(x)\r\n     10 print("x=", x)\r\n     11 if x == 3.5:\r\n     12     # provoke an exception\r\n---> 13     1/0\r\n     14 elif x > 4:\r\n     15     # call interactive IPython\r\n     16     IPS(theme_name="nocolor")\r\n\r\nZeroDivisionError: division by zero\r\n\r\n\r\nPython__dot_star__\r\nType \'copyright\', \'credits\' or \'license\' for more information\r\nIPython __dot_star__ -- An enhanced Interactive Python. Type \'?\' for help.\r\n'''
            eout = eout.replace("\r", "")

            self.assertTrue(ipydex.utils.regex_a_in_b(eout, out_a))

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

    def test_ipython_embed3(self):
        with NamedFileInTemporaryDirectory("file_with_embed.py", "wb") as f:
            f.write(_sample_embed_ips3)
            f.flush()
            f.close()  # otherwise msft won't be able to read the file

            fname = f.name

            env = os.environ.copy()
            env["IPY_TEST_SIMPLE_PROMPT"] = "1"
            env["IPYDEX_UNITTEST_RUNNING"] = "1"
            env["IPYDEX_CLIPBOARD_MOCK"] = dedent("""
            def new_method(self=None):
                print("SUCCESS")
            """)
            cmd2 = f"{sys.executable} {fname}"
            p = PopenSpawn(cmd2, env=env)

            ####################################################################
            # first part: test function mode
            p.expect(ipy_prompt)
            out_a = ipy_io(p, fname, "new_method()\n", decode=True)

            eout = "NameError__dot_star__ name 'new_method' is not defined"
            self.assertTrue(ipydex.utils.regex_a_in_b(eout, out_a))

            src = "%create_method_from_pasted_function\n"
            out_a = ipy_io(p, fname, src, decode=True)

            # ensure that the new function (called "new_method") can be executed
            out_a = ipy_io(p, fname, "new_method()\n", decode=True)
            self.assertTrue(out_a.strip().startswith("SUCCESS"))

            # leave this shell
            out_a = ipy_io(p, fname, "exit()\n\n", decode=True)
            self.assertIn("Interactive IPython Shell. Type `?`<enter> for help.", out_a)

            ####################################################################
            # second part: test oo-mode
            p.expect(ipy_prompt)

            out_a = ipy_io(p, fname, "self.new_method()\n", decode=True)

            # ensure that the method is not present
            eout = "AttributeError__dot_star__'A' object has no attribute 'new_method'"
            self.assertTrue(ipydex.utils.regex_a_in_b(eout, out_a))

            src = "%create_method_from_pasted_function\n"
            out_a = ipy_io(p, fname, src, decode=True)
            self.assertIn("Method 'new_method' added to `self`.", out_a)

            # ensure that the new method can be executed
            out_a = ipy_io(p, fname, "self.new_method()\n", decode=True)
            self.assertTrue(out_a.strip().startswith("SUCCESS"))


# noinspection PyPep8Naming,PyUnresolvedReferences,PyUnusedLocal
class TestDBG(unittest.TestCase):

    def test_trace1(self):
        with NamedFileInTemporaryDirectory("file_with_trace.py", "wb") as f:
            f.write(_sample_embed_dbg1)
            f.flush()
            f.close()  # otherwise msft won't be able to read the file

            # run `python file_with_embed.py`
            cmd = [sys.executable, f.name]

            std, _ = ipydex.utils.get_out_and_err_of_command(
                cmd, _input=_exit, extra_env={"IPY_TEST_SIMPLE_PROMPT": "1"}
            )

        eout = f'{f.name}(17)<module>()\n     15 \n     16 \n---> 17 f1()\n     18 y = 20\n     19'
        self.assertIn(eout, std)


def debug_function():


    IPS()
    exit()



    x = 10

    def f1():
        a = 7
        b = 8

        return a + b

    Pdb_instance.set_colors("nocolor")
    set_trace()


    f1()
    y = 20

    exit()


if __name__ == "__main__":

    # debug_function()

    unittest.main()


# other useful techniques:
"""
    import pexpect
    ipy_prompt = r']:' # ANSI color codes give problems matching beyond this
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
