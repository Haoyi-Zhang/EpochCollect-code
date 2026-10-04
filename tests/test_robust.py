"""Corner enumeration and counterexamples for static interval robustness."""
import copy
import itertools
import random
import unittest
from checker import checked_input, interpret, matching, check
from epochs import parse, certificate
from horizon import Horizon
from robust import plan_box, replay_box


def legal_batches(raw):
    pairs, _, pred = checked_input(raw)
    n = len(pairs)
    for assignment in itertools.product(range(n),repeat=n):
        k = max(assignment)+1
        if set(assignment) != set(range(k)):
            continue
        if any(assignment[u] > assignment[v] for v in range(n) for u in pred[v]):
            continue
        batches = [[v for v in range(n) if assignment[v] == i] for i in range(k)]
        if all(matching(pairs[v] for v in ids) for ids in batches):
            yield batches


def interpreted_cost(raw, batches, durations, rho):
    pairs, _, pred = checked_input(raw)
    done, value = set(), (len(batches)-1)*rho
    for ids in batches:
        t, _ = interpret(ids,done,pairs,durations,pred)
        value += t
        done.update(ids)
    return value


class RobustTest(unittest.TestCase):
    def test_box_minimax_against_independent_corner_enumeration(self):
        for seed in range(12):
            r = random.Random(6100+seed)
            raw = {'ports':4,'tasks':[{'pair':sorted(r.sample(range(4),2)),
                   'p':1,'pred':[j for j in range(i) if r.random()<.2]} for i in range(4)]}
            high = [r.randint(2,7) for _ in range(4)]
            corners = list(itertools.product(*[(1,x) for x in high]))
            plan = plan_box(raw,high,3)
            worst_values = []
            for batches in legal_batches(raw):
                worst = max(interpreted_cost(raw,batches,list(p),rho)
                            for p in corners for rho in (0,3))
                self.assertEqual(worst,interpreted_cost(raw,batches,high,3))
                worst_values.append(worst)
            self.assertEqual(plan['worst_case_optimum'],min(worst_values))
            for p in corners:
                for rho in (0,3):
                    replay = replay_box(plan,list(p),rho)
                    self.assertLessEqual(replay['makespan'],plan['worst_case_optimum'])

    def test_bounded_overestimate_against_clairvoyant_optimum(self):
        for seed in range(24):
            r = random.Random(6200+seed)
            raw = {'ports':6,'tasks':[{'pair':sorted(r.sample(range(6),2)),
                   'p':r.randint(1,6),'pred':[j for j in range(i) if r.random()<.2]}
                    for i in range(5)]}
            actual = [t['p'] for t in raw['tasks']]
            high = [p*r.randint(1,3) for p in actual]
            plan = plan_box(raw,high,4)
            clairvoyant = Horizon(raw); clairvoyant.solve()
            replay = replay_box(plan,actual,2)
            self.assertLessEqual(replay['makespan'],3*clairvoyant.schedule(2)['makespan'])

    def test_box_guarantee_is_not_taskwise_realization_dominance(self):
        high = {'ports':5,'tasks':[{'pair':[0,1],'p':10,'pred':[]},
                {'pair':[1,4],'p':1,'pred':[0]}, {'pair':[2,3],'p':10,'pred':[]}]}
        _, ht = parse(high)
        original = certificate(ht,[1,6],0)
        normalized = certificate(ht,[5,2],0)
        check(high,original); check(high,normalized)
        self.assertEqual(original['makespan'],20)
        self.assertEqual(normalized['makespan'],11)
        low = copy.deepcopy(high); low['tasks'][0]['p'] = 1
        _, lt = parse(low)
        a,b = certificate(lt,[1,6],0),certificate(lt,[5,2],0)
        old_finish = {e['task']:e['finish'] for ep in a['epochs'] for e in ep['events']}
        new_finish = {e['task']:e['finish'] for ep in b['epochs'] for e in ep['events']}
        self.assertEqual(old_finish[1],2)
        self.assertEqual(new_finish[1],11)

    def test_stored_interval_structure_is_checked_on_replay(self):
        raw = {'ports':2,'tasks':[{'pair':[0,1],'p':2,'pred':[]}]}
        plan = plan_box(raw,[5],2)
        for key,value in [('upper',[]),('upper',[1]),('upper',[True]),
                          ('rho_upper',True),('rho_upper',3),
                          ('worst_case_optimum',True)]:
            bad = copy.deepcopy(plan); bad[key] = value
            with self.assertRaises(ValueError): replay_box(bad,[2],0)

    def test_invalid_or_tampered_boxes_are_rejected(self):
        raw = {'ports':2,'tasks':[{'pair':[0,1],'p':2,'pred':[]}]}
        for upper in ([],[1],[True],[2.5]):
            with self.assertRaises(ValueError): plan_box(raw,upper)
        plan = plan_box(raw,[5],2)
        for ds,rho in (([1],0),([6],0),([3],3),([True],0)):
            with self.assertRaises(ValueError): replay_box(plan,ds,rho)
        plan['worst_case_optimum'] = 0
        with self.assertRaises(ValueError): replay_box(plan,[2],0)

if __name__ == '__main__':
    unittest.main()
