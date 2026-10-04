"""Reproduce the completion-horizon extension, in resumable bounded chunks.

All input rules are fixed in stress_cases()/oracle_cases(), not selected by
results. Completed searches are checked; resource-limited searches remain
explicitly incomplete. No network, optional package, GPU or subprocess is used.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from fractions import Fraction
import json
import os
from pathlib import Path
import random
import resource
import time
import checker
import epochs
import generators
import oracle
from horizon import Horizon, Limits, SearchLimit, pareto, envelope, normalize
from prefix import Prefix

ROOT = Path(__file__).resolve().parent
SMALL = Limits(seconds=30, states=50000, transitions=5000000, matchings=100000)
STRESS = Limits(seconds=3, states=5000, transitions=200000, matchings=5000)


def random_dag(ports, count, density, seed):
    rng = random.Random(seed)
    return {'ports': ports, 'family': 'random-dag', 'seed': seed, 'density': density,
            'tasks': [{'pair': sorted(rng.sample(range(ports), 2)),
                       'p': rng.choice([1, 2, 4, 8]),
                       'pred': [j for j in range(i) if rng.random() < density]}
                      for i in range(count)]}


def stress_cases():
    i = 0
    for kind in ('broadcast', 'allreduce'):
        for ports in (4, 7):
            for shape in ('binary', 'path', 'star'):
                for chunks in (1, 2, 4, 8, 16):
                    for seed in (101, 103):
                        raw = generators.tree_case(ports, chunks, shape, seed, kind)
                        raw['case'] = f'stress{i:04d}'
                        i += 1
                        yield raw
    for ports in (4, 6, 8):
        for count in (8, 12, 16, 24, 32):
            for density in (0, 0.15, 0.5):
                for seed in (101, 103):
                    raw = random_dag(ports, count, density, seed)
                    raw['case'] = f'stress{i:04d}'
                    i += 1
                    yield raw


def oracle_cases():
    for count in (5, 6):
        for seed in range(700, 724):
            raw = random_dag(6, count, 0.2, seed)
            raw['case'] = f'oracle{count}-{seed}'
            yield raw


def cost(spec, rho):
    return min(Fraction(b) + (int(k)-1)*rho for k, b in spec.items())


def compare_policies(sel, sat):
    """Exact supremum ratio over all rho>=0, from affine interval endpoints."""
    es, ea = envelope(sel), envelope(sat)
    points = {Fraction(0)}
    for row in es+ea:
        points.add(Fraction(row['lo']))
        if row['hi'] is not None:
            points.add(Fraction(row['hi']))
    ratios = [(cost(sat, x)/cost(sel, x), x) for x in points]
    ratio, where = max(ratios, key=lambda z: (z[0], -z[1]))
    assert ratio >= 1 and min(sel) == min(sat)
    # With a positive minimum slope both policies have the same asymptotic
    # slope. A zero slope means a one-epoch optimum, common to both policies.
    tail = Fraction(1)
    if min(sel) == 1:
        tail = Fraction(sat[1], sel[1])
        assert tail == 1
    return {'strict_somewhere': ratio > 1, 'max_ratio': str(max(ratio, tail)),
            'max_at_rho': str(where), 'selective_envelope': es,
            'saturated_envelope': ea, 'breakpoints_checked': len(points)}


def run_engine(raw, cls, limits=SMALL, all_matchings=False):
    begin = time.process_time()
    engine = None
    try:
        engine = cls(raw, limits=limits, use_maximal=not all_matchings)
        frontier = engine.solve()
    except (SearchLimit, MemoryError) as error:
        return {'status': 'incomplete', 'reason': str(error) or 'memory limit',
                'cpu_seconds': time.process_time()-begin,
                'stats': dict(engine.stats) if engine is not None else None}
    measured = time.process_time()-begin
    checks = 0
    for rho in (0, 1, 4, 16):
        cert = engine.schedule(rho)
        checker.check(raw, cert)
        checks += int(checker.check_collective(raw, cert).get('applicable', False))
    return {'status': 'complete', 'frontier': frontier, 'cpu_seconds': measured,
            'stats': dict(engine.stats), 'symbolic_checks': checks}


def run_reference(raw):
    begin = time.process_time()
    engine = epochs.Exact(raw)
    full = engine.solve()
    reference_time = time.process_time()-begin
    expected = pareto(full['selective'])
    h = run_engine(raw, Horizon)
    p = run_engine(raw, Prefix)
    assert h['status'] == p['status'] == 'complete', raw['case']
    assert h['frontier'] == p['frontier'] == expected, raw['case']
    cert = engine.schedule(1, 'selective')
    normalized = normalize(raw, cert)
    assert normalized['makespan'] <= cert['makespan']
    result = {'case': raw['case'], 'family': raw['family'], 'tasks': len(raw['tasks']),
              'ports': raw['ports'], 'agreement': True, 'reference_cpu_seconds': reference_time,
              'horizon': h, 'prefix': p,
              'policy': compare_policies(full['selective'], full['saturated'])}
    if raw['case'].startswith('weighted'):
        a = run_engine(raw, Horizon, all_matchings=True)
        assert a['status'] == 'complete' and a['frontier'] == expected
        result['all_matchings'] = a
    return result


def run_oracle(raw):
    full, counts = oracle.spectra(raw, max_tasks=6)
    h = run_engine(raw, Horizon)
    p = run_engine(raw, Prefix)
    assert h['status'] == p['status'] == 'complete'
    assert h['frontier'] == p['frontier'] == pareto(full['selective'])
    return {'case': raw['case'], 'tasks': len(raw['tasks']), 'agreement': True,
            'oracle': counts, 'horizon': h, 'prefix': p}


def run_stress(raw):
    h = run_engine(raw, Horizon, STRESS)
    p = run_engine(raw, Prefix, STRESS)
    agree = None
    if h['status'] == p['status'] == 'complete':
        assert h['frontier'] == p['frontier'], raw['case']
        agree = True
    return {'case': raw['case'], 'family': raw['family'], 'shape': raw.get('shape'),
            'ports': raw['ports'], 'chunks': raw.get('chunks'), 'density': raw.get('density'),
            'tasks': len(raw['tasks']), 'horizon': h, 'prefix': p, 'agreement': agree}


def exact_json(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'))


def inputs(name):
    funcs = {'exhaustive': generators.exhaustive, 'weighted': generators.weighted,
             'oracle': oracle_cases, 'stress': stress_cases}
    cases = list(funcs[name]())
    target = ROOT/'inputs'/f'horizon-{name}.jsonl'
    text = ''.join(exact_json(r)+'\n' for r in cases)
    if target.exists():
        if target.read_text() != text:
            raise ValueError(f'frozen input differs from deterministic generator: {target}')
    else:
        target.write_text(text)
    return cases


def summarize(out):
    summary = {}
    for name, expected in [('exhaustive', 6912), ('weighted', 240), ('oracle', 48), ('stress', 210)]:
        path = out/f'{name}.jsonl'
        rows = [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
        part = {'records': len(rows), 'expected': expected,
                'cpu_seconds': sum(r['cpu_seconds'] for r in rows)}
        if rows:
            for alg in ('horizon', 'prefix'):
                completed = [r for r in rows if r[alg]['status']=='complete']
                part[alg] = {'completed': len(completed), 'incomplete': len(rows)-len(completed),
                    'cpu_seconds': sum(r[alg]['cpu_seconds'] for r in rows),
                    'raw_candidates_completed': sum(r[alg]['stats']['horizon_candidates'] for r in completed),
                    'states_completed': sum(r[alg]['stats']['states'] for r in completed)}
            if 'policy' in rows[0]:
                part['strict_somewhere'] = sum(r['policy']['strict_somewhere'] for r in rows)
                part['max_ratio'] = str(max(Fraction(r['policy']['max_ratio']) for r in rows))
                families = {}
                for fam in sorted({r['family'] for r in rows}):
                    xs = [r for r in rows if r['family']==fam]
                    families[fam] = {'cases': len(xs), 'strict_somewhere': sum(r['policy']['strict_somewhere'] for r in xs),
                                    'max_ratio': str(max(Fraction(r['policy']['max_ratio']) for r in xs))}
                part['families'] = families
            if name=='oracle':
                part['assignments'] = sum(r['oracle']['assignments'] for r in rows)
            if name=='stress':
                both = [r for r in rows if r['horizon']['status']==r['prefix']['status']=='complete']
                part['jointly_completed'] = len(both)
                part['horizon_only'] = sum(r['horizon']['status']=='complete' and r['prefix']['status']!='complete' for r in rows)
                part['prefix_only'] = sum(r['prefix']['status']=='complete' and r['horizon']['status']!='complete' for r in rows)
                part['both_incomplete'] = sum(r['prefix']['status']!='complete' and r['horizon']['status']!='complete' for r in rows)
        summary[name] = part
    summary['complete'] = all(s['records']==s['expected'] for s in summary.values() if isinstance(s,dict))
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output-dir', type=Path, default=ROOT/'results'/'horizon')
    ap.add_argument('--phase', choices=['all','exhaustive','weighted','oracle','stress'], default='all')
    ap.add_argument('--seconds', type=float, default=20)
    ap.add_argument('--limit', type=int, default=100000)
    args = ap.parse_args()
    if not 0 < args.seconds <= 30 or args.limit < 1:
        ap.error('require seconds in (0,30], limit>=1')
    if hasattr(os, 'sched_setaffinity'):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS, (3*1024**3, 3*1024**3))
    out = args.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    start = time.monotonic(); processed = 0
    phases = ['exhaustive','weighted','oracle','stress'] if args.phase=='all' else [args.phase]
    for name in phases:
        cases = inputs(name)
        path = out/f'{name}.jsonl'
        old = [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
        if [r['case'] for r in old] != [r['case'] for r in cases[:len(old)]]:
            raise ValueError('result prefix does not match declared input order')
        for raw in cases[len(old):]:
            if time.monotonic()-start > args.seconds or processed >= args.limit:
                print(json.dumps({'status': 'RESUME', 'summary': summarize(out)})); return
            cpu = time.process_time()
            row = run_reference(raw) if name in ('exhaustive','weighted') else run_oracle(raw) if name=='oracle' else run_stress(raw)
            row['cpu_seconds'] = time.process_time()-cpu
            row['peak_process_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            with path.open('a') as f:
                f.write(exact_json(row)+'\n'); f.flush()
            processed += 1
    summary = summarize(out)
    print(json.dumps({'status': 'COMPLETE' if summary['complete'] else 'PHASE_COMPLETE', 'summary': summary}))

if __name__=='__main__':
    main()
