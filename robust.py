"""Exact static minimax planning for a rectangular duration/setup uncertainty set.

No adaptivity is claimed. All tasks and matching batches are fixed before the
realization. Completion, not an elapsed nominal timer, triggers each boundary.
"""
from __future__ import annotations
from copy import deepcopy
from epochs import parse, certificate
from checker import check
from horizon import Horizon, Limits


def plan_box(raw: dict, upper: list[int], rho_upper: int = 0,
             limits: Limits | None = None) -> dict:
    """raw task durations are lower bounds; upper are componentwise upper bounds."""
    _, tasks = parse(raw)
    if type(upper) is not list or len(upper) != len(tasks):
        raise ValueError('one upper duration per task is required')
    if any(type(x) is not int or not t.p <= x <= 10**12 for x,t in zip(upper,tasks)):
        raise ValueError('invalid duration interval')
    if type(rho_upper) is not int or not 0 <= rho_upper <= 10**12:
        raise ValueError('invalid setup upper bound')
    high = deepcopy(raw)
    for t,p in zip(high['tasks'],upper):
        t['p'] = p
    engine = Horizon(high, limits=limits or Limits())
    engine.solve()  # Resource limits raise: a partial plan never claims minimax.
    cert = engine.schedule(rho_upper)
    check(high, cert)
    return {'lower_instance': deepcopy(raw), 'upper': list(upper),
            'rho_upper': rho_upper, 'worst_case_certificate': cert,
            'worst_case_optimum': cert['makespan']}


def replay_box(plan: dict, durations: list[int], rho: int = 0) -> dict:
    """Replay the fixed batches at a specified in-box realization, with validation."""
    raw = deepcopy(plan['lower_instance'])
    upper = plan['upper']
    _, lower_tasks = parse(raw)
    if type(upper) is not list or len(upper) != len(lower_tasks):
        raise ValueError('one upper duration per task is required')
    if any(type(x) is not int or not t.p <= x <= 10**12 for x,t in zip(upper,lower_tasks)):
        raise ValueError('invalid stored duration interval')
    if type(plan['rho_upper']) is not int or not 0 <= plan['rho_upper'] <= 10**12:
        raise ValueError('invalid stored setup bound')
    if type(plan['worst_case_optimum']) is not int or plan['worst_case_optimum'] <= 0:
        raise ValueError('invalid stored worst-case cost')
    if plan['worst_case_certificate'].get('rho') != plan['rho_upper']:
        raise ValueError('certificate setup differs from uncertainty upper bound')
    if type(durations) is not list or len(durations) != len(lower_tasks):
        raise ValueError('one realized duration per task is required')
    if any(type(x) is not int or not t.p <= x <= hi
           for t, x, hi in zip(lower_tasks, durations, upper)):
        raise ValueError('realization outside duration box')
    if type(rho) is not int or not 0 <= rho <= plan['rho_upper']:
        raise ValueError('realization outside setup box')
    high = deepcopy(raw)
    for t,p in zip(high['tasks'],upper):
        t['p'] = p
    check(high, plan['worst_case_certificate'])
    if plan['worst_case_optimum'] != plan['worst_case_certificate']['makespan']:
        raise ValueError('inconsistent worst-case cost')
    for t,p in zip(raw['tasks'],durations):
        t['p'] = p
    _, tasks = parse(raw)
    batches = [sum(1 << v for v in ep['tasks'])
               for ep in plan['worst_case_certificate']['epochs']]
    cert = certificate(tasks,batches,rho)
    check(raw,cert)
    if cert['makespan'] > plan['worst_case_optimum']:
        raise AssertionError('monotone replay bound violated')
    return cert
