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

    def test_classify_line_by_comment(self):

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

        lhs, rhs, cmt = dt.get_line_segments(l1)

        self.assertEqual(lhs, "x")
        self.assertEqual(rhs, "0")
        self.assertEqual(cmt, "")

        l1 = "# abx"

        lhs, rhs, cmt = dt.get_line_segments(l1)

        self.assertEqual(lhs, None)
        self.assertEqual(rhs, None)
        self.assertEqual(cmt, "# abx")

        l1 = "     "
        lhs, rhs, cmt = dt.get_line_segments(l1)
        self.assertEqual((lhs, rhs, cmt), (None, None, ""))

        l1 = ""
        lhs, rhs, cmt = dt.get_line_segments(l1)
        self.assertEqual((lhs, rhs, cmt), (None, None, ""))

        l1 = "x + y  ##"

        lhs, rhs, cmt = dt.get_line_segments(l1)

        self.assertEqual(lhs, None)
        self.assertEqual(rhs, "x + y")
        self.assertEqual(cmt, "##")

        l1 = "x + y 'z=#'  ##:"

        lhs, rhs, cmt = dt.get_line_segments(l1)

        self.assertEqual(lhs, None)
        self.assertEqual(rhs, "x + y 'z=#'")
        self.assertEqual(cmt, "##:")

        l1 = "A =     '#xyz=7'  # abcd ##: efg    "
        lhs, rhs, cmt = dt.get_line_segments(l1)
        self.assertEqual(lhs, "A")
        self.assertEqual(rhs, "'#xyz=7'")
        self.assertEqual(cmt, "# abcd ##: efg")

    def _test_insert_disp_lines1(self):
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
        IPS()

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

        IPS()


if __name__ == "__main__":
    unittest.main()