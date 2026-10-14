"""Owned finite disagreement/admission controls, including optimized Python."""
import copy
import unittest
import sys
from unittest.mock import patch

import evaluate_horizon as evaluation
import reproduce
from horizon import envelope
from verify_horizon import engine
from reproduce_all import python_command, main as reproduce_main, ROOT
from workflow_cost import workflow, compare
from horizon import Horizon
from prefix import Prefix
import json


RAW = {'case': 'owned-one-task', 'family': 'owned', 'ports': 2,
       'tasks': [{'pair': [0, 1], 'p': 3}]}


class EvidenceGateTests(unittest.TestCase):
    def test_child_interpreter_preserves_optimization(self):
        command = python_command('reproduce.py')
        self.assertEqual(command.count('-O'), sys.flags.optimize)
        self.assertIn('-B', command)

    def test_cached_directory_cannot_claim_fresh_execution(self):
        with patch('sys.argv', ['reproduce_all.py', '--full', '--output-dir', str(ROOT/'evidence/owned-cache')]), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.iterdir', return_value=iter(['existing-record'])), \
             patch('reproduce_all.run') as execute:
            with self.assertRaises(SystemExit) as error:
                reproduce_main()
            self.assertEqual(error.exception.code, 2)
            execute.assert_not_called()

    def test_full_workflow_equal_information_and_cost_partition(self):
        text = json.dumps(RAW)
        a, b = workflow(text, Horizon), workflow(text, Prefix)
        compare(a, b)
        for row in (a, b):
            timing = row['timing_ns']
            parts = [timing[k] for k in ('input_decode', 'initialize_and_solve',
                     'reconstruct', 'validate', 'serialize_decode_replay', 'deadline_query')]
            self.assertEqual(sum(parts), timing['total'])
            self.assertTrue(all(x >= 0 for x in parts))
            self.assertEqual([c['makespan'] for c in row['certificates']], [3]*4)
            self.assertTrue(row['decision']['unbounded'])
        bad = copy.deepcopy(b); bad['deadline'] += 1
        with self.assertRaisesRegex(ValueError, 'workflow disagreement'):
            compare(a, bad)

    def test_assignment_disagreement_cannot_report_agreement(self):
        bad = {'selective': {1: 4}, 'saturated': {1: 4}}
        with patch('reproduce.oracle.spectra', return_value=(bad, {})):
            with self.assertRaisesRegex(AssertionError, 'spectrum mismatch'):
                reproduce.run_exhaustive(copy.deepcopy(RAW))

    def test_incomplete_reference_cannot_report_agreement(self):
        with patch('evaluate_horizon.run_engine', return_value={'status': 'incomplete'}):
            with self.assertRaisesRegex(AssertionError, 'reference search incomplete'):
                evaluation.run_reference(copy.deepcopy(RAW))

    def test_larger_oracle_disagreement_cannot_report_agreement(self):
        bad = {'selective': {1: 4}, 'saturated': {1: 4}}
        with patch('evaluate_horizon.oracle.spectra', return_value=(bad, {})):
            with self.assertRaisesRegex(AssertionError, 'oracle frontier mismatch'):
                evaluation.run_oracle(copy.deepcopy(RAW))

    def test_stress_disagreement_is_not_success(self):
        outputs = [{'status': 'complete', 'frontier': {1: 3}},
                   {'status': 'complete', 'frontier': {1: 4}}]
        with patch('evaluate_horizon.run_engine', side_effect=outputs):
            with self.assertRaisesRegex(AssertionError, 'stress frontier mismatch'):
                evaluation.run_stress(copy.deepcopy(RAW))

    def test_policy_ordering_is_enforced(self):
        with self.assertRaisesRegex(AssertionError, 'policy ordering'):
            evaluation.compare_policies({1: 3}, {1: 2})

    def test_envelope_rejects_noninteger_count_or_service(self):
        for frontier in ({True: 3}, {1.9: 3}, {'1': 3}, {0: 3},
                         {1: True}, {1: 0}, {1: 3.0}, {}, []):
            with self.subTest(frontier=frontier):
                with self.assertRaises(ValueError):
                    envelope(frontier)

    def test_shared_breakpoint_belongs_to_smaller_count(self):
        from fractions import Fraction
        rows = envelope({4: 41, 6: 38})
        point = Fraction(3, 2)
        selected = [row for row in rows if Fraction(row['lo']) <= point and
                    (row['hi'] is None or point < Fraction(row['hi']))]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]['epochs'], 4)

    def test_json_frontier_aliases_are_not_silently_merged(self):
        stats = dict(complete=True, matchings=1, states=2, transitions=1,
                     horizon_candidates=1, labels=2)
        for frontier in ({'01': 3}, {'+1': 3}, {'1': 3, '01': 3}, {True: 3}):
            with self.subTest(frontier=frontier):
                with self.assertRaisesRegex(ValueError, 'count key'):
                    engine({'status': 'complete', 'stats': stats, 'frontier': frontier}, 1)
        self.assertEqual(engine({'status': 'complete', 'stats': stats,
                                 'frontier': {'1': 3}}, 1), {1: 3})


if __name__ == '__main__':
    unittest.main(verbosity=2)
