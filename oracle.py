"""Tiny exhaustive epoch-assignment oracle, independent of the ideal-state planner."""
from itertools import product
from checker import checked_input, interpret, is_saturated, matching


def spectra(raw, max_tasks=4):
    pairs, p, pred = checked_input(raw)
    n = len(pairs)
    if type(max_tasks) is not int or not 1 <= max_tasks <= 6:
        raise ValueError('oracle cap must be an integer in [1,6]')
    if n > max_tasks:
        raise ValueError(f'brute-force oracle is limited to {max_tasks} tasks')
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
