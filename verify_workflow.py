"""Independent consumer/algebra replay of paired workflow evidence, not timing rerun."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import statistics

import checker

ROOT = Path(__file__).resolve().parent


def setup_cap(frontier, deadline):
    if any(k == 1 and b <= deadline for k, b in frontier.items()):
        return None
    values = [Fraction(deadline-b, k-1) for k, b in frontier.items() if k > 1 and b <= deadline]
    if not values:
        raise ValueError('unexpected infeasible deadline')
    return max(values)


def verify(directory, frontiers):
    texts = (ROOT/'inputs/weighted.jsonl').read_text().splitlines()
    inputs = {json.loads(text)['case']: (json.loads(text), hashlib.sha256(text.encode()).hexdigest()) for text in texts}
    reference = {row['case']: row['horizon']['frontier'] for row in
                 (json.loads(text) for text in frontiers.read_text().splitlines())}
    if len(inputs) != 240 or set(reference) != set(inputs):
        raise ValueError('complete unchanged weighted source and fresh reference required')
    rows = [json.loads(text) for text in (directory/'raw.jsonl').read_text().splitlines()]
    expected = {(case, repetition, method) for case in inputs for repetition in range(3) for method in ('Horizon', 'Prefix')}
    by_key, interpreted = {}, 0
    for row in rows:
        key = (row['case'], row['repetition'], row['method'])
        if key not in expected or key in by_key:
            raise ValueError('duplicate or undeclared paired observation')
        by_key[key] = row
        raw, digest = inputs[row['case']]
        if row['input_sha256'] != digest or row['frontier'] != reference[row['case']]:
            raise ValueError('input/frontier correspondence failure')
        sp = {int(k): b for k, b in row['frontier'].items()}
        certs = row['certificates']
        if len(certs) != 4 or [c['rho'] for c in certs] != [0, 1, 4, 16]:
            raise ValueError('four setup obligations required')
        for cert in certs:
            checker.check(raw, cert)
            checker.check_collective(raw, cert)
            if cert['makespan'] != min(b+(k-1)*cert['rho'] for k, b in sp.items()):
                raise ValueError('certificate is not optimal for supplied completed frontier')
            interpreted += 1
        deadline = certs[1]['makespan'] + 2
        if row['deadline'] != deadline:
            raise ValueError('different consumer deadline')
        cap = setup_cap(sp, deadline)
        decision = row['decision']
        if decision.get('feasible') is not True or decision.get('unbounded') is not (cap is None):
            raise ValueError('incorrect deadline decision')
        if cap is not None:
            if Fraction(decision['maximum_setup']) != cap:
                raise ValueError('incorrect maximum setup')
            if decision['service'] + (decision['epochs']-1)*cap != deadline:
                raise ValueError('deadline witness fails exact algebra')
        timing = row['timing_ns']
        parts = ('input_decode', 'initialize_and_solve', 'reconstruct', 'validate', 'serialize_decode_replay', 'deadline_query')
        if any(type(timing[k]) is not int or timing[k] < 0 for k in (*parts, 'total', 'cpu_total')) or sum(timing[k] for k in parts) != timing['total']:
            raise ValueError('invalid cost partition')
    if set(by_key) != expected:
        raise ValueError('incomplete paired workflow')
    ratios = [by_key[case, repetition, 'Prefix']['timing_ns']['total'] /
              by_key[case, repetition, 'Horizon']['timing_ns']['total']
              for repetition in range(3) for case in inputs]
    summary = json.loads((directory/'summary.json').read_text())
    actual = {'median': statistics.median(ratios), 'minimum': min(ratios), 'maximum': max(ratios),
              'prefix_faster_pairs': sum(x < 1 for x in ratios)}
    if actual != summary['prefix_over_horizon_total']:
        raise ValueError('summary ratio mismatch')
    for name, counts in summary['methods'].items():
        if any(sum(r['timing_ns'][k] for r in rows if r['method'] == name) != value for k, value in counts.items()):
            raise ValueError('summary stage-total mismatch')
    source_matches = all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest for name, digest in summary['source_sha256'].items())
    return {'records': len(rows), 'certificate_interpretations': interpreted,
            'independent_deadline_algebra': True, 'fresh_frontier_correspondence': True,
            'stored_source_hashes_match_current': source_matches,
            'timings_remeasured': False, 'scope': 'offline evidence replay; no device or proof-assistant validation'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--frontiers', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, args.frontiers), indent=2))
