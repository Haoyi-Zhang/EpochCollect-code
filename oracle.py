"""Tiny exhaustive epoch-assignment oracle, independent of the ideal-state planner."""
from itertools import product
from checker import checked_input, interpret, is_saturated, matching


def spectra(raw):
    pairs, p, pred = checked_input(raw)
    n = len(pairs)
    if n > 4:
        raise ValueError('brute-force oracle is limited to four tasks')
    output = {'selective': {}, 'saturated': {}}
    count = valid = 0
    for assignment in product(range(n), repeat=n):
        count += 1
        k = max(assignment) + 1
        if set(assignment) != set(range(k)):
            continue
        if any(assignment[u] > assignment[v] for v in range(n) for u in pred[v]):
            continue
        batches = [[v for v in range(n) if assignment[v] == i] for i in range(k)]
        if any(not matching(pairs[v] for v in ids) for ids in batches):
            continue
        done, value, saturated = set(), 0, True
        for ids in batches:
            t, _ = interpret(ids, done, pairs, p, pred)
            value += t
            saturated = saturated and is_saturated(ids, done, pairs, pred)
            done.update(ids)
        valid += 1
        for mode in (['selective', 'saturated'] if saturated else ['selective']):
            old = output[mode].get(k)
            if old is None or value < old:
                output[mode][k] = value
    return output, {'assignments': count, 'valid_assignments': valid}
