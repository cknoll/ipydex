import unittest

import sys
from contextlib import contextmanager
from io import StringIO

from ipydex import displaytools as dt
from ipydex import IPS


def bool_sum(x):
    if x:
        return 1
    else:
        return 0


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


# noinspection PyPep8Naming,PyUnresolvedReferences,PyUnusedLocal
class TestDT1(unittest.TestCase):

    def setUp(self):
        pass

    def test_classify_comment(self):

        c1 = ""
        r1 = dt.classify_comment(c1)
        self.assertTrue(r1.empty_comment)
        # all other flags should be false
        self.assertEqual(bool_sum(r1.value_list()), 1)

        c1 = "# nothing special here"
        r1 = dt.classify_comment(c1)
        # all flags should be false
        self.assertFalse(any(r1.value_list()))

        c1 = "# comments ##: more comments"
        r1 = dt.classify_comment(c1)
        self.assertTrue(r1.lhs)
        self.assertTrue(r1.sc)
        self.assertFalse(r1.transpose)

        c1 = "# comments ##:T more comments"
        r1 = dt.classify_comment(c1)
        self.assertTrue(r1.lhs)
        self.assertTrue(r1.sc)
        self.assertTrue(r1.transpose)
        self.assertFalse(r1.shape)

        c1 = "# comments ##:S more comments"
        r1 = dt.classify_comment(c1)
        # all flags should be false
        self.assertTrue(r1.sc)
        self.assertTrue(r1.shape)
        self.assertFalse(r1.transpose)

    def _test_classify_line_by_comment(self):

        l1 = "x = 0 # nothing special here"
        r1 = dt.classify_line_by_comment(l1)
        # all flags should be false
        self.assertFalse(any(r1.value_list()))

        l1 = "# nothing special here"
        r1 = dt.classify_line_by_comment(l1)
        self.assertTrue(r1.comment_only)

        l1 = "x = '# '"
        r1 = dt.classify_line_by_comment(l1)
        # all flags should be false
        self.assertFalse(any(r1.value_list()))

        l1 = "x = '##:'"
        r1 = dt.classify_line_by_comment(l1)
        # all flags should be false
        self.assertFalse(any(r1.value_list()))

        l1 = "x = '##:T' ##:"
        r1 = dt.classify_line_by_comment(l1)
        # all flags should be false
        self.assertTrue(r1.sc)
        self.assertTrue(r1.lhs)
        self.assertFalse(r1.transpose)

        l1 = "x = a*b # xyz ##:S"
        r1 = dt.classify_line_by_comment(l1)
        # all flags should be false
        self.assertTrue(r1.sc)
        self.assertTrue(r1.lhs)
        self.assertTrue(r1.shape)
        self.assertFalse(r1.transpose)

    def test_get_line_segments(self):

        l1 = "x = 0"

        def f(txt):
            return dt.get_logical_lines_of_cell(txt)[0]

        ind, lhs, rhs, cmt = dt.get_line_segments_from_logical_line(f(l1))
        self.assertEqual((ind, lhs, rhs, cmt), ("", "x", "0", ""))

        l1 = "# abx"
        ind, lhs, rhs, cmt = dt.get_line_segments_from_logical_line(f(l1))
        self.assertEqual((ind, lhs, rhs, cmt), ("", None, None, "# abx"))

        l1 = "     "
        ind, lhs, rhs, cmt = dt.get_line_segments_from_logical_line(f(l1))
        self.assertEqual((ind, lhs, rhs, cmt), ("", None, None, ""))

        l1 = ""
        ind, lhs, rhs, cmt = dt.get_line_segments_from_logical_line(f(l1))
        self.assertEqual((ind, lhs, rhs, cmt), ("", None, None, ""))

        l1 = "x + y  ##"
        ind, lhs, rhs, cmt = dt.get_line_segments_from_logical_line(f(l1))
        self.assertEqual((ind, lhs, rhs, cmt), ("", None, "x + y", "##"))

        l1 = "x + y + 'z=#'  ##:"
        ind, lhs, rhs, cmt = dt.get_line_segments_from_logical_line(f(l1))
        self.assertEqual((ind, lhs, rhs, cmt), ("", None, "x + y + 'z=#'", "##:"))

        l1 = "A =     '#xyz=7'  # abcd ##: efg    "
        ind, lhs, rhs, cmt = dt.get_line_segments_from_logical_line(f(l1))
        self.assertEqual((ind, lhs, rhs, cmt), ("", "A", "'#xyz=7'", "# abcd ##: efg"))

        l1 = "    A = X  # Z"
        ind, lhs, rhs, cmt = dt.get_line_segments_from_logical_line(f(l1))
        self.assertEqual((ind, lhs, rhs, cmt), ("    ", "A", "X", "# Z"))

        l1 = "    y, x, z = A = X  # Z"
        ind, lhs, rhs, cmt = dt.get_line_segments_from_logical_line(f(l1))
        self.assertEqual((ind, lhs, rhs, cmt), ("    ", "A", "X", "# Z"))

        l1 = "    A = y, x, z = X  # Z"
        ind, lhs, rhs, cmt = dt.get_line_segments_from_logical_line(f(l1))
        self.assertEqual((ind, lhs, rhs, cmt), ("    ", "y, x, z", "X", "# Z"))

        l1 = "x = func1(a=a, b = b) ##:"
        ind, lhs, rhs, cmt = sgm = dt.get_line_segments_from_logical_line(f(l1))
        self.assertEqual((ind, lhs, rhs, cmt), ("", "x", "func1(a=a, b = b)", "##:"))

        l1 = "xyz=x ##:i"
        ind, lhs, rhs, cmt = sgm = dt.get_line_segments_from_logical_line(f(l1))
        self.assertEqual((ind, lhs, rhs, cmt), ("", "xyz", "x", "##:i"))

    def test_insert_disp_lines1(self):
        raw_cell1 = """\
x = 0
y = 1 ##:
z = 0
"""

        eres1 = """\
x = 0
y = 1 ##:
custom_display("y", y); print("---")
z = 0
"""

        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(eres1, res1)

        # --------------------

        raw_cell1 = """\
x = 0
y = 1 # more comments ##: more comments
z = 0
"""

        eres1 = """\
x = 0
y = 1 # more comments ##: more comments
custom_display("y", y); print("---")
z = 0
"""

        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(eres1, res1)

        # --------------------

        raw_cell1 = """\
x = 0
# y = 1 ##:
ZZ = 0
"""

        eres1 = raw_cell1

        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(eres1, res1)

        # --------------------

        raw_cell1 = """\
x = 0
if 1:
    y = 1 ##:
z = 0
"""

        eres1 = """\
x = 0
if 1:
    y = 1 ##:
    custom_display("y", y); print("---")
z = 0
"""

        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(eres1, res1)

        # --------------------

        raw_cell1 = """\
x = 0
if 1:
    y ##:
C.xyz ##:
"""

        eres1 = """\
x = 0
if 1:
    custom_display("(y)", (y)); print("---")
custom_display("(C.xyz)", (C.xyz)); print("---")
"""

        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(eres1, res1)
        # --------------------

        raw_cell1 = """\
x = 0
if 1:
    y1, y2 = 1, 2 ##:

    y1, y2 = yy = 1, 2 ##:

    yy = y1, y2 = 1, 2 ##:

    y1, y2 = yy = 1, 2 ##:T
z = 0
"""

        eres1 = """\
x = 0
if 1:
    y1, y2 = 1, 2 ##:
    custom_display("(y1, y2)", (y1, y2)); print("---")

    y1, y2 = yy = 1, 2 ##:
    custom_display("yy", yy); print("---")

    yy = y1, y2 = 1, 2 ##:
    custom_display("(y1, y2)", (y1, y2)); print("---")

    y1, y2 = yy = 1, 2 ##:T
    custom_display("yy.T", yy.T); print("---")
z = 0
"""

        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(eres1, res1)

        # --------------------

        raw_cell1 = """\
def func(a, b):
    '''
    some docstring
    '''
    pass
"""

        eres1 = raw_cell1

        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(eres1, res1)

        # --------------------

        raw_cell1 = """\
x = func1(a=a, b = b) ##:
if 1:
    y = func2(a=a, b = b) ##:T
"""

        eres1 = """\
x = func1(a=a, b = b) ##:
custom_display("x", x); print("---")
if 1:
    y = func2(a=a, b = b) ##:T
    custom_display("y.T", y.T); print("---")
"""

        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(eres1, res1)

        # --------------------
        # --------------------
        # --------------------

    def test_insert_disp_lines2(self):
        raw_cell1 = """\
y = x ##:S
z = 0
"""

        eres1 = """\
y = x ##:S
custom_display("y.shape", y.shape); print("---")
z = 0
"""

        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(eres1, res1)

        # --------------------

        raw_cell1 = """\
y = x ##:i
z = 0
"""

        eres1 = """\
y = x ##:i
custom_display("info(y)", _ipydex__info(y)); print("---")
z = 0
"""

        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(eres1, res1)
        # --------------------
        # --------------------

    def test_insert_disp_lines3(self):
        raw_cell1 = """\
y=x ##:
y=x ##:i
z = 0
"""
        eres1 = """\
y=x ##:
custom_display("y", y); print("---")
y=x ##:i
custom_display("info(y)", _ipydex__info(y)); print("---")
z = 0
"""
        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(eres1, res1)

    def test_logical_lines1(self):
        raw_cell1 = """\
x = 0
# y = 1 ##:
ZZ = 0
"""
        ll_list = dt.get_logical_lines_of_cell(raw_cell1)
        self.assertEqual(len(ll_list), 3)

        # test whether the last logical line only consists of ENDMARKER and friends
        ignorable_tokens = [dt.tk.ENDMARKER, dt.tk.NL]
        self.assertTrue(all(elt.type in ignorable_tokens for elt in ll_list[-1].tokens))

    def test_logical_lines2(self):

        raw_cell1 = """\
z1 = [ 1,
       2,
       3 ]



z2 = [ 1,
       2,
       3 ]  ##:

z3 = [ 1,  # some comment
       2,  ##:
       3 ] # more comments

# note the spaces in the  "empty" line below
       
z4 = [ 1,  
       2,  
       3 ] ##:
"""

        aa = dt.ast.parse(raw_cell1)
        ll = dt.get_logical_lines_of_cell(raw_cell1)

        self.assertEqual(ll[0].txt, 'z1 = [ 1,\n       2,\n       3 ]\n')
        self.assertEqual(ll[1].txt, '\n\n\nz2 = [ 1,\n       2,\n       3 ]  ##:\n')
        self.assertEqual(ll[2].txt, '\nz3 = [ 1,  # some comment\n       2,  ##:\n       3 ] # more comments\n')

        eres = '\n# note the spaces in the  "empty" line below\n       \nz4 = [ 1,  \n       2,  \n       3 ] ##:\n'
        self.assertEqual(ll[3].txt, eres)

        indent, lhs, rhs, comments = dt.get_line_segments_from_logical_line(ll[2])
        self.assertEqual(indent, "")
        self.assertEqual(lhs, "z3")
        self.assertEqual(rhs, "[ 1,\n       2,\n       3 ]")

    def test_info1(self):
        res1 = dt.info(1)
        eres1 = "<class 'int'> with value: 1"
        self.assertEqual(res1, eres1)
        # --------------------

        res1 = dt.info(1.0)
        eres1 = "<class 'float'> with value: 1.0"
        self.assertEqual(res1, eres1)
        # --------------------

        res1 = dt.info([])
        eres1 = "<class 'list'> with length: 0"
        self.assertEqual(res1, eres1)
        # --------------------

        res1 = dt.info({1: 2})
        eres1 = "<class 'dict'> with length: 1"
        self.assertEqual(res1, eres1)
        # --------------------

        try:
            # noinspection PyPackageRequirements
            import numpy as np
        except ImportError:
            return

        res1 = dt.info(np.zeros((12, 15)))
        eres1 = "<class 'numpy.ndarray'> with shape: (12, 15)"
        self.assertEqual(res1, eres1)
        # --------------------

    def test_is_single_name(self):
        self.assertTrue(dt.is_single_name("a"))
        self.assertTrue(dt.is_single_name("abc_xyz "))

        self.assertFalse(dt.is_single_name("abc,xyz "))
        self.assertFalse(dt.is_single_name("abc, xyz, qwe"))
        self.assertFalse(dt.is_single_name("abc + xyz"))
        self.assertFalse(dt.is_single_name("abc - xyz"))
        self.assertFalse(dt.is_single_name("abc*xyz-1"))
        self.assertFalse(dt.is_single_name("abc/xyz-1"))
        self.assertFalse(dt.is_single_name("abc%xyz-1"))
        self.assertFalse(dt.is_single_name("abc^xyz-1"))

    def test_custom_display(self):
        # ensure that no error occurs

        with captured_output() as (out, err):
            r1 = dt.custom_display("a", 3.1)

        self.assertEqual(r1, None)
        o1 = out.getvalue().strip()
        self.assertEqual(o1, 'a := 3.1')

        try:
            # noinspection PyPackageRequirements
            import numpy as np
            with captured_output() as (out, err):
                r1 = dt.custom_display("a", np.array([1, 3.0, 500]))
                o1 = out.getvalue().strip()

            # number of spaces depends on python version...
            o1_expected = 'a := array([  1.,   3., 500.])'.replace(" ", "")
            self.assertEqual(o1.replace(" ", ""), o1_expected)
        except ImportError:
            pass


# noinspection PyPep8Naming,PyUnresolvedReferences,PyUnusedLocal
class TestDT2(unittest.TestCase):

    def setUp(self):
        pass

    def test_demo5(self):
        raw_cell1 = """\
# numpy arrays and matrices are indented to take left-hand-side into account


np.random.seed(0)

A = np.random.random((5, 4)) ##:
np.matrix(A) ##:

# heuristic to insert a newline if indentation would be too long
A_with_long_name = A ##:

"""

        eres1 = """\
# numpy arrays and matrices are indented to take left-hand-side into account


np.random.seed(0)

A = np.random.random((5, 4)) ##:
custom_display("A", A); print("---")
custom_display("(np.matrix(A))", (np.matrix(A))); print("---")

# heuristic to insert a newline if indentation would be too long
A_with_long_name = A ##:
custom_display("A_with_long_name", A_with_long_name); print("---")

"""

        ll = dt.get_logical_lines_of_cell(raw_cell1)
        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(res1, eres1)

    def test_demo4(self):
        raw_cell1 = """\
if:
    # van-der-Pol-Oszillator
    f = sp.Matrix([x2, (1-x1**2)*x2 - x1])
    y = h = x1

    
selector ##:
n = len(f)
f ##:
y ##:
"""

        eres1 = """\
if:
    # van-der-Pol-Oszillator
    f = sp.Matrix([x2, (1-x1**2)*x2 - x1])
    y = h = x1
custom_display("(selector)", (selector)); print("---")
n = len(f)
custom_display("(f)", (f)); print("---")
custom_display("(y)", (y)); print("---")
"""
        ll = dt.get_logical_lines_of_cell(raw_cell1)
        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(res1, eres1)

    def testLL3(self):
        raw_cell1 = """\
xx = sp.Matrix(sp.symbols('x1:11'))
yy = sp.Matrix(sp.symbols('y1:11'))

xx.shape, yy.shape ##:
"""
        eres1 = """\
xx = sp.Matrix(sp.symbols('x1:11'))
yy = sp.Matrix(sp.symbols('y1:11'))
custom_display("(xx.shape, yy.shape)", (xx.shape, yy.shape)); print("---")
"""

        ll = dt.get_logical_lines_of_cell(raw_cell1)
        res1 = dt.insert_disp_lines(raw_cell1)
        self.assertEqual(res1, eres1)

    def testLL1(self):
        raw_cell1 = """\
x = 0
if 1:
    y ##:
C.xyz ##:
"""

        ll = dt.get_logical_lines_of_cell(raw_cell1)

        if 1:
            res = [dt.get_line_segments_from_logical_line(elt) for elt in ll]

            self.assertEqual(res[0], ("",     "x", "0", ""))
            self.assertEqual(res[2], ("    ", None, "y", "##:"))
            self.assertEqual(res[3], ("",     None, "C.xyz", "##:"))

    def testLL2(self):

        raw_cell1 = """\
x = 0
if 1:
    # a = 0 
    # b = 1 ##:
    WW = 10
    XX = 0 # abc1
    if 1: 
        YY = 1
Z1 = 1
Z2 = 2# abc 
"""

        ll = dt.get_logical_lines_of_cell(raw_cell1)

        res = [dt.get_line_segments_from_logical_line(elt) for elt in ll]

        self.assertEqual(res[0], ("", "x", "0", ""))
        self.assertEqual(res[2], ("    ", "WW", "10", ""))
        self.assertEqual(res[3], ("    ", "XX", "0", "# abc1"))


if __name__ == "__main__":
    unittest.main()
