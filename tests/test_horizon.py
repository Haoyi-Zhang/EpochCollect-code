"""Adversarial finite checks of the horizon normal form (not a proof assistant)."""
import copy
import itertools
import random
import unittest
from fractions import Fraction
from unittest.mock import patch

from epochs import Exact, parse, bits, certificate
from checker import check, check_collective
from oracle import spectra as oracle_spectra
from generators import fork, tree_case
from prefix import Prefix
from horizon import Horizon, Limits, SearchLimit, maximal_matchings, pareto, normalize, envelope


def random_case(seed, n=6):
    r = random.Random(seed)
    return {'ports': 6, 'tasks': [dict(pair=sorted(r.sample(range(6), 2)),
            p=r.randint(1, 11), pred=[j for j in range(i) if r.random() < .25]) for i in range(n)]}


def independent_matchings(pairs):
    pairs = list(sorted(set(pairs)))
    good = []
    for mask in range(1, 1 << len(pairs)):
        q = [pairs[i] for i in range(len(pairs)) if mask >> i & 1]
        flat = sum((list(x) for x in q), [])
        if len(flat) == len(set(flat)):
            good.append(frozenset(q))
    return set(m for m in good if not any(m < s for s in good))


class HorizonTest(unittest.TestCase):
    def test_equal_makespan_labels_do_not_encode_regular_objectives(self):
        raw = {'ports':3,'tasks':[{'pair':[0,1],'p':1,'pred':[]},
                                  {'pair':[0,2],'p':10,'pred':[]}]}
        _, tasks = parse(raw)
        first = certificate(tasks,[1,2],0)
        second = certificate(tasks,[2,1],0)
        check(raw,first); check(raw,second)
        self.assertEqual(first['makespan'],second['makespan'])
        sums = [sum(e['finish'] for ep in c['epochs'] for e in ep['events'])
                for c in (first,second)]
        self.assertEqual(sums,[12,21])
        self.assertEqual(Horizon(raw).solve(),{2:11})

    def test_topology_dependent_setup_breaks_maximal_matching_dominance(self):
        raw = {'ports':4,'tasks':[{'pair':[0,1],'p':1,'pred':[]},
                   {'pair':[1,2],'p':1,'pred':[0]}, {'pair':[2,3],'p':1,'pred':[]}]}
        _, tasks = parse(raw)
        singleton = certificate(tasks,[1,2,4],0)
        check(raw,singleton)
        self.assertEqual(singleton['makespan'],3)
        matchings = set(maximal_matchings([t.pair for t in tasks]))
        self.assertEqual(matchings,{frozenset({(0,1),(2,3)}),frozenset({(1,2)})})
        # Charge 100 only between these two maximal installed topologies.
        # The singleton path uses no such transition. Every maximal-only plan
        # needs both topologies (and at least two service units).
        self.assertEqual(Horizon(raw).solve(),{2:2})
        maximal_minimum = 2 + 100
        self.assertGreater(maximal_minimum,singleton['makespan'])

    def test_matchings_all_graphs_on_four_endpoints(self):
        edges = list(itertools.combinations(range(4), 2))
        for mask in range(1, 1 << len(edges)):
            pairs = [q for i, q in enumerate(edges) if mask >> i & 1]
            self.assertEqual(set(maximal_matchings(pairs)), independent_matchings(pairs))

    def test_random_graph_matchings(self):
        for seed in range(100):
            r = random.Random(seed)
            pairs = r.sample(list(itertools.combinations(range(6), 2)), r.randint(1, 10))
            self.assertEqual(set(maximal_matchings(pairs)), independent_matchings(pairs))

    def test_full_spectra_reference_random(self):
        for seed in range(80):
            raw = random_case(seed, 5 + seed % 2)
            old = Exact(raw)
            spec = old.solve()['selective']
            h = Horizon(raw)
            self.assertEqual(h.solve(), pareto(spec))
            for rho in (0, 1, 5, 17):
                packet = h.schedule(rho)
                check(raw, packet)
                self.assertEqual(packet['makespan'], old.schedule(rho)['makespan'])
                normalized = normalize(raw, old.schedule(rho))
                self.assertLessEqual(normalized['makespan'], packet['makespan'])

    def test_maximal_against_all_matchings(self):
        for seed in range(30):
            raw = random_case(seed)
            a, b = Horizon(raw), Horizon(raw, use_maximal=False)
            self.assertEqual(a.solve(), b.solve())

    def test_local_event_dominance(self):
        # Check every legal (I,S) in 24 independently generated instances.
        for seed in range(24):
            raw = random_case(1000 + seed, 5)
            e, h = Exact(raw), Horizon(raw)
            for done in range(e.full + 1):
                if not e.ideal[done]:
                    continue
                for extra in range(1, e.full + 1):
                    end = done | extra
                    if done & extra or not e.ideal[end] or not e.feasible[extra]:
                        continue
                    support = set(e.tasks[i].pair for i in bits(extra))
                    for m in h.matchings:
                        if support <= m:
                            ts = h.completion_times(done, m)
                            reached = done | sum(1 << i for i, t in enumerate(ts)
                                                if t is not None and 0 < t <= e.duration[extra])
                            self.assertEqual(end & reached, end)
                            self.assertTrue(e.ideal[reached])
                            self.assertTrue(e.feasible[reached ^ done])
                            self.assertLessEqual(e.duration[reached ^ done], e.duration[extra])

    def test_prefix_dominance(self):
        for seed in range(10):
            raw = random_case(2000 + seed, 5)
            e, h = Exact(raw), Horizon(raw)
            ideals = [i for i in range(e.full + 1) if e.ideal[i]]
            for i in ideals:
                for j in ideals:
                    if i & j != i:
                        continue
                    for m in h.matchings:
                        ti, tj = h.completion_times(i, m), h.completion_times(j, m)
                        for a, b in zip(ti, tj):
                            if a is not None:
                                self.assertIsNotNone(b)
                                self.assertLessEqual(b, a)

    def test_exact_count_spectra_need_not_survive(self):
        raw = {'ports': 2, 'tasks': [dict(pair=[0,1], p=1, pred=[])] * 3}
        spec = Exact(raw).solve()['selective']
        self.assertEqual(spec, {1: 3, 2: 3, 3: 3})
        self.assertEqual(Horizon(raw).solve(), {1: 3})

    def test_no_admission_of_straddling_task(self):
        raw = {'ports': 4, 'tasks': [dict(pair=[0,1], p=1, pred=[]),
                dict(pair=[0,1], p=50, pred=[0]), dict(pair=[2,3], p=2, pred=[])]}
        h = Horizon(raw)
        arcs = h.transitions(0)
        self.assertIn(1, arcs)
        self.assertEqual(arcs[1], 1)
        self.assertIn(5, arcs)
        self.assertEqual(arcs[5], 2)
        self.assertNotIn(3, arcs)  # long same-pair successor finishes at 51, not 1.

    def test_positive_horizons_not_idempotent(self):
        raw = {'ports': 2, 'tasks': [dict(pair=[0,1], p=1, pred=[])] * 3}
        h = Horizon(raw)
        self.assertIn(1, h.transitions(0))
        self.assertIn(3, h.transitions(1))
        self.assertNotEqual(1, 3)  # a relative time budget is not a closure operator.

    def test_constructed_tight_family(self):
        for m in range(1,5):
            for length in (1,7):
                raw = fork(m, length)
                h = Horizon(raw)
                self.assertEqual(h.solve(), {2*m-1: 2*m-1+length})
                for rho in (0,1,9):
                    self.assertEqual(h.schedule(rho)['makespan'], 2*m-1+length+(2*m-2)*rho)

    def test_semantic_collectives(self):
        for shape in ('binary','path','star'):
            for kind in ('allreduce','broadcast'):
                raw = tree_case(4, 2, shape, 913, kind)
                h = Horizon(raw)
                h.solve()
                for rho in (0,1,16):
                    check_collective(raw, h.schedule(rho))

    def test_relabel_and_scaling(self):
        for seed in range(30):
            raw = random_case(3000+seed)
            original = Horizon(raw).solve()
            transformed = copy.deepcopy(raw)
            for t in transformed['tasks']:
                t['pair'] = [5-x for x in t['pair']]
                t['p'] *= 7
            self.assertEqual(Horizon(transformed).solve(), {k: 7*v for k,v in original.items()})

    def test_repeated_solve_resets(self):
        h = Horizon(fork(3,7))
        a = h.solve(); stats = dict(h.stats)
        self.assertEqual(h.solve(), a)
        self.assertEqual(h.stats, stats)

    def test_limits_do_not_report_optimality(self):
        h = Horizon(fork(3,7), Limits(states=1))
        with self.assertRaises(SearchLimit):
            h.solve()
        self.assertFalse(h.stats['complete'])
        self.assertEqual(h.frontier, {})
        with self.assertRaises(SearchLimit):
            Horizon(fork(3,7), Limits(matchings=1))
        with self.assertRaises(ValueError):
            Horizon(fork(3,7), Limits(seconds=-1))

    def test_one_matching_shortcut_checks_elapsed_budget(self):
        raw = {'ports': 2, 'tasks': [{'pair': [0, 1], 'p': 1}]}
        for cls in (Horizon, Prefix):
            with self.subTest(method=cls.__name__):
                with patch('horizon.time.monotonic', return_value=0.0) as clock:
                    engine = cls(raw, Limits(seconds=1))
                    original = engine.completion_times
                    def delayed_timetable(*args):
                        result = original(*args)
                        clock.return_value = 2.0
                        return result
                    engine.completion_times = delayed_timetable
                    with self.assertRaisesRegex(SearchLimit, 'wall-time'):
                        engine.solve()
                    self.assertFalse(engine.stats['complete'])
                    self.assertEqual(engine.frontier, {})
                    self.assertEqual(engine.parents, {})

    def test_one_matching_shortcut_includes_initialization_budget(self):
        raw = {'ports': 2, 'tasks': [{'pair': [0, 1], 'p': 1}]}
        for cls in (Horizon, Prefix):
            with self.subTest(method=cls.__name__):
                with patch('horizon.time.monotonic', return_value=0.0):
                    engine = cls(raw, Limits(seconds=1))
                    engine.initialization_seconds = 2.0
                    with self.assertRaisesRegex(SearchLimit, 'wall-time'):
                        engine.solve()
                    self.assertFalse(engine.stats['complete'])
                    self.assertEqual(engine.frontier, {})

    def test_frontier_exact_values(self):
        for seed in range(200):
            r = random.Random(seed)
            sp = {k: r.randint(1,50) for k in range(1, r.randint(2,10))}
            env = envelope(sp)
            for x in [Fraction(i,7) for i in range(50)] + [Fraction(100)]:
                row = next(a for a in env if Fraction(a['lo']) <= x and
                           (a['hi'] is None or x <= Fraction(a['hi'])))
                self.assertEqual(row['service'] + (row['epochs']-1)*x,
                                 min(b+(k-1)*x for k,b in sp.items()))

    def test_prefix_baseline(self):
        for seed in range(50):
            raw = random_case(4000+seed, 5+seed%2)
            self.assertEqual(Prefix(raw).solve(), pareto(Exact(raw).solve()['selective']))

    def test_maximal_saturation_is_not_dominant(self):
        raw = {'ports': 6, 'tasks': [dict(pair=[0,1],p=1,pred=[]),
               dict(pair=[1,4],p=1,pred=[0]), dict(pair=[0,5],p=10,pred=[1]),
               dict(pair=[2,3],p=10,pred=[])]}
        class MaximalSaturation(Horizon):
            def transitions(self, done):
                arcs = {}
                for m in self.matchings:
                    times = self.completion_times(done,m)
                    extra = sum(1<<v for v,t in enumerate(times) if t is not None and t>0)
                    if extra:
                        arcs[done|extra] = max(t for t in times if t is not None)
                return arcs
        self.assertEqual(Exact(raw).solve()['saturated'][2], 12)
        self.assertEqual(Horizon(raw).solve(), {2:12})
        self.assertEqual(MaximalSaturation(raw).solve(), {2:21})

    def test_aggregate_demands_do_not_determine_price(self):
        for m in range(2,5):
            for length in (1,7,19):
                raw = fork(m,length)
                independent = copy.deepcopy(raw)
                for task in independent['tasks']:
                    task['pred'] = []  # parse restores the identical pair FIFO.
                self.assertEqual([t['pair'] for t in raw['tasks']],
                                 [t['pair'] for t in independent['tasks']])
                e = Exact(independent)
                self.assertEqual(e.solve()['selective'][2], length+2)
                self.assertEqual(e.solve()['saturated'][2], length+2)
                for rho in (0,1,13):
                    for mode in ('selective','saturated'):
                        self.assertEqual(e.schedule(rho,mode)['makespan'],length+2+rho)

    def test_all_small_legal_schedules_normalize_taskwise(self):
        checked = 0
        for seed in range(8):
            raw = random_case(5000+seed,4)
            exact = Exact(raw)
            def visit(done, batches):
                nonlocal checked
                if done == exact.full:
                    for rho in (0,1,9):
                        original = certificate(exact.tasks,batches,rho,'selective')
                        new = normalize(raw,original)
                        self.assertLessEqual(new['makespan'],original['makespan'])
                        checked += 1
                    return
                for extra in range(1,exact.full+1):
                    if extra & done == 0 and exact.ideal[extra|done] and exact.feasible[extra]:
                        visit(done|extra,batches+[extra])
            visit(0,[])
        self.assertGreater(checked,24)

    def test_oracle_cap_is_explicit(self):
        for cap in (True,0,7,1.5):
            with self.assertRaises(ValueError):
                oracle_spectra(random_case(0,3),max_tasks=cap)
        with self.assertRaises(ValueError):
            oracle_spectra(random_case(0,5))
        _, counts = oracle_spectra(random_case(0,5),max_tasks=5)
        self.assertEqual(counts['assignments'],3125)

    def test_verifier_rejects_tampered_frontier(self):
        from evaluate_horizon import run_reference
        from verify_horizon import validate_row
        raw = fork(2,7); raw['case']='test'; raw['family']='fork'
        good = run_reference(raw)
        validate_row(good,raw,'weighted')
        bad = copy.deepcopy(good)
        key = next(iter(bad['horizon']['frontier']))
        bad['horizon']['frontier'][key] += 1
        with self.assertRaises(ValueError):
            validate_row(bad,raw,'weighted')
        bad = copy.deepcopy(good)
        bad['policy']['max_ratio'] = '1000'
        with self.assertRaises(ValueError):
            validate_row(bad,raw,'weighted')

    def test_bad_input_is_rejected(self):
        for raw in ({}, {'ports':2,'tasks':[]}, {'ports':2,'tasks':[dict(pair=[0,0],p=1)]},
                    {'ports':2,'tasks':[dict(pair=[0,1],p=0)]}):
            with self.assertRaises(ValueError):
                Horizon(raw)

if __name__ == '__main__':
    unittest.main()
