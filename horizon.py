"""Time-preserving horizon admission for drained, fixed-FIFO circuit epochs.

Exact mode enumerates maximal installed matchings, not arbitrary task subsets.
The returned spectrum is the nondominated (epoch count, service) frontier;
it is NOT an exact-count spectrum. Resource limits raise SearchLimit: no
partial search is reported as optimal. Only Python's standard library is used.
"""
from __future__ import annotations
import argparse
import heapq
import json
import math
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable
from epochs import Task, parse, bits, certificate, integer


class SearchLimit(RuntimeError):
    """Exhaustive search did not finish within the declared resource bound."""


def maximal_matchings(pairs: Iterable[tuple[int, int]], limit: int = 100000, deadline: float | None = None):
    """Enumerate maximal cliques of the pair-compatibility graph.

    This is a standard pivoted Bron--Kerbosch enumeration, not a novelty claim.
    Pair tuples are normalized by parse(). Matchings may contain idle pairs.
    """
    pairs = tuple(sorted(set(pairs)))
    if not pairs:
        return (frozenset(),)
    adjacency = []
    for i, q in enumerate(pairs):
        adjacency.append(sum(1 << j for j, r in enumerate(pairs)
                             if i != j and not (set(q) & set(r))))
    out = []

    def visit(chosen: int, pending: int, excluded: int):
        if deadline is not None and time.monotonic() > deadline:
            raise SearchLimit("matching-enumeration wall-time limit")
        if not pending and not excluded:
            out.append(frozenset(pairs[i] for i in bits(chosen)))
            if len(out) > limit:
                raise SearchLimit(f'more than {limit} maximal matchings')
            return
        union = pending | excluded
        pivot = max(bits(union), key=lambda i: ((pending & adjacency[i]).bit_count(), -i))
        candidates = pending & ~adjacency[pivot]
        for v in list(bits(candidates)):
            b = 1 << v
            visit(chosen | b, pending & adjacency[v], excluded & adjacency[v])
            pending &= ~b
            excluded |= b
    visit(0, (1 << len(pairs)) - 1, 0)
    return tuple(sorted(out, key=lambda x: tuple(sorted(x))))


def pareto(spectrum: dict[int, int]) -> dict[int, int]:
    """Remove points dominated simultaneously in count and service."""
    out = {}
    best = None
    for k, value in sorted(spectrum.items()):
        if best is None or value < best:
            out[k] = value
            best = value
    return out


@dataclass(frozen=True)
class Limits:
    seconds: float = 30.0
    states: int = 50000
    transitions: int = 5000000
    matchings: int = 100000
    tasks: int = 512


class Horizon:
    """Exact dynamic program on reachable ideals and horizon-complete batches."""
    def __init__(self, raw: dict, limits: Limits | None = None,
                 use_maximal: bool = True):
        self.raw = raw
        self.ports, self.tasks = parse(raw)
        self.limits = limits or Limits()
        if not math.isfinite(self.limits.seconds) or self.limits.seconds <= 0 or any(type(v) is not int or v < 1 for v in
                (self.limits.states, self.limits.transitions, self.limits.matchings, self.limits.tasks)):
            raise ValueError('search limits must be positive')
        if len(self.tasks) > self.limits.tasks:
            raise SearchLimit(f'task count exceeds {self.limits.tasks}')
        self.n = len(self.tasks)
        self.full = (1 << self.n) - 1
        self.pred = tuple(sum(1 << d for d in t.pred) for t in self.tasks)
        self.start_time = time.monotonic()
        pairs = tuple(sorted(set(t.pair for t in self.tasks)))
        if use_maximal:
            self.matchings = maximal_matchings(pairs, self.limits.matchings,
                                               self.start_time + self.limits.seconds)
        else:
            # Ablation only: explicitly enumerate every nonempty matching.
            matches = [frozenset()]
            for pair in pairs:
                if time.monotonic() - self.start_time > self.limits.seconds:
                    raise SearchLimit('all-matching enumeration wall-time limit')
                matches += [m | {pair} for m in matches
                            if all(not set(pair) & set(q) for q in m)]
                if len(matches) > self.limits.matchings + 1:
                    raise SearchLimit('all-matching enumeration limit')
            self.matchings = tuple(m for m in matches if m)
        self.initialization_seconds = time.monotonic() - self.start_time
        self.stats = {'tasks': self.n, 'matchings': len(self.matchings),
                      'states': 0, 'transitions': 0, 'horizon_candidates': 0,
                      'labels': 0, 'complete': False, 'one_matching_fastpath': False}
        self.dp: dict[int, dict[int, int]] = {}
        self.parents: dict[tuple[int, int], tuple[int, int]] = {}
        self.frontier: dict[int, int] = {}

    def completion_times(self, done: int, matching: frozenset) -> list[int | None]:
        """ASAP completion on a fixed matching. None denotes unreachable.

        The timetable describes unrestricted recursive execution but admission
        subsequently uses ONLY tasks completing by the selected horizon.
        A task that merely starts before the horizon is not admitted.
        """
        finish: list[int | None] = [None] * self.n
        for v, t in enumerate(self.tasks):
            if done >> v & 1:
                finish[v] = 0
            elif t.pair in matching:
                ds = [finish[d] for d in t.pred]
                if all(x is not None for x in ds):
                    finish[v] = t.p + max(ds, default=0)
        return finish

    def transitions(self, done: int):
        """Distinct destinations and their exact service; at most N per M."""
        arcs: dict[int, int] = {}
        for i, matching in enumerate(self.matchings):
            if i % 128 == 0 and time.monotonic() - self.start_time > self.limits.seconds:
                raise SearchLimit('wall-time limit')
            finish = self.completion_times(done, matching)
            events: dict[int, int] = {}
            for v, t in enumerate(finish):
                if t is not None and t > 0:
                    events[t] = events.get(t, 0) | (1 << v)
            reached = done
            for t, added in sorted(events.items()):
                reached |= added
                self.stats['horizon_candidates'] += 1
                if self.stats['horizon_candidates'] > self.limits.transitions:
                    raise SearchLimit('horizon-candidate limit')
                if reached in arcs and arcs[reached] != t:
                    raise AssertionError('a fixed admitted set has inconsistent duration')
                arcs[reached] = t
        return arcs

    def solve(self) -> dict[int, int]:
        # Every successor mask is numerically larger: the heap is a topological
        # order and all predecessor labels are final before a state is expanded.
        self.start_time = time.monotonic() - self.initialization_seconds
        self.stats.update(states=0, transitions=0, horizon_candidates=0, labels=0, complete=False, one_matching_fastpath=False)
        self.dp, self.parents, self.frontier = {}, {}, {}
        # Common exact lower-bound fast path, also used by Prefix below. When
        # every used pair is disjoint, the global weighted critical path is both
        # attainable in one epoch and a lower bound for every schedule.
        if len(self.matchings) == 1 and len(self.matchings[0]) == len(set(t.pair for t in self.tasks)):
            if self.limits.states < 2:
                raise SearchLimit('state limit')
            value = max(t for t in self.completion_times(0, self.matchings[0]) if t is not None)
            self.dp = {0: {0: 0}, self.full: {1: value}}
            self.parents = {(self.full, 1): (0, 0)}
            self.frontier = {1: value}
            self.stats.update(states=2, transitions=1, horizon_candidates=1, labels=2,
                              complete=True, one_matching_fastpath=True)
            return dict(self.frontier)
        dp: dict[int, dict[int, int]] = {0: {0: 0}}
        parents = {}
        pending = [0]
        popped = 0
        while pending:
            if time.monotonic() - self.start_time > self.limits.seconds:
                raise SearchLimit('wall-time limit')
            done = heapq.heappop(pending)
            popped += 1
            values = dp[done] = pareto(dp[done])
            if done == self.full:
                continue
            for reached, duration in self.transitions(done).items():
                self.stats['transitions'] += 1
                if self.stats['transitions'] > self.limits.transitions:
                    raise SearchLimit('transition limit')
                if reached not in dp:
                    if len(dp) >= self.limits.states:
                        raise SearchLimit('state limit')
                    dp[reached] = {}
                    heapq.heappush(pending, reached)
                for k, value in values.items():
                    candidate = value + duration
                    old = dp[reached].get(k + 1)
                    if old is None or candidate < old:
                        dp[reached][k + 1] = candidate
                        parents[reached, k + 1] = (done, k)
        self.dp, self.parents = dp, parents
        self.frontier = pareto(dp[self.full])
        self.stats.update(states=popped, labels=sum(map(len, dp.values())), complete=True)
        return dict(self.frontier)

    def schedule(self, rho: int) -> dict:
        integer(rho, 'rho', 0, 10**12)
        if not self.stats['complete']:
            self.solve()
        k = min(self.frontier, key=lambda k: (self.frontier[k] + (k - 1) * rho, k))
        masks, done, count = [], self.full, k
        while done:
            previous, previous_count = self.parents[done, count]
            masks.append(done ^ previous)
            done, count = previous, previous_count
        return certificate(self.tasks, list(reversed(masks)), rho, 'selective')


def normalize(raw: dict, cert: dict) -> dict:
    """Normalize any checked schedule without increasing count or service.

    Uses its own supports, so normalization itself needs no matching enumeration.
    The theorem additionally permits extending supports to maximal matchings.
    """
    import checker
    checker.check(raw, cert)
    _, tasks = parse(raw)
    done, masks = 0, []
    for ep in cert['epochs']:
        matching = frozenset(tasks[v].pair for v in ep['tasks'])
        finish: list[int | None] = [None] * len(tasks)
        for v, task in enumerate(tasks):
            if done >> v & 1:
                finish[v] = 0
            elif task.pair in matching:
                pred_times = [finish[u] for u in task.pred]
                if all(t is not None for t in pred_times):
                    finish[v] = task.p + max(pred_times, default=0)
        horizon = ep['end'] - ep['start']
        extra = sum(1 << v for v, t in enumerate(finish) if t is not None and 0 < t <= horizon)
        if extra:
            masks.append(extra)
            done |= extra
    if done != (1 << len(tasks)) - 1:
        raise AssertionError('normalization failed to cover every task')
    out = certificate(tasks, masks, cert['rho'], 'selective')
    checker.check(raw, out)
    if len(out['epochs']) > len(cert['epochs']) or out['makespan'] > cert['makespan']:
        raise AssertionError('time-preserving normalization failed')
    old_finish = {e['task']:e['finish'] for ep in cert['epochs'] for e in ep['events']}
    new_finish = {e['task']:e['finish'] for ep in out['epochs'] for e in ep['events']}
    if any(new_finish[v] > old_finish[v] for v in old_finish):
        raise AssertionError('taskwise completion dominance failed')
    return out


def envelope(spectrum: dict[int, int]) -> list[dict]:
    """Exact lower envelope on rho >= 0 with smaller-count tie breaking.

    Pairwise rational intersections provide an intentionally simple reference
    computation. Nondominated count labels number at most N.
    """
    items = sorted(pareto({int(k): v for k, v in spectrum.items()}).items())
    if not items:
        raise ValueError('empty spectrum')
    points = {Fraction(0)}
    for i, (k, b) in enumerate(items):
        for l, a in items[i + 1:]:
            x = Fraction(b - a, l - k)
            if x > 0:
                points.add(x)
    points = sorted(points)
    out = []
    for i, lo in enumerate(points):
        hi = points[i + 1] if i + 1 < len(points) else None
        mid = (lo + hi) / 2 if hi is not None else lo + 1
        k, b = min(items, key=lambda kb: (kb[1] + (kb[0] - 1) * mid, kb[0]))
        row = {'lo': str(lo), 'hi': str(hi) if hi is not None else None,
               'epochs': k, 'service': b}
        if out and out[-1]['epochs'] == k:
            out[-1]['hi'] = row['hi']
        else:
            out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('instance', type=Path)
    ap.add_argument('--rho', type=int, default=1)
    ap.add_argument('--seconds', type=float, default=30)
    ap.add_argument('--states', type=int, default=50000)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if not 0 < args.seconds <= 40 or not 1 <= args.states <= 200000:
        ap.error('require 0 < seconds <= 40 and 1 <= states <= 200000')
    try:
        raw = json.loads(args.instance.read_text())
        solver = Horizon(raw, Limits(seconds=args.seconds, states=args.states))
        frontier = solver.solve()
        packet = {'instance': raw, 'frontier': frontier, 'envelope': envelope(frontier),
                  'certificate': solver.schedule(args.rho), 'search': solver.stats}
        import checker
        checker.check(raw, packet['certificate'])
        args.output.write_text(json.dumps(packet, indent=2) + '\n')
    except (ValueError, TypeError, KeyError, OSError, SearchLimit) as exc:
        ap.exit(2, f'not completed: {exc}\n')

if __name__ == '__main__':
    main()
