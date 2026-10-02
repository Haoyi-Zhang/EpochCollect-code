"""Compare exact scientific outputs, ignoring explicitly measured resource fields.

This is structural comparison, not a hash or toolchain manifest. All retained
certificates are independently interpreted again. No network is used.
"""
import argparse, json
from pathlib import Path
import checker
ROOT = Path(__file__).resolve().parent
MEASURED = {'cpu_seconds', 'wall_seconds', 'peak_rss_kib'}

def scientific(x):
    if isinstance(x, dict):
        return {k: scientific(v) for k, v in x.items() if k not in MEASURED}
    if isinstance(x, list):
        return [scientific(v) for v in x]
    return x

def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines()]

def verify(other):
    total = 0
    for phase, count in [('exhaustive',6912), ('weighted',240), ('scale',80)]:
        actual = rows(other / (phase + '.jsonl'))
        reference = rows(ROOT / 'results' / (phase + '.jsonl'))
        source = rows(ROOT / 'inputs' / (phase + '.jsonl'))
        if len(actual) != count or len(reference) != count:
            raise ValueError('incomplete ' + phase)
        if [x['case'] for x in actual] != [x['case'] for x in source]:
            raise ValueError('input selection or order differs: ' + phase)
        if scientific(actual) != scientific(reference):
            raise ValueError('scientific results differ: ' + phase)
        total += count
    if scientific(json.loads((other/'summary.json').read_text())) != scientific(json.loads((ROOT/'results/summary.json').read_text())):
        raise ValueError('summary differs')
    checked = semantic = 0
    for directory in (ROOT/'results/certificates', other/'certificates'):
        files = sorted(directory.glob('*.json'))
        if len(files) != 320:
            raise ValueError('expected 240 weighted and 80 scale packets')
        for path in files:
            packet = json.loads(path.read_text())
            for c in packet['certificates'].values():
                checker.check(packet['instance'], c)
                result = checker.check_collective(packet['instance'], c)
                semantic += int(result.get('applicable', False)); checked += 1
            peer = (other/'certificates'/path.name) if directory == ROOT/'results/certificates' else (ROOT/'results/certificates'/path.name)
            if packet != json.loads(peer.read_text()):
                raise ValueError('certificate packet differs: ' + path.name)
    return {'status':'EXACT_SCIENTIFIC_MATCH', 'result_rows':total,
            'certificate_interpretations':checked, 'symbolic_interpretations':semantic,
            'resource_measurements_compared':False,
            'meaning':'fresh execution agrees with retained finite results; not a general machine proof'}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('result_directory', type=Path)
    args=ap.parse_args()
    try:
        print(json.dumps(verify(args.result_directory.resolve()), indent=2))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        ap.exit(2, f'rejected: {exc}\n')
if __name__=='__main__': main()
