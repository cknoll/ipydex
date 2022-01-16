import unittest

import ipydex as ipd

# run with e.g. rednose ipydex.test.test_core

zz_global = 5678


# noinspection PyPep8Naming,PyUnresolvedReferences,PyUnusedLocal
class TestCore1(unittest.TestCase):

    def setUp(self):
        pass

    def test_container_aux_functions(self):
        s = "x = Container(cargs=(a, b0, z_test))"
        r = ipd.get_whole_assignment_expression(s, "cargs", tuple)

        self.assertEqual(r, "cargs=(a, b0, z_test)")

        cvars = ipd.get_carg_vars(r)
        self.assertEqual(cvars,  ["a", "b0", "z_test"])

    def test_container1(self):

        C1 = ipd.Container(a=1.25, xaz=[42])

        self.assertEqual(C1.a, 1.25)
        self.assertEqual(C1.xaz, [42])

        z1, z2 = C1._get_attrs("a, xaz")
        self.assertEqual(z1, 1.25)
        self.assertEqual(z2, [42])

        C2 = ipd.Container(fetch_locals=True)

        self.assertEqual(C2.self, self)
        self.assertEqual(C2.z1, z1)
        self.assertEqual(C2.z2, z2)
        self.assertEqual(C2.C1, C1)

        C3 = ipd.Container(X=7, Y="test")

        with self.assertRaises(NameError) as cm:
            # this local variable does not exist
            q = X

        C3.publish_attrs()
        # now this is possible
        q = X

        self.assertEqual(X, 7)
        self.assertEqual(Y, "test")

    def test_container2(self):
        C1 = ipd.Container(a=1.25, xaz=(42,), s="test")

        l = C1.value_list()

        self.assertEqual(set(l), set([1.25, (42,), "test"]))

        x = 123.4
        y2 = (5, 6, 7)

        C2 = ipd.Container(cargs=(x, y2, zz_global), u=0.1, v=0.2)

        self.assertEqual(C2.x, x)
        self.assertEqual(C2.y2, y2)
        self.assertEqual(C2.zz_global, zz_global)
        self.assertEqual(C2.u, 0.1)
        self.assertEqual(C2.v, 0.2)

        C3 = ipd.Container(cargs=[x])
        self.assertEqual(C3.x, x)

        with self.assertRaises(ValueError) as cm:
            ipd.Container(cargs=(x, (y2, zz_global)))

        with self.assertRaises(ValueError) as cm:
            ipd.Container(cargs=(x, "y"))

        with self.assertRaises(NameError) as cm:
            ipd.Container(cargs=(x, y2), x=0.1, v=0.2)

        with self.assertRaises(TypeError) as cm:
            ipd.Container(cargs=set([x, y2]), x=0.1, v=0.2)

        with self.assertRaises(TypeError) as cm:
            ipd.Container(cargs=x)

    def test_container3(self):
        C1 = ipd.Container(a=1.25, xaz=(42,), s="test", d={"a": 1, 2: "b"})

        fname = "container.pcl"
        C1.save_with_pickle(fname)
        C2 = ipd.Container.load_with_pickle(fname)

        C2.publish_attrs()

        self.assertEqual(a, 1.25)
        self.assertEqual(s, "test")
        self.assertEqual(xaz, (42,))
        self.assertEqual(d, {"a": 1, 2: "b"})

    def test_container_equality(self):
        C1 = ipd.Container(arg1=0, arg2="abc", arg3=[10, 2.5, "xyz", tuple()])
        C2 = ipd.Container(arg1=0, arg2="abc", arg3=[10, 2.5, "xyz", tuple()])
        C3 = ipd.Container(arg1=1, arg2="abc", arg3=[10, 2.5, "xyz", tuple()])
        C4 = ipd.Container(arg1=0, arg2="abc", arg3=[2.5, 10, "xyz", tuple()])

        self.assertEqual(C1, C2)
        self.assertNotEqual(C1, C3)
        self.assertNotEqual(C1, C4)

    def test_in_ipynb(self):
        self.assertFalse(ipd.in_ipynb())


class TestCore2(unittest.TestCase):

    def test_calling_stack_info(self):
        def foobar_xyz():
            return foobar_abc()

        def foobar_abc():
            return foobar_123()

        def foobar_123():
            res = ipd.calling_stack_info(print_res=False, code_context=0)

            return res
        res1 = foobar_xyz()
        res2 = foobar_123()

        self.assertTrue("foobar_abc" in res1.tb_txt)
        self.assertTrue("foobar_xyz" in res1.tb_txt)
        self.assertTrue("foobar_123" in res1.tb_txt)

        self.assertFalse("foobar_abc" in res2.tb_txt)
        self.assertFalse("foobar_xyz" in res2.tb_txt)
        self.assertTrue("foobar_123" in res2.tb_txt)


class TestCore3(unittest.TestCase):

    def test_dirsearch(self):
        import math

        res = ipd.dirsearch("log", math)

        expeced_res = ('log', 'log10', 'log1p', 'log2')

        self.assertEqual(res, expeced_res)

        res = ipd.dirsearch("log", math, only_keys=False)
        expeced_res = \
            [('log', '<built-in function..'),
             ('log10', '<built-in function..'),
             ('log1p', '<built-in function..'),
             ('log2', '<built-in function..')]

        self.assertEqual(res, expeced_res)

        res = ipd.dirsearch("log", math, only_keys=False, maxlength=50)
        expeced_res = \
            [('log', '<built-in function log>'),
             ('log10', '<built-in function log10>'),
             ('log1p', '<built-in function log1p>'),
             ('log2', '<built-in function log2>')]

        self.assertEqual(res, expeced_res)


def f1(*args1, **kwargs1):
    """
    This function serves to test manually how ips_after_exception behaves
    :param args1:
    :param kwargs1:
    :return:
    """
    name = "f1"
    ipd.activate_ips_on_exception()
    x = kwargs1.get("x", 0)
    print("x=", x)
    if x > 3:
        ipd.IPS()
        1/0
    else:
        f2(x)


def f2(x):
    name = "f2"
    import time
    t = time.time()
    time.sleep(0.05)
    f1(x=x+1)


def f3():
    name = "f3"
    a = 1
    b = [1, 3]

    f2(5)


if __name__ == "__main__":
    unittest.main()

    # interactively test activate ips_on exception
    # f3()
