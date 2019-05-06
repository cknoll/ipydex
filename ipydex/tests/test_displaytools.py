import unittest

from ipydex import displaytools as dt
from ipydex import IPS, activate_ips_on_exception
activate_ips_on_exception()


def bool_sum(x):
    if x:
        return 1
    else:
        return 0


# noinspection PyPep8Naming,PyUnresolvedReferences,PyUnusedLocal
class InteractiveConvenienceTest(unittest.TestCase):

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

        ind, lhs, rhs, cmt = dt.get_line_segments(l1)
        self.assertEqual((ind, lhs, rhs, cmt), ("", "x", "0", ""))

        l1 = "# abx"
        ind, lhs, rhs, cmt = dt.get_line_segments(l1)
        self.assertEqual((ind, lhs, rhs, cmt), ("", None, None, "# abx"))

        l1 = "     "
        ind, lhs, rhs, cmt = dt.get_line_segments(l1)
        self.assertEqual((ind, lhs, rhs, cmt), ("", None, None, ""))

        l1 = ""
        ind, lhs, rhs, cmt = dt.get_line_segments(l1)
        self.assertEqual((ind, lhs, rhs, cmt), ("", None, None, ""))

        l1 = "x + y  ##"
        ind, lhs, rhs, cmt = dt.get_line_segments(l1)
        self.assertEqual((ind, lhs, rhs, cmt), ("", None, "x + y", "##"))

        l1 = "x + y + 'z=#'  ##:"
        ind, lhs, rhs, cmt = dt.get_line_segments(l1)
        self.assertEqual((ind, lhs, rhs, cmt), ("", None, "x + y + 'z=#'", "##:"))

        l1 = "A =     '#xyz=7'  # abcd ##: efg    "
        ind, lhs, rhs, cmt = dt.get_line_segments(l1)
        self.assertEqual((ind, lhs, rhs, cmt), ("", "A", "'#xyz=7'", "# abcd ##: efg"))

        l1 = "    A = X  # Z"
        ind, lhs, rhs, cmt = dt.get_line_segments(l1)
        self.assertEqual((ind, lhs, rhs, cmt), ("    ", "A", "X", "# Z"))

        l1 = "    y, x, z = A = X  # Z"
        ind, lhs, rhs, cmt = dt.get_line_segments(l1)
        self.assertEqual((ind, lhs, rhs, cmt), ("    ", "A", "X", "# Z"))
        l1 = "    A = y, x, z = X  # Z"
        ind, lhs, rhs, cmt = dt.get_line_segments(l1)
        self.assertEqual((ind, lhs, rhs, cmt), ("    ", "y, x, z", "X", "# Z"))

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
z = 0
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
        # --------------------
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


if __name__ == "__main__":
    unittest.main()
