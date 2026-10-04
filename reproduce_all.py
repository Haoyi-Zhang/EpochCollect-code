"""Run retained checks, or bounded sequential clean numerical reproduction.

No experiment uses a network connection or external service. CPU/RSS are
measurements and excluded from exact scientific comparisons. This script does
not certify research novelty, publication readiness, or general proof validity.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(command: list[str], log: Path | None = None, timeout: int = 45) -> None:
    print(' '.join(command), flush=True)
    if log is None:
        subprocess.run(command, cwd=ROOT, check=True, timeout=timeout)
    else:
        with log.open('w') as stream:
            subprocess.run(command, cwd=ROOT, check=True, timeout=timeout,
                           stdout=stream, stderr=subprocess.STDOUT)


def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--full', action='store_true', help='also recompute both complete campaigns')
    ap.add_argument('--output-dir', type=Path, default=ROOT/'reproduced')
    ap.add_argument('--seconds', type=int, default=20, choices=range(1,26), metavar='1..25')
    ap.add_argument('--max-chunks', type=int, default=20)
    opts=ap.parse_args()
    if not 1 <= opts.max_chunks <= 100:
        ap.error('--max-chunks must be in 1..100')
    out=opts.output_dir.resolve()
    if opts.full and (out == ROOT or out == ROOT/'results' or ROOT/'results' in out.parents):
        ap.error('fresh output must not overwrite retained evidence')
    py=sys.executable; start=time.monotonic()
    run([py,'-m','unittest','discover','-s','tests','-v'])
    run([py,'verify_results.py','results'])
    run([py,'verify_horizon.py','results/horizon'])
    if not opts.full:
        print(json.dumps({'retained_checks_complete':True,'fresh_execution':False}))
        return
    out.mkdir(parents=True,exist_ok=True); logs=out/'logs'; logs.mkdir(exist_ok=True)
    for name,program in [('base','reproduce.py'),('event','evaluate_horizon.py')]:
        target=out/name
        for number in range(1,opts.max_chunks+1):
            run([py,program,'--output-dir',str(target),'--seconds',str(opts.seconds)],
                logs/f'{name}-{number:03d}.txt')
            summary=json.loads((target/'summary.json').read_text())
            if summary.get('complete') is True:
                break
        else:
            raise RuntimeError(f'{name} campaign incomplete after {opts.max_chunks} chunks; resume explicitly')
    run([py,'verify_results.py',str(out/'base')],logs/'verify-base.txt')
    run([py,'verify_horizon.py',str(out/'event'),'--against','results/horizon'],logs/'verify-event.txt')
    run([py,'make_tables.py','--output-dir',str(out/'base')],logs/'tables-base.txt')
    run([py,'make_horizon_tables.py','--results',str(out/'event')],logs/'tables-event.txt')
    result={'retained_checks_complete':True,'fresh_execution':True,
            'scientific_comparison_complete':True,'elapsed_seconds':time.monotonic()-start,
            'resource_fields_expected_to_vary':True,
            'meaning':'Completed finite reproduction, not a general proof or a venue acceptance assessment.'}
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Reproduction failed: {error}')
