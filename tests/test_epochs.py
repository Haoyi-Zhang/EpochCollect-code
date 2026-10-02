"""Deterministic positive and deliberately invalid schedule controls."""
import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import checker, epochs, generators, oracle, reproduce

class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.raw = generators.fork(3,7)
        self.engine = epochs.Exact(self.raw)
        self.cert = self.engine.schedule(1)

    def reject(self, modify):
        c=copy.deepcopy(self.cert); modify(c)
        with self.assertRaises(ValueError): checker.check(self.raw,c)

    def test_valid_selective(self):
        self.assertEqual(checker.check(self.raw,self.cert)['makespan'],16)

    def test_valid_saturated(self):
        self.assertEqual(checker.check(self.raw,self.engine.schedule(1,'saturated'))['makespan'],30)

    def test_false_saturation(self):
        self.reject(lambda c:c.update(mode='saturated'))

    def test_short_service(self):
        self.reject(lambda c:c['epochs'][0]['events'][0].update(finish=0))

    def test_setup_overlap(self):
        self.reject(lambda c:c['epochs'][1].update(start=1))

    def test_epoch_ends_before_drain(self):
        self.reject(lambda c:c['epochs'][-1].update(end=c['epochs'][-1]['end']-1))

    def test_missing_task(self):
        self.reject(lambda c:c['epochs'].pop())

    def test_duplicate_identity(self):
        self.reject(lambda c:c['epochs'][0]['tasks'].append(0))

    def test_incorrect_makespan(self):
        self.reject(lambda c:c.update(makespan=15))

    def test_unknown_mode(self):
        self.reject(lambda c:c.update(mode='unsupported'))

    def test_nonideal_epoch(self):
        raw={'ports':4,'tasks':[{'pair':[0,1],'p':1,'pred':[]},
             {'pair':[1,2],'p':1,'pred':[0]},{'pair':[0,1],'p':1,'pred':[1]}]}
        _,ts=epochs.parse(raw)
        c=epochs.certificate(ts,[5,2],0)
        with self.assertRaisesRegex(ValueError,'ideal'): checker.check(raw,c)

    def test_nonmatching_epoch(self):
        raw={'ports':3,'tasks':[{'pair':[0,1],'p':1},{'pair':[1,2],'p':1}]}
        _,ts=epochs.parse(raw); c=epochs.certificate(ts,[3],0)
        with self.assertRaisesRegex(ValueError,'partners'):checker.check(raw,c)

    def test_noncanonical_noncritical_delay(self):
        raw={'ports':4,'tasks':[{'pair':[0,1],'p':3},{'pair':[2,3],'p':1}]}
        c=epochs.Exact(raw).schedule(0)
        c['epochs'][0]['events'][1].update(start=1,finish=2)
        with self.assertRaisesRegex(ValueError,'canonical'):checker.check(raw,c)

    def test_reverse_arc(self):
        raw=copy.deepcopy(self.raw);raw['tasks'][0]['pred']=[1]
        for parser in (epochs.parse,checker.checked_input):
            with self.assertRaises(ValueError):parser(raw)

    def test_boolean_duration(self):
        raw=copy.deepcopy(self.raw);raw['tasks'][0]['p']=True
        for parser in (epochs.parse,checker.checked_input):
            with self.assertRaises(ValueError):parser(raw)

    def test_zero_duration(self):
        raw=copy.deepcopy(self.raw);raw['tasks'][0]['p']=0
        for parser in (epochs.parse,checker.checked_input):
            with self.assertRaises(ValueError):parser(raw)

    def test_bad_endpoint(self):
        raw=copy.deepcopy(self.raw);raw['tasks'][0]['pair']=[0,raw['ports']]
        for parser in (epochs.parse,checker.checked_input):
            with self.assertRaises(ValueError):parser(raw)

    def test_implicit_fifo(self):
        raw={'ports':2,'tasks':[{'pair':[0,1],'p':2},{'pair':[1,0],'p':3}]}
        e=epochs.Exact(raw);c=e.schedule(0)
        self.assertEqual(c['makespan'],5)
        self.assertEqual(checker.checked_input(raw)[2],[set(),{0}])
        checker.check(raw,c)

    def test_solve_is_repeatable(self):
        a=self.engine.solve(); stats=copy.deepcopy(self.engine.stats)
        self.assertEqual(a,self.engine.solve());self.assertEqual(stats,self.engine.stats)

    def test_exact_limit(self):
        raw={'ports':2,'tasks':[{'pair':[0,1],'p':1} for _ in range(17)]}
        with self.assertRaises(ValueError):epochs.Exact(raw)

    def test_oracle_limit(self):
        with self.assertRaises(ValueError):oracle.spectra(self.raw)

class MathematicalControls(unittest.TestCase):
    def test_formula_grid(self):
        for m in (1,2,3,4,5):
            for length in (1,7,31):
                raw=generators.fork(m,length);e=epochs.Exact(raw);s=e.solve()
                self.assertEqual(min(s['selective']),2*m-1)
                self.assertEqual(min(s['saturated']),2*m-1)
                for rho in (0,1,4,16):
                    for mode,coefficient in [('selective',1),('saturated',m)]:
                        c=e.schedule(rho,mode);checker.check(raw,c)
                        self.assertEqual(c['makespan'],2*m-1+coefficient*length+(2*m-2)*rho)

    def test_unit_expansion(self):
        for m,length in [(2,2),(3,2),(4,2),(2,3),(3,3)]:
            raw=generators.fork(m,length,True);e=epochs.Exact(raw)
            for mode,coefficient in [('selective',1),('saturated',m)]:
                c=e.schedule(1,mode);checker.check(raw,c)
                self.assertEqual(c['makespan'],4*m-3+coefficient*length)

    def test_unique_pair_null(self):
        raw={'ports':6,'tasks':[{'pair':[0,1],'p':3}, {'pair':[2,3],'p':2},
             {'pair':[4,5],'p':7,'pred':[0]},{'pair':[1,2],'p':5,'pred':[1]}]}
        e=epochs.Exact(raw);s=e.solve()
        self.assertEqual(s['selective'],s['saturated'])

    def test_total_order_null(self):
        raw={'ports':4,'tasks':[{'pair':[0,1],'p':3}, {'pair':[2,3],'p':2,'pred':[0]},
             {'pair':[0,1],'p':7,'pred':[1]},{'pair':[1,2],'p':5,'pred':[2]}]}
        e=epochs.Exact(raw)
        for rho in (0,1,4,16):
            self.assertEqual(e.schedule(rho)['makespan'],e.schedule(rho,'saturated')['makespan'])

    def test_independent_queues_are_not_a_null(self):
        # AB has two chunks; CD then DE can be packed beside separate AB chunks.
        raw={'ports':5,'tasks':[{'pair':[0,1],'p':10},{'pair':[0,1],'p':10},
             {'pair':[2,3],'p':10},{'pair':[3,4],'p':10}]}
        e=epochs.Exact(raw)
        self.assertEqual(e.schedule(0)['makespan'],20)
        self.assertEqual(e.schedule(0,'saturated')['makespan'],30)

    def test_symbolic_collectives(self):
        for kind in ('broadcast','allreduce'):
            for shape in ('binary','path','star'):
                raw=generators.tree_case(4,2,shape,7,kind);e=epochs.Exact(raw)
                for mode in ('selective','saturated'):
                    self.assertTrue(checker.check_collective(raw,e.schedule(1,mode))['valid'])

    def test_bad_symbolic_value(self):
        raw=generators.tree_case(4,2,'binary',7,'allreduce');c=epochs.Exact(raw).schedule(1)
        raw['tasks'][0]['value']=0
        with self.assertRaisesRegex(ValueError,'source value'):checker.check_collective(raw,c)

    def test_missing_symbolic_destination(self):
        raw=generators.tree_case(4,1,'binary',7,'broadcast')
        raw['chunks']=2;c=epochs.Exact(raw).schedule(1)
        with self.assertRaisesRegex(ValueError,'postcondition'):checker.check_collective(raw,c)

    def test_completion_triggered_interval(self):
        raw=generators.fork(4,7);c=epochs.Exact(raw).schedule(4)
        p=[t['p'] for t in raw['tasks']]
        self.assertLessEqual(reproduce.replay(raw,c,[x+1 for x in p],8),2*c['makespan'])
        self.assertEqual(reproduce.replay(raw,c,[2*x for x in p],8),2*c['makespan'])

    def test_unbounded_service_has_no_bound(self):
        raw={'ports':2,'tasks':[{'pair':[0,1],'p':1}]};c=epochs.Exact(raw).schedule(0)
        self.assertEqual(reproduce.replay(raw,c,[1000000],0),1000000)

class SemanticSchemaTests(unittest.TestCase):
    def setUp(self):
        self.raw = generators.tree_case(4, 2, 'binary', 7, 'allreduce')
        self.cert = epochs.Exact(self.raw).schedule(1)

    def reject(self, change):
        raw = copy.deepcopy(self.raw)
        change(raw)
        with self.assertRaises(ValueError):
            checker.check_collective(raw, self.cert)

    def test_unknown_semantics(self):
        self.reject(lambda r: r.update(semantics='all-reduce'))

    def test_null_semantics(self):
        self.reject(lambda r: r.update(semantics=None))

    def test_zero_chunks(self):
        self.reject(lambda r: r.update(chunks=0))

    def test_boolean_chunks(self):
        self.reject(lambda r: r.update(chunks=True))

    def test_symbolic_cell_budget(self):
        self.reject(lambda r: r.update(chunks=1000000))

    def test_unknown_phase(self):
        self.reject(lambda r: r['tasks'][0].update(phase='copy-typo'))

    def test_negative_chunk(self):
        self.reject(lambda r: r['tasks'][0].update(chunk=-1))

    def test_out_of_range_chunk(self):
        self.reject(lambda r: r['tasks'][0].update(chunk=2))

    def test_boolean_source(self):
        self.reject(lambda r: r['tasks'][0].update(src=True))

    def test_missing_destination(self):
        self.reject(lambda r: r['tasks'][0].pop('dst'))

    def test_boolean_value(self):
        self.reject(lambda r: r['tasks'][0].update(value=True))

    def test_foreign_symbol(self):
        self.reject(lambda r: r['tasks'][0].update(value=16))

    def test_reduction_not_broadcast(self):
        raw = generators.tree_case(4, 1, 'binary', 7, 'broadcast')
        cert = epochs.Exact(raw).schedule(1)
        raw['tasks'][0]['phase'] = 'reduce'
        with self.assertRaisesRegex(ValueError, 'not a broadcast'):
            checker.check_collective(raw, cert)

    def test_generic_not_applicable(self):
        raw = generators.fork(2, 3)
        result = checker.check_collective(raw, epochs.Exact(raw).schedule(1))
        self.assertEqual(result, {'applicable': False})

    def test_mixed_type_endpoints(self):
        raw = {'ports': 2, 'tasks': [{'pair': [0, '1'], 'p': 1}]}
        for parse in (epochs.parse, checker.checked_input):
            with self.assertRaises(ValueError):
                parse(raw)

if __name__=='__main__':unittest.main(verbosity=2)
