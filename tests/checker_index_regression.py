"""Finite independent checker-index controls; run explicitly, without a campaign.

All fixtures and references are local to this public artifact. These controls
test feasibility and exact rejection, not optimization, timing or a general proof.
"""
import copy
import itertools
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import checker


def fifo_reference(raw):
    """Build complete per-pair queues, then add adjacent queue edges."""
    pairs = [tuple(sorted(t['pair'])) for t in raw['tasks']]
    durations = [t['p'] for t in raw['tasks']]
    pred = [set(t.get('pred', [])) for t in raw['tasks']]
    ordered = sorted(range(len(pairs)), key=lambda v: (pairs[v], v))
    for _, group in itertools.groupby(ordered, key=lambda v: pairs[v]):
        ids = list(group)
        for u, v in zip(ids, ids[1:]):
            pred[v].add(u)
    return pairs, durations, pred


def overlap_reference(pairs, eventmap):
    """Pairwise endpoint intersection; no endpoint buckets or adjacent scan."""
    for u, v in itertools.combinations(range(len(pairs)), 2):
        a, b = eventmap[u]
        c, d = eventmap[v]
        if set(pairs[u]) & set(pairs[v]) and max(a, c) < min(b, d):
            return True
    return False


def scalar_certificate(raw, batches, rho=0, mode='selective'):
    """Scalar completion simulation: next completion by scanning running tasks."""
    pairs, durations, pred = fifo_reference(raw)
    complete, now, epochs = set(), 0, []
    for index, ids in enumerate(batches):
        if index:
            now += rho
        start = now
        waiting, running, events = set(ids), {}, []
        while waiting or running:
            for v in sorted(waiting):
                if pred[v] <= complete:
                    waiting.remove(v)
                    running[v] = now + durations[v]
                    events.append({'task': v, 'start': now, 'finish': running[v]})
            if not running:
                raise AssertionError('reference batch is not an ideal difference')
            now = min(running.values())
            finished = [v for v in running if running[v] == now]
            for v in finished:
                del running[v]
                complete.add(v)
        epochs.append({'tasks': list(ids), 'start': start, 'end': now,
                       'events': events})
    return {'mode': mode, 'rho': rho, 'epochs': epochs, 'makespan': now}


def bounded_encodings():
    for n, alphabet, durations in (
        (3, list(itertools.combinations(range(4), 2)), (1, 2, 3)),
        (4, [(0, 1), (1, 2), (2, 3)], (1, 3, 2, 4)),
    ):
        edges = list(itertools.combinations(range(n), 2))
        for word in itertools.product(alphabet, repeat=n):
            for mask in range(1 << len(edges)):
                tasks = []
                for i, pair in enumerate(word):
                    deps = [u for j, (u, v) in enumerate(edges)
                            if v == i and mask >> j & 1]
                    tasks.append({'pair': list(pair if i % 2 else pair[::-1]),
                                  'p': durations[i], 'pred': deps + deps})
                yield {'ports': 4, 'tasks': tasks}


class CheckerIndexRegression(unittest.TestCase):
    def test_all_6912_fifo_encodings(self):
        count = 0
        for raw in bounded_encodings():
            self.assertEqual(checker.checked_input(raw), fifo_reference(raw))
            count += 1
        self.assertEqual(count, 6912)

    def test_strict_admission_errors(self):
        good = {'ports': 4, 'tasks': [{'pair': [0, 1], 'p': 1},
                                     {'pair': [1, 0], 'p': 2, 'pred': [0, 0]}]}
        cases = [(None, 'invalid port count'), ({}, 'invalid port count')]
        for ports in (True, 1, 10001, 4.0):
            raw = copy.deepcopy(good); raw['ports'] = ports
            cases.append((raw, 'invalid port count'))
        for tasks in (None, [], (), [None], [{}]):
            raw = copy.deepcopy(good); raw['tasks'] = tasks
            cases.append((raw, 'invalid task count' if tasks in (None, [], ()) else 'invalid pair'))
        for pair in (None, [0], [0, 1, 2], {0, 1}):
            raw = copy.deepcopy(good); raw['tasks'][0]['pair'] = pair
            cases.append((raw, 'invalid pair'))
        for pair in ([0, True], [0, '1'], [0, 4], [0, -1], [1, 1]):
            raw = copy.deepcopy(good); raw['tasks'][0]['pair'] = pair
            cases.append((raw, 'invalid endpoints'))
        for duration in (True, 0, -1, 1.0, 10**12 + 1):
            raw = copy.deepcopy(good); raw['tasks'][0]['p'] = duration
            cases.append((raw, 'invalid duration'))
        for deps in ([True], [1], [-1], [0.0], (0,), None):
            raw = copy.deepcopy(good); raw['tasks'][1]['pred'] = deps
            cases.append((raw, 'not topologically indexed'))
        for raw, expected in cases:
            with self.subTest(expected=expected, raw=raw):
                with self.assertRaisesRegex(ValueError, '^' + expected + '$'):
                    checker.checked_input(raw)

    def test_input_bounds_and_call_locality(self):
        raw = {'ports': 10000, 'tasks': [
            {'pair': [9999, 0], 'p': 10**12} for _ in range(10000)]}
        pairs, durations, pred = checker.checked_input(raw)
        self.assertEqual(len(pairs), 10000)
        self.assertTrue(all(p == (0, 9999) for p in pairs))
        self.assertTrue(all(d == 10**12 for d in durations))
        self.assertEqual(pred, [set()] + [{i - 1} for i in range(1, 10000)])
        raw['tasks'].append({'pair': [0, 1], 'p': 1})
        with self.assertRaisesRegex(ValueError, '^invalid task count$'):
            checker.checked_input(raw)
        raw['tasks'] = [{'pair': [9999, 0], 'p': 1}]
        self.assertEqual(checker.checked_input(raw)[2], [set()])
        self.assertEqual(checker.checked_input(raw), fifo_reference(raw))

    def test_direct_overlap_and_half_open_boundaries(self):
        pairs_options = [((0, 9999), (0, 9999)),
                         ((0, 9999), (1, 9999)),
                         ((0, 9999), (1, 9998))]
        count = 0
        for pairs in pairs_options:
            for a, c, p, q in itertools.product(range(4), range(4), (1, 2), (1, 2)):
                events = {0: (a, a + p), 1: (c, c + q)}
                if overlap_reference(pairs, events):
                    with self.assertRaisesRegex(ValueError, '^endpoint service overlap$'):
                        checker._check_endpoint_intervals(pairs, events)
                else:
                    self.assertIsNone(checker._check_endpoint_intervals(pairs, events))
                count += 1
        self.assertEqual(count, 192)
        pairs = [(0, 9999)] * 3
        for events in ({0: (0, 1), 1: (1, 2), 2: (2, 3)},
                       {0: (1, 2), 1: (2, 3), 2: (0, 1)}):
            self.assertFalse(overlap_reference(pairs, events))
            checker._check_endpoint_intervals(pairs, events)
        for events in ({0: (0, 9), 1: (1, 2), 2: (2, 3)},
                       {0: (0, 1), 1: (0, 1), 2: (2, 3)}):
            self.assertTrue(overlap_reference(pairs, events))
            with self.assertRaisesRegex(ValueError, '^endpoint service overlap$'):
                checker._check_endpoint_intervals(pairs, events)

    def test_canonical_certificates_and_rejections(self):
        patterns = [((0, 9999),) * 4,
                    ((0, 1), (2, 3), (1, 0), (3, 2)),
                    ((0, 1), (1, 2), (2, 3), (3, 9999)),
                    ((0, 1), (2, 3), (4, 5), (6, 9999))]
        edges = list(itertools.combinations(range(4), 2))
        for word in patterns:
            for mask in range(64):
                raw = {'ports': 10000, 'tasks': [
                    {'pair': list(word[v]), 'p': (1, 3, 2, 4)[v],
                     'pred': [u for j, (u, w) in enumerate(edges) if w == v and mask >> j & 1]}
                    for v in range(4)]}
                cert = scalar_certificate(raw, [[v] for v in range(4)], rho=2)
                result = checker.check(raw, cert)
                self.assertEqual(result, {'valid': True, 'tasks': 4, 'epochs': 4,
                    'makespan': 16, 'meaning': 'feasible canonical timeline, not a proof of optimality'})
        raw = {'ports': 10000, 'tasks': [dict(pair=[0, 9999], p=3),
                                       dict(pair=[1, 9998], p=1)]}
        cert = scalar_certificate(raw, [[0, 1]])
        self.assertTrue(checker.check(raw, cert)['valid'])
        bad = copy.deepcopy(cert)
        bad['epochs'][0]['events'][1].update(start=1, finish=2)
        with self.assertRaisesRegex(ValueError, '^event is not the canonical ASAP execution$'):
            checker.check(raw, bad)
        bad = copy.deepcopy(cert); bad['epochs'][0]['tasks'].append(0)
        with self.assertRaisesRegex(ValueError, '^duplicate or invalid task$'):
            checker.check(raw, bad)
        bad = copy.deepcopy(cert); bad['makespan'] = 4
        with self.assertRaisesRegex(ValueError, '^incorrect makespan$'):
            checker.check(raw, bad)

    def test_symbolic_start_capture_and_budget_controls(self):
        raw = {'ports': 3, 'semantics': 'broadcast', 'chunks': 1, 'tasks': [
            dict(pair=[0, 1], p=2, src=0, dst=1, chunk=0, value=1, phase='broadcast'),
            dict(pair=[1, 2], p=1, pred=[0], src=1, dst=2, chunk=0, value=1, phase='broadcast')]}
        cert = scalar_certificate(raw, [[0], [1]])
        self.assertEqual(checker.check_collective(raw, cert), {'applicable': True,
            'valid': True, 'chunks': 1,
            'meaning': 'exact symbolic data coverage, not floating-point or device execution'})
        for key, value, error in [('chunks', 21846, 'invalid symbolic chunk count or cell budget'),
                                  ('chunks', True, 'invalid symbolic chunk count or cell budget'),
                                  ('semantics', None, 'unknown collective semantics')]:
            bad = copy.deepcopy(raw); bad[key] = value
            with self.assertRaisesRegex(ValueError, '^' + error + '$'):
                checker.check_collective(bad, cert)
        bad = copy.deepcopy(raw); bad['tasks'][1]['src'] = 2; bad['tasks'][1]['dst'] = 1
        with self.assertRaisesRegex(ValueError, '^symbolic source value unavailable at start$'):
            checker.check_collective(bad, cert)


if __name__ == '__main__':
    unittest.main(verbosity=2)
