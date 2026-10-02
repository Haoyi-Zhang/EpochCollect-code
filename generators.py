"""Frozen, deterministic synthetic input families. No downloaded traces."""
import itertools
import json
import random
from pathlib import Path


def fork(m, length, unit=False):
    ts = []
    prev = None
    for i in range(m):
        a = len(ts)
        ts.append({'pair': [2*i, 2*i+1], 'p': 1, 'pred': [] if prev is None else [prev]})
        leafpred = a
        for _ in range(length if unit else 1):
            v = len(ts)
            ts.append({'pair': [2*i, 2*i+1], 'p': 1 if unit else length, 'pred': [leafpred]})
            leafpred = v
        if i < m - 1:
            prev = len(ts)
            ts.append({'pair': [2*i+1, 2*i+2], 'p': 1, 'pred': [a]})
    return {'ports': 2*m, 'tasks': ts, 'family': 'unit-fork' if unit else 'fork', 'm': m, 'length': length}


def exhaustive():
    number = 0
    for n, alphabet, durations in [(3, list(itertools.combinations(range(4), 2)), [1, 2, 3]),
                                     (4, [(0, 1), (1, 2), (2, 3)], [1, 3, 2, 4])]:
        edges = list(itertools.combinations(range(n), 2))
        for pairs in itertools.product(alphabet, repeat=n):
            for mask in range(1 << len(edges)):
                ts = [{'pair': list(pairs[i]), 'p': durations[i],
                       'pred': [u for j, (u, v) in enumerate(edges) if v == i and mask >> j & 1]}
                      for i in range(n)]
                yield {'case': f'case{number:06d}', 'family': f'enumerated-{n}', 'ports': 4, 'tasks': ts}
                number += 1


def tree_case(ports, chunks, shape, seed, kind):
    rng = random.Random(seed)
    parent = {v: ((v-1)//2 if shape == 'binary' else v-1 if shape == 'path' else 0)
              for v in range(1, ports)}
    children = {v: [u for u in range(1, ports) if parent[u] == v] for v in range(ports)}
    subtree = {}
    for v in reversed(range(ports)):
        subtree[v] = (1 << v) | sum(subtree[u] for u in children[v])
    ts = []
    for c in range(chunks):
        reduction, broadcast = {}, {}
        if kind == 'allreduce':
            for v in reversed(range(1, ports)):
                reduction[v] = len(ts)
                ts.append({'pair': [v, parent[v]], 'p': rng.choice([1, 2, 4, 8]),
                           'pred': [reduction[u] for u in children[v]],
                           'chunk': c, 'src': v, 'dst': parent[v], 'phase': 'reduce', 'value': subtree[v]})
        for v in range(1, ports):
            p = parent[v]
            deps = ([broadcast[p]] if p != 0 else
                    [reduction[u] for u in children[0]] if kind == 'allreduce' else [])
            broadcast[v] = len(ts)
            ts.append({'pair': [p, v], 'p': rng.choice([1, 2, 4, 8]), 'pred': deps,
                       'chunk': c, 'src': p, 'dst': v, 'phase': 'broadcast',
                       'value': (1 << ports)-1 if kind == 'allreduce' else 1})
    return {'ports': ports, 'tasks': ts, 'family': kind, 'semantics': kind,
            'chunks': chunks, 'shape': shape, 'seed': seed}


def weighted():
    cases = []
    for shape in ['binary', 'path', 'star']:
        for chunks in [1, 2]:
            for seed in range(20):
                cases.append(tree_case(4, chunks, shape, seed, 'allreduce'))
        for seed in range(10):
            cases.append(tree_case(7, 2, shape, seed, 'broadcast'))
    for seed in range(20):
        rng = random.Random(seed)
        ts = [{'pair': list(pair), 'p': rng.choice([1, 2, 4, 8]), 'pred': []}
              for _ in range(2) for pair in itertools.combinations(range(4), 2)]
        cases.append({'ports': 4, 'tasks': ts, 'family': 'pair-exchange', 'seed': seed})
    for n in [8, 12]:
        for seed in range(20):
            rng = random.Random(seed)
            ts = [{'pair': sorted(rng.sample(range(6), 2)), 'p': rng.choice([1, 2, 4, 8]),
                   'pred': [j for j in range(i) if rng.random() < 0.18]} for i in range(n)]
            cases.append({'ports': 6, 'tasks': ts, 'family': 'random-dag', 'seed': seed})
    for seed in range(10):
        rng = random.Random(seed)
        ts = [{'pair': sorted(rng.sample(range(6), 2)), 'p': rng.choice([1, 2, 4, 8]),
               'pred': [] if i == 0 else [i-1]} for i in range(12)]
        cases.append({'ports': 6, 'tasks': ts, 'family': 'total-chain', 'seed': seed})
    for m in [1, 2, 3, 4, 5]:
        for length in [1, 7, 31]:
            cases.append(fork(m, length))
    for m, length in [(2, 2), (3, 2), (4, 2), (2, 3), (3, 3)]:
        cases.append(fork(m, length, unit=True))
    for i, case in enumerate(cases):
        case['case'] = f'weighted{i:04d}'
        yield case


def scale_cases():
    i = 0
    for m in (2, 4, 8, 16, 32):
        for length in (1, 8, 64, 512):
            for rho in (0, 1, 8, 64):
                raw = fork(m, length)
                raw.update(case=f'scale{i:04d}', rho=rho)
                i += 1
                yield raw


def main():
    root = Path(__file__).resolve().parent / 'inputs'
    root.mkdir(exist_ok=True)
    for name, cases in [('exhaustive', exhaustive()), ('weighted', weighted()), ('scale', scale_cases())]:
        text = ''.join(json.dumps(c, sort_keys=True, separators=(',', ':')) + '\n' for c in cases)
        (root / f'{name}.jsonl').write_text(text)
    sample = fork(3, 7)
    sample['case'] = 'example'
    (root / 'example.json').write_text(json.dumps(sample, indent=2) + '\n')

if __name__ == '__main__':
    main()
