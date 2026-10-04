"""Validate horizon result structure, exact envelopes and fresh-run agreement.

This checks evidence consistency, not a general mathematical proof. The producer
checks reconstructed schedules through checker.py, which does not import the
horizon or prefix solvers. --against compares a freshly computed run, ignoring
only CPU time and peak RSS; no result is accepted merely because it says PASS.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import json
from pathlib import Path
from horizon import pareto, envelope
from evaluate_horizon import inputs

COUNTS = {'exhaustive': 6912, 'weighted': 240, 'oracle': 48, 'stress': 210}
VOLATILE = {'cpu_seconds', 'reference_cpu_seconds', 'peak_process_rss_kib'}


def scientific(value):
    if isinstance(value, dict):
        return {k: scientific(v) for k, v in value.items() if k not in VOLATILE}
    if isinstance(value, list):
        return [scientific(v) for v in value]
    return value


def engine(record, n):
    if record.get('status') == 'incomplete':
        if not record.get('reason') or 'frontier' in record:
            raise ValueError('incomplete search must give a reason and no optimal frontier')
        return None
    if record.get('status') != 'complete' or not record.get('stats', {}).get('complete'):
        raise ValueError('invalid completion status')
    sp = {int(k): v for k, v in record['frontier'].items()}
    if not sp or any(not 1 <= k <= n or type(v) is not int or v <= 0 for k,v in sp.items()):
        raise ValueError('invalid count/service frontier')
    if pareto(sp) != sp:
        raise ValueError('frontier contains dominated points')
    for field in ('matchings', 'states', 'transitions', 'horizon_candidates', 'labels'):
        if type(record['stats'].get(field)) is not int or record['stats'][field] < 1:
            raise ValueError('invalid search counters')
    return sp


def validate_row(row, raw, phase):
    if row['case'] != raw['case'] or row['tasks'] != len(raw['tasks']):
        raise ValueError('result/input identity mismatch')
    h, p = engine(row['horizon'], row['tasks']), engine(row['prefix'], row['tasks'])
    if h is not None and p is not None:
        if h != p or row.get('agreement') is not True:
            raise ValueError('exact methods disagree')
    elif phase != 'stress' or row.get('agreement') is not None:
        raise ValueError('unexpected incomplete case')
    if 'all_matchings' in row and engine(row['all_matchings'], row['tasks']) != h:
        raise ValueError('maximal matching ablation disagrees')
    if 'policy' in row:
        pol = row['policy']
        if pol['selective_envelope'] != envelope(h):
            raise ValueError('selective envelope does not match frontier')
        sat = {x['epochs']: x['service'] for x in pol['saturated_envelope']}
        if not sat or min(sat) != min(h) or envelope(sat) != pol['saturated_envelope']:
            raise ValueError('saturated envelope/count inconsistency')
        points = {Fraction(0)}
        for e in (pol['selective_envelope'], pol['saturated_envelope']):
            for x in e:
                points.add(Fraction(x['lo']))
                if x['hi'] is not None:
                    points.add(Fraction(x['hi']))
        def cost(s, x):
            return min(b+(k-1)*x for k,b in s.items())
        actual = max(cost(sat,x)/cost(h,x) for x in points)
        if actual != Fraction(pol['max_ratio']) or pol['strict_somewhere'] != (actual > 1):
            raise ValueError('policy price inconsistent with exact envelopes')
        if any(cost(sat,x) < cost(h,x) for x in points):
            raise ValueError('saturation cannot improve on selection')
        if actual > raw['ports']//2:
            raise ValueError('workload bound violated')
    if phase == 'oracle' and row['oracle']['assignments'] != row['tasks']**row['tasks']:
        raise ValueError('incorrect assignment enumeration count')


def verify(directory, against=None):
    output = {}
    for phase, count in COUNTS.items():
        cases = inputs(phase)
        rows = [json.loads(x) for x in (directory/f'{phase}.jsonl').read_text().splitlines()]
        if len(rows) != count or len(cases) != count:
            raise ValueError(f'incomplete campaign phase: {phase}')
        for row, raw in zip(rows,cases):
            validate_row(row,raw,phase)
        if against is not None:
            fresh = [json.loads(x) for x in (against/f'{phase}.jsonl').read_text().splitlines()]
            if len(fresh) != len(rows):
                raise ValueError('fresh run has different record count')
            for old,new in zip(rows,fresh):
                if scientific(old) != scientific(new):
                    raise ValueError(f'fresh scientific evidence differs: {old["case"]}')
        output[phase] = {'records': count, 'validated': True,
                         'fresh_agreement': against is not None}
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory', type=Path)
    ap.add_argument('--against', type=Path)
    args = ap.parse_args()
    try:
        print(json.dumps(verify(args.directory,args.against), indent=2))
    except (ValueError, KeyError, OSError, TypeError) as error:
        ap.exit(2, f'verification failed: {error}\n')

if __name__ == '__main__':
    main()
