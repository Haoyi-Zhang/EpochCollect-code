"""Exact whole-phase deadline queries on a completed service/count frontier.

This is algebra over an already proved exact frontier, not another optimizer.
It does not establish feasibility for per-task deadlines. Fractions describe
setup thresholds; the certificate interpreter continues to require integers
(or an explicit valid common scaling).
"""
from fractions import Fraction
from typing import Mapping


def setup_budget(frontier: Mapping[int, int], deadline: int | Fraction) -> dict:
    """Return the largest uniform setup compatible with a makespan deadline.

    A feasible finite answer includes a terminal (epochs, service) witness.
    Unbounded means a feasible one-epoch schedule. An infeasible result means
    no nonnegative setup meets the deadline on this frontier. Input is an exact
    completed frontier; this function cannot validate its global optimality.
    """
    if not isinstance(frontier, Mapping) or not frontier:
        raise ValueError('a nonempty completed frontier is required')
    if type(deadline) not in (int, Fraction) or deadline < 0:
        raise ValueError('deadline must be a nonnegative integer or Fraction')
    rows = []
    for k, b in frontier.items():
        if type(k) is not int or type(b) is not int or k < 1 or b < 1:
            raise ValueError('epoch counts and total service must be positive integers')
    for k, b in frontier.items():
        if b <= deadline:
            if k == 1:
                return {'feasible': True, 'unbounded': True, 'maximum_setup': None,
                        'epochs': k, 'service': b}
            rows.append((Fraction(deadline-b, k-1), -k, b))
    if not rows:
        return {'feasible': False, 'unbounded': False, 'maximum_setup': None,
                'epochs': None, 'service': None}
    cap, neg_k, b = max(rows)
    return {'feasible': True, 'unbounded': False, 'maximum_setup': cap,
            'epochs': -neg_k, 'service': b}
