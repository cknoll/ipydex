import unittest

import ipydex as ipd


zz_global = 5678

# noinspection PyPep8Naming,PyUnresolvedReferences,PyUnusedLocal
class InteractiveConvenienceTest(unittest.TestCase):

    def setUp(self):
        pass

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
        C1 = ipd.Container(a=1.25, xaz=[42], s="test")

        l = C1.value_list()

        self.assertEqual(l, [1.25, [42], "test"])

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

    def test_container_aux_functions(self):
        s = "x = Container(cargs=(a, b0, z_test))"
        r = ipd.get_whole_assignment_expression(s, "cargs", tuple)

        self.assertEqual(r, "cargs=(a, b0, z_test)")

        cvars = ipd.get_carg_vars(r)
        self.assertEqual(cvars,  ["a", "b0", "z_test"])


if __name__ == "__main__":
    unittest.main()
