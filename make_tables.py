"""Derive LaTeX tables and figure data from raw finite results; no plotting dependency."""
import argparse,csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output-dir',type=Path,default=ROOT/'results')
    args=ap.parse_args(); out=args.output_dir
    summary=json.loads((out/'summary.json').read_text())
    if not summary['complete']:
        ap.error('the campaign is incomplete')
    names={'allreduce':'Allreduce','broadcast':'Broadcast','fork':'Gated fork',
           'pair-exchange':'Pair exchange','random-dag':'Random DAG','total-chain':'Total chain','unit-fork':'Unit fork'}
    rows=[]
    for x in summary['weighted']['families']:
        if x['rho']==1:
            rows.append(f"{names[x['family']]} & {x['cases']} & {x['saturated_slower']} & "
                        f"{x['mean_sat_over_selective']:.3f} & {x['max_sat_over_selective']:.3f} & "
                        f"{x['different_optimal_epochs']} "+r'\\')
    (out/'family-table.tex').write_text(r'\begin{tabular}{lrrrrr}\toprule'+'\n'+r'Family & Cases & Slower & Mean & Max. & $\Delta K$\\\midrule'+'\n'+'\n'.join(rows)+'\n'+r'\bottomrule\end{tabular}'+'\n')
    rows=[]
    for x in summary['weighted']['families']:
        if x['rho']==1:
            rows.append(f"{names[x['family']]} & {x['mean_entry_over_selective']:.3f} & "
                        f"{x['mean_saturated_greedy_over_selective']:.3f} & "
                        f"{x['mean_singleton_over_selective']:.3f} "+r'\\')
    (out/'baseline-table.tex').write_text(r'\begin{tabular}{lrrr}\toprule'+'\n'+r'Family & Entry & Closed & Singleton\\\midrule'+'\n'+'\n'.join(rows)+'\n'+r'\bottomrule\end{tabular}'+'\n')
    rows=[]
    for x in [json.loads(s) for s in (out/'scale.jsonl').read_text().splitlines()]:
        if x['rho']==1:
            rows.append({'m':x['m'],'L':x['length'],'rho':1,'ratio':x['saturated']/x['selective']})
    with (out/'saturation-price.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['m','L','rho','ratio']);w.writeheader();w.writerows(rows)
    for m in (2,4,8,16,32):
        (out/f'price-m{m}.dat').write_text('L ratio\n'+''.join(f"{r['L']} {r['ratio']:.12g}\n" for r in rows if r['m']==m))
    print('Derived two LaTeX tables and the rho=1 construction plot from raw results.')
if __name__=='__main__': main()
