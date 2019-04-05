import unittest

import ipydex as ipd


# noinspection PyPep8Naming,PyUnresolvedReferences,PyUnusedLocal
class InteractiveConvenienceTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_container(self):

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
