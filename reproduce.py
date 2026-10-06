"""Bounded, single-worker, resumable reproduction of the frozen experiment.

Run from any directory. A completed invocation is explicitly marked COMPLETE;
otherwise run the same command again. Exact scientific results are compared to
independent event and assignment implementations, not to stored golden answers.
"""
from __future__ import annotations
import argparse, csv, json, os, sys, time
from collections import defaultdict
from pathlib import Path
import checker, epochs, generators, oracle

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'results'
RHOS = (0, 1, 4, 16)


def lower_bound(raw):
    ports, ts = epochs.parse(raw)
    work = sum(t.p for t in ts)
    load = max(sum(t.p for t in ts if v in t.pair) for v in range(ports))
    finish = []
    for t in ts:
        finish.append(t.p + max((finish[d] for d in t.pred), default=0))
    return {'work': work, 'capacity': ports // 2, 'endpoint_load': load, 'critical_path': max(finish)}


def greedy(raw, rho, saturate=False):
    _, ts = epochs.parse(raw)
    done, batches = 0, []
    full = (1 << len(ts)) - 1
    pred = [sum(1 << d for d in t.pred) for t in ts]
    while done != full:
        matching, ports, mask = set(), set(), 0
        for v, t in enumerate(ts):
            if done >> v & 1 or pred[v] & done != pred[v]:
                continue
            if t.pair in matching or not set(t.pair) & ports:
                matching.add(t.pair); ports.update(t.pair); mask |= 1 << v
        if saturate:
            reached = done
            for v, t in enumerate(ts):
                if t.pair in matching and pred[v] & reached == pred[v]:
                    reached |= 1 << v
            mask = reached ^ done
        if not mask:
            raise AssertionError('ready-set greedy failed to progress')
        batches.append(mask); done |= mask
    return epochs.certificate(ts, batches, rho, 'saturated' if saturate else 'selective')


def replay(raw, cert, p, rho):
    """Independent completion-triggered execution with changed service times."""
    pairs, _, pred = checker.checked_input(raw)
    done, now = set(), 0
    for i, ep in enumerate(cert['epochs']):
        service, _ = checker.interpret(ep['tasks'], done, pairs, p, pred)
        now += service + (rho if i else 0)
        done.update(ep['tasks'])
    return now


def run_exhaustive(raw):
    engine = epochs.Exact(raw)
    a = engine.solve()
    b, counts = oracle.spectra(raw)
    assert a == b, ('spectrum mismatch', raw, a, b)
    assert min(a['selective']) == min(a['saturated']), ('minimum epoch mismatch', raw)
    for rho in (0, 1, 4):
        for mode in a:
            checker.check(raw, engine.schedule(rho, mode))
    return {'case': raw['case'], 'family': raw['family'], 'spectrum': a,
            'search': engine.stats, 'oracle': counts, 'agreement': True}


def run_weighted(raw):
    engine = epochs.Exact(raw)
    spectrum = engine.solve()
    assert min(spectrum['selective']) == min(spectrum['saturated'])
    costs, robustness, semantic_checks = [], [], 0
    for rho in RHOS:
        certs = {mode: engine.schedule(rho, mode) for mode in ('selective', 'saturated')}
        certs['entry-greedy'] = greedy(raw, rho)
        certs['saturated-greedy'] = greedy(raw, rho, True)
        _, ts = epochs.parse(raw)
        certs['singleton'] = epochs.certificate(ts, [1 << i for i in range(len(ts))], rho)
        row = {'rho': rho}
        for name, c in certs.items():
            checker.check(raw, c)
            sem = checker.check_collective(raw, c)
            semantic_checks += int(sem.get('applicable', False))
            row[name] = c['makespan']; row[name + '-epochs'] = len(c['epochs'])
        assert row['selective'] <= row['saturated'] <= row['saturated-greedy']
        assert row['selective'] <= row['entry-greedy'] and row['selective'] <= row['singleton']
        assert row['saturated'] <= (raw['ports'] // 2) * row['selective']
        if raw['family'] == 'total-chain':
            assert row['saturated'] == row['selective']
        if raw['family'] in ('fork', 'unit-fork'):
            m, length = raw['m'], raw['length']
            assert row['selective'] == 2*m-1 + length + (2*m-2)*rho
            assert row['saturated'] == 2*m-1 + m*length + (2*m-2)*rho
        costs.append(row)
        p = [t.p for t in ts]
        actual = [v + (i % 3) for i, v in enumerate(p)]
        # p_actual <= 3*p, rho_actual <= 2*rho (including rho=0).
        observed = replay(raw, certs['selective'], actual, 2*rho)
        assert observed <= 3 * certs['selective']['makespan']
        upper = replay(raw, certs['selective'], [3*v for v in p], 2*rho)
        assert observed <= upper
        robustness.append({'rho': rho, 'actual_cost': observed, 'interval_upper': upper,
                           'multiplicative_upper': 3*certs['selective']['makespan']})
        if rho == 1:
            out = RESULTS/'certificates'/f"{raw['case']}.json"
            out.parent.mkdir(exist_ok=True)
            out.write_text(json.dumps({'instance': raw, 'certificates': certs}, separators=(',', ':'))+'\n')
    return {'case': raw['case'], 'family': raw['family'], 'shape': raw.get('shape'),
            'tasks': len(raw['tasks']), 'ports': raw['ports'], 'costs': costs,
            'bounds': lower_bound(raw), 'spectrum': spectrum, 'search': engine.stats,
            'robustness': robustness, 'semantic_checks': semantic_checks}


def run_scale(raw):
    _, ts = epochs.parse(raw)
    m, length, rho = raw['m'], raw['length'], raw['rho']
    selective, saturated, leaves = [], [], 0
    for i in range(m):
        a, leaf = 3*i, 3*i+1
        leaves |= 1 << leaf
        saturated.append((1 << a) | (1 << leaf))
        if i < m-1:
            selective += [1 << a, 1 << (a+2)]
            saturated.append(1 << (a+2))
    selective.append(leaves | (1 << (3*(m-1))))
    costs, certs = {}, {}
    for mode, masks in [('selective', selective), ('saturated', saturated)]:
        c = epochs.certificate(ts, masks, rho, mode)
        checker.check(raw, c)
        expected = 2*m-1 + (length if mode=='selective' else m*length) + (2*m-2)*rho
        assert c['makespan'] == expected
        costs[mode] = c['makespan']
        certs[mode] = c
    target = RESULTS/'certificates'/f"{raw['case']}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({'instance': raw, 'certificates': certs}, separators=(',', ':'))+'\n')
    return {'case':raw['case'], 'm': m, 'length': length, 'rho': rho, 'tasks':len(ts),
            'epochs':2*m-1, **costs, 'meaning':'explicit certificates checked; optimality uses the theorem, not large exact search'}


def summarize():
    result = {}
    for phase, expected in [('exhaustive',6912),('weighted',240),('scale',80)]:
        path = RESULTS/f'{phase}.jsonl'
        rows = [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
        result[phase] = {'completed':len(rows), 'expected':expected,
                         'cpu_seconds':sum(r['cpu_seconds'] for r in rows),
                         'peak_rss_kib':max((r['peak_rss_kib'] for r in rows), default=0)}
        if phase == 'exhaustive':
            result[phase]['assignments'] = sum(r['oracle']['assignments'] for r in rows)
            result[phase]['valid_assignments'] = sum(r['oracle']['valid_assignments'] for r in rows)
            result[phase]['spectrum_disagreements'] = sum(not r['agreement'] for r in rows)
        if phase == 'weighted':
            result[phase]['symbolic_collective_checks'] = sum(r['semantic_checks'] for r in rows)
            grouped = defaultdict(list)
            for r in rows:
                for c in r['costs']:
                    grouped[r['family'],c['rho']].append(c)
            summary = []
            for (family,rho), values in sorted(grouped.items()):
                ratios = [c['saturated']/c['selective'] for c in values]
                summary.append({'family':family, 'rho':rho, 'cases':len(values),
                                'saturated_slower':sum(x>1 for x in ratios),
                                'mean_sat_over_selective':sum(ratios)/len(ratios),
                                'max_sat_over_selective':max(ratios),
                                'different_optimal_epochs':sum(c['saturated-epochs'] != c['selective-epochs'] for c in values),
                                'mean_entry_over_selective':sum(c['entry-greedy']/c['selective'] for c in values)/len(values),
                                'mean_saturated_greedy_over_selective':sum(c['saturated-greedy']/c['selective'] for c in values)/len(values),
                                'mean_singleton_over_selective':sum(c['singleton']/c['selective'] for c in values)/len(values)})
            result[phase]['families'] = summary
            if summary:
                with (RESULTS/'family_summary.csv').open('w',newline='') as f:
                    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    result['complete'] = all(result[p]['completed']==result[p]['expected'] for p in ('exhaustive','weighted','scale'))
    (RESULTS/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    global RESULTS
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seconds',type=float,default=30)
    ap.add_argument('--phase',choices=['all','exhaustive','weighted','scale'],default='all')
    ap.add_argument('--limit',type=int,default=100000,help='maximum new instances this invocation')
    ap.add_argument('--output-dir', type=Path, default=RESULTS,
                    help='result directory; use a new empty directory for a clean reproduction')
    args=ap.parse_args()
    # Only the Linux campaign CLI needs process resource controls. Pure replay,
    # oracle checks and regression imports must not require the resource module.
    try:
        import resource
    except ImportError:
        ap.error('bounded campaign CLI requires Linux resource controls')
    RESULTS=args.output_dir.resolve()
    if not 0 < args.seconds <= 40 or args.limit < 1:
        ap.error('require 0 < seconds <= 40 and a positive instance limit')
    if hasattr(os,'sched_setaffinity'):
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    cap=3*1024**3
    resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
    RESULTS.mkdir(parents=True, exist_ok=True)
    if any(not (ROOT/'inputs'/f'{phase}.jsonl').exists() for phase in ('exhaustive','weighted','scale')):
        ap.error('retained scientific input is missing; run generators.py explicitly to regenerate')
    start=time.monotonic(); count=0
    for phase,func in [('exhaustive',run_exhaustive),('weighted',run_weighted),('scale',run_scale)]:
        if args.phase not in ('all',phase): continue
        path=RESULTS/f'{phase}.jsonl'
        done={json.loads(s)['case'] for s in path.read_text().splitlines()} if path.exists() else set()
        raws=[json.loads(s) for s in (ROOT/'inputs'/f'{phase}.jsonl').read_text().splitlines()]
        with path.open('a') as f:
            for raw in raws:
                if raw['case'] in done: continue
                if time.monotonic()-start >= args.seconds or count>=args.limit: break
                wall=time.monotonic(); cpu=time.process_time()
                row=func(raw)
                row.update(cpu_seconds=time.process_time()-cpu, wall_seconds=time.monotonic()-wall,
                           peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                f.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');f.flush()
                count+=1
    result=summarize()
    print(json.dumps({'status':'COMPLETE' if result['complete'] else 'RESUMABLE',
                      'new_instances':count,'elapsed_seconds':time.monotonic()-start,
                      'progress':{p:result[p]['completed'] for p in ('exhaustive','weighted','scale')}},indent=2))
    return 0

if __name__=='__main__':
    sys.exit(main())
