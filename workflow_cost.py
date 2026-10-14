"""Paired full offline workflow costs on the unchanged 240 weighted inputs.

No hardware service timing, external program, network or new workload is used.
Both methods consume identical serialized inputs and produce the same frontier,
four feasibility/semantic certificates, and whole-phase deadline decision.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import statistics
import time

import checker
from campaign_environment import configure
from horizon import Horizon
from prefix import Prefix
from queries import setup_budget

ROOT = Path(__file__).resolve().parent


def workflow(text, cls):
    start = time.perf_counter_ns()
    cpu_start = time.process_time_ns()
    raw = json.loads(text)
    parsed = time.perf_counter_ns()
    solver = cls(raw)
    frontier = solver.solve()
    solved = time.perf_counter_ns()
    certificates = [solver.schedule(rho) for rho in (0, 1, 4, 16)]
    constructed = time.perf_counter_ns()
    for cert in certificates:
        checker.check(raw, cert)
        checker.check_collective(raw, cert)
    checked = time.perf_counter_ns()
    # JSON round-trip and independent consumer replay are part of both costs.
    wire = json.dumps(certificates, sort_keys=True, separators=(',', ':'))
    consumed = json.loads(wire)
    for cert in consumed:
        checker.check(raw, cert)
        checker.check_collective(raw, cert)
    replayed = time.perf_counter_ns()
    deadline = certificates[1]['makespan'] + 2
    decision = setup_budget(frontier, deadline)
    finished = time.perf_counter_ns()
    return {'case': raw['case'], 'method': cls.__name__, 'family': raw['family'],
            'frontier': frontier, 'certificates': consumed, 'deadline': deadline,
            'decision': {k: str(v) if isinstance(v, Fraction) else v for k, v in decision.items()},
            'timing_ns': {'input_decode': parsed-start, 'initialize_and_solve': solved-parsed,
                          'reconstruct': constructed-solved, 'validate': checked-constructed,
                          'serialize_decode_replay': replayed-checked,
                          'deadline_query': finished-replayed, 'total': finished-start,
                          'cpu_total': time.process_time_ns()-cpu_start},
            'search': dict(solver.stats), 'certificate_wire_bytes': len(wire.encode('utf-8'))}


def compare(a, b):
    fields = ('case', 'frontier', 'deadline', 'decision')
    if any(a[k] != b[k] for k in fields):
        raise ValueError('same-information workflow disagreement')
    if [c['makespan'] for c in a['certificates']] != [c['makespan'] for c in b['certificates']]:
        raise ValueError('equal-guarantee cost mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--portable', action='store_true')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out == ROOT or out == ROOT/'results' or ROOT/'results' in out.parents or (ROOT/'results').is_relative_to(out):
        parser.error('use an isolated output directory')
    if out.exists() and any(out.iterdir()):
        parser.error('output directory must be empty')
    environment, _ = configure(args.portable)
    texts = (ROOT/'inputs/weighted.jsonl').read_text().splitlines()
    if len(texts) != 240:
        raise ValueError('unchanged 240-input domain required')
    out.mkdir(parents=True, exist_ok=True)
    rows, ratios = [], []
    with (out/'raw.jsonl').open('w', encoding='utf-8') as stream:
        for repetition in range(3):
            for index, text in enumerate(texts):
                order = (Horizon, Prefix) if (repetition+index)%2 == 0 else (Prefix, Horizon)
                pair = [workflow(text, cls) for cls in order]
                compare(*pair)
                by_method = {row['method']: row for row in pair}
                ratios.append(by_method['Prefix']['timing_ns']['total'] / by_method['Horizon']['timing_ns']['total'])
                for row in pair:
                    row.update(repetition=repetition, input_sha256=hashlib.sha256(text.encode()).hexdigest())
                    stream.write(json.dumps(row, sort_keys=True, separators=(',', ':'))+'\n')
                    rows.append(row)
    sources = list(ROOT.glob('*.py')) + [ROOT/'inputs/weighted.jsonl']
    summary = {'environment': environment, 'records': len(rows), 'paired_runs': len(ratios),
               'inputs': 240, 'repetitions': 3, 'order': 'alternating per case/repetition; no warmup',
               'agreement': True, 'prefix_over_horizon_total': {'median': statistics.median(ratios),
                           'minimum': min(ratios), 'maximum': max(ratios),
                           'prefix_faster_pairs': sum(x < 1 for x in ratios)},
               'methods': {name: {k: sum(r['timing_ns'][k] for r in rows if r['method'] == name)
                                  for k in rows[0]['timing_ns']} for name in ('Horizon', 'Prefix')},
               'source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
               'scope': 'single-host offline Python end-to-end costs; no collective/device execution, no new input matrix'}
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
