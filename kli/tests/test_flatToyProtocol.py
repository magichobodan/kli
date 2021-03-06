from unittest import TestCase
import unittest
import kli.toy
import kli.parameter

__author__ = 'sean'


class TestFlatToyProtocol(TestCase):
    def setUp(self):
        self.q0 = kli.parameter.Parameter("q0", 0.5, "kHz", log=True)
        self.q1 = kli.parameter.Parameter("q1", 0.25, "kHz", log=True)
        self.q = kli.parameter.Parameter("q", 1. / 6., "kHz", log=True)
        self.T3 = kli.toy.Toy([self.q0, self.q1])
        self.T2 = kli.toy.Toy([self.q])
        self.F2 = self.T2.flatten(2)
        self.F3 = self.T3.flatten(3)
        self.F2.sim(10)
        self.F3.sim(10)

    def test_Toy2_like(self):
        self.assertEqual(self.F2.like(), -22.693346462595336)  # -30.619490619218585)

    def test_Toy3_like(self):
        self.assertEqual(self.F3.like(), -24.595563663018137)  # -27.500748311455272)

    def test_Toy_KL(self):
        self.assertEqual(self.F3.KL(self.F2), 0.012275727108696066)

if __name__ == '__main__':
    unittest.main()