"""Generate manuscript tables/plot data only from validated retained results."""
from pathlib import Path
import argparse
import csv
import json
from fractions import Fraction
from verify_horizon import verify
from horizon import Horizon, envelope
import generators


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results',type=Path,default=Path(__file__).parent/'results'/'horizon')
    ap.add_argument('--output-dir',type=Path)
    a=ap.parse_args(); verify(a.results)
    out=a.output_dir or a.results;out.mkdir(parents=True,exist_ok=True)
    read=lambda name:[json.loads(x) for x in (a.results/(name+'.jsonl')).read_text().splitlines()]
    w=read('weighted'); stress=read('stress')
    lines=[r'\begin{tabular}{lrrr}',r'\toprule Family & Cases & Strict & Maximum \\',r'\midrule']
    fam=[('allreduce','Allreduce'),('broadcast','Broadcast'),('fork','Gated fork'),
         ('pair-exchange','Pair exchange'),('random-dag','Random DAG'),('total-chain','Total chain'),('unit-fork','Unit fork')]
    for key,label in fam:
        xs=[r for r in w if r['family']==key]; val=max(Fraction(r['policy']['max_ratio']) for r in xs)
        value=str(val.numerator) if val.denominator==1 else f'${val.numerator}/{val.denominator}$'
        lines.append(f'{label} & {len(xs)} & {sum(r["policy"]["strict_somewhere"] for r in xs)} & {value} '+r'\\')
    lines.extend([r'\bottomrule',r'\end{tabular}'])
    (out/'weighted-table.tex').write_text('\n'.join(lines)+'\n')
    both=[r for r in stress if r['horizon']['status']==r['prefix']['status']=='complete']
    with (out/'stress-paired.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['case','tasks','ports','horizon','prefix','ratio','family'])
        for r in both:
            h,p=r['horizon']['stats']['horizon_candidates'],r['prefix']['stats']['horizon_candidates']
            wr.writerow([r['case'],r['tasks'],r['ports'],h,p,p/h,r['family']])
    lines=[r'\begin{tabular}{lrrr}',r'\toprule Set / method & Candidates & States & CPU (s) \\',r'\midrule']
    def add(label,rows,alg):
        candidates=sum(r[alg]['stats']['horizon_candidates'] for r in rows)
        states=sum(r[alg]['stats']['states'] for r in rows)
        cpu=sum(r[alg]['cpu_seconds'] for r in rows)
        lines.append(f'{label} & {candidates:,} & {states:,} & {cpu:.3f} '+r'\\')
    add('Weighted: horizon',w,'horizon');add('Weighted: prefix',w,'prefix');add('Weighted: all matchings',w,'all_matchings')
    lines.append(r'\midrule')
    add('Stress: horizon',both,'horizon');add('Stress: prefix',both,'prefix')
    lines.extend([r'\bottomrule',r'\end{tabular}']);(out/'search-table.tex').write_text('\n'.join(lines)+'\n')
    raws=list(generators.weighted())
    raw=next(r for r in raws if r['family']=='broadcast' and r['shape']=='binary' and r['seed']==0)
    idx=next(i for i,r in enumerate(raws) if r['case']==raw['case']); pol=w[idx]['policy']
    def envcost(rows,rho):
        return min(Fraction(r['service'])+(r['epochs']-1)*rho for r in rows)
    with (out/'broadcast-envelope.dat').open('w') as f:
        f.write('rho selective saturated\n')
        for rho in [Fraction(i,10) for i in range(41)]:
            f.write(f'{float(rho)} {float(envcost(pol["selective_envelope"],rho))} {float(envcost(pol["saturated_envelope"],rho))}\n')
    (out/'broadcast-envelope.json').write_text(json.dumps({'case':raw['case'],'policy':pol},indent=2)+'\n')
    print(json.dumps({'weighted_rows':len(w),'paired_stress_rows':len(both),'broadcast_case':raw['case']}))

if __name__=='__main__':main()
