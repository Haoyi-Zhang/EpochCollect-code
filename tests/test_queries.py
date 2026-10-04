import random
import unittest
from fractions import Fraction
from queries import setup_budget


class DeadlineQueryTest(unittest.TestCase):
    def test_retained_broadcast_exact_thresholds(self):
        for deadline, expected in [(43,Fraction(1)),(45,Fraction(7,5)),(50,Fraction(3))]:
            got=setup_budget({4:41,6:38},deadline)
            self.assertEqual(got['maximum_setup'],expected)
            self.assertEqual(got['service']+(got['epochs']-1)*expected,deadline)
        self.assertEqual(setup_budget({4:43},45)['maximum_setup'],Fraction(2,3))

    def test_unbounded_zero_and_infeasible(self):
        self.assertTrue(setup_budget({1:3},3)['unbounded'])
        self.assertFalse(setup_budget({1:3},2)['feasible'])
        self.assertFalse(setup_budget({2:4,4:3},2)['feasible'])
        self.assertEqual(setup_budget({2:4},4)['maximum_setup'],0)
        self.assertEqual(setup_budget({3:3},Fraction(7,2))['maximum_setup'],Fraction(1,4))

    def test_direct_finite_frontier_queries(self):
        rng=random.Random(891)
        for _ in range(200):
            f={k:rng.randint(1,30) for k in range(2,rng.randint(3,8))}
            d=rng.randint(0,40)
            got=setup_budget(f,d)
            if not got['feasible']:
                self.assertTrue(all(b>d for b in f.values()))
                continue
            cap=got['maximum_setup']
            self.assertLessEqual(min(b+(k-1)*cap for k,b in f.items()),d)
            self.assertGreater(min(b+(k-1)*(cap+Fraction(1,997)) for k,b in f.items()),d)
            for rho in [Fraction(0),cap/2,cap]:
                self.assertLessEqual(min(b+(k-1)*rho for k,b in f.items()),d)

    def test_bad_query_is_rejected(self):
        for f,d in [({},3),({1:3,2:False},4),({0:2},3),({2:0},3),({2:3},True),({2:3},3.5),({2:3},-1)]:
            with self.assertRaises(ValueError):
                setup_budget(f,d)

    def test_equal_count_family_setup_budget_gap(self):
        for m in range(2,6):
            for length in (1,7,31):
                k=2*m-1; sel=k+length; sat=k+m*length
                for deadline in (sat,sat+10):
                    a=setup_budget({k:sel},deadline)
                    b=setup_budget({k:sat},deadline)
                    self.assertEqual(a['maximum_setup']-b['maximum_setup'],Fraction(length,2))
                self.assertTrue(setup_budget({k:sel},sel)['feasible'])
                self.assertFalse(setup_budget({k:sat},sel)['feasible'])
