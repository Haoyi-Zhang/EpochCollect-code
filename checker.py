"""Independent schedule validator and event interpreter; no planner imports."""
from __future__ import annotations
import argparse
import heapq
import json
from pathlib import Path


def checked_input(raw):
    if type(raw) is not dict or type(raw.get('ports')) is not int or not 2 <= raw['ports'] <= 10000:
        raise ValueError('invalid port count')
    data = raw.get('tasks')
    if type(data) is not list or not 1 <= len(data) <= 10000:
        raise ValueError('invalid task count')
    ps, duration, pred = [], [], []
    last = {}
    for i, x in enumerate(data):
        if type(x) is not dict or type(x.get('pair')) not in (list, tuple) or len(x['pair']) != 2:
            raise ValueError('invalid pair')
        if any(type(y) is not int or not 0 <= y < raw['ports'] for y in x['pair']):
            raise ValueError('invalid endpoints')
        p = tuple(sorted(x['pair']))
        if p[0] == p[1]:
            raise ValueError('invalid endpoints')
        if type(x.get('p')) is not int or not 1 <= x['p'] <= 10**12:
            raise ValueError('invalid duration')
        deps = x.get('pred', [])
        if type(deps) is not list or any(type(d) is not int or not 0 <= d < i for d in deps):
            raise ValueError('not topologically indexed')
        # Checker-local queue construction, independent of every planner.
        pred.append(set(deps) | ({last[p]} if p in last else set()))
        last[p] = i
        ps.append(p)
        duration.append(x['p'])
    return ps, duration, pred


def matching(pairs):
    seen = set()
    for pair in set(pairs):
        if seen.intersection(pair):
            return False
        seen.update(pair)
    return True


def interpret(ids, done, pairs, duration, pred):
    """Event-driven execution, different from the planner's weighted-path recurrence."""
    ids = set(ids)
    if not ids or not matching(pairs[v] for v in ids):
        raise ValueError('empty or incompatible batch')
    if any(not pred[v] <= done | ids for v in ids):
        raise ValueError('future predecessor')
    complete = set(done)
    waiting = set(ids)
    running = []
    events = []
    now = 0
    while waiting or running:
        ready = sorted(v for v in waiting if pred[v] <= complete)
        for v in ready:
            waiting.remove(v)
            heapq.heappush(running, (now + duration[v], v))
            events.append((v, now, now + duration[v]))
        if not running:
            raise ValueError('deadlocked admitted batch')
        now = running[0][0]
        while running and running[0][0] == now:
            _, v = heapq.heappop(running)
            complete.add(v)
    return now, events


def is_saturated(ids, done, pairs, pred):
    allowed = set(pairs[v] for v in ids)
    reached = set(done)
    while True:
        next_set = reached | {v for v in range(len(pairs)) if pairs[v] in allowed and pred[v] <= reached}
        if next_set == reached:
            return reached == done | set(ids)
        reached = next_set


def _check_endpoint_intervals(pairs, eventmap):
    """Direct half-open overlap check on validated task pairs and intervals."""
    by_port = {}
    for v, pair in enumerate(pairs):
        for port in pair:
            by_port.setdefault(port, []).append(eventmap[v])
    for intervals in by_port.values():
        intervals = sorted(intervals)
        if any(b > c for (_, b), (c, _) in zip(intervals, intervals[1:])):
            raise ValueError('endpoint service overlap')


def check(raw, cert):
    pairs, duration, pred = checked_input(raw)
    n = len(pairs)
    if type(cert) is not dict or type(cert.get('rho')) is not int or not 0 <= cert['rho'] <= 10**12:
        raise ValueError('invalid setup cost')
    epochs = cert.get('epochs')
    if type(epochs) is not list or not epochs:
        raise ValueError('missing epochs')
    mode = cert.get('mode')
    if mode not in ('selective', 'saturated'):
        raise ValueError('unknown scheduling mode')
    done, seen, eventmap, allocation = set(), set(), {}, {}
    previous_end = 0
    for i, ep in enumerate(epochs):
        if type(ep) is not dict or type(ep.get('tasks')) is not list or not ep['tasks']:
            raise ValueError('invalid epoch')
        ids = ep['tasks']
        if any(type(v) is not int or not 0 <= v < n for v in ids) or len(set(ids)) != len(ids):
            raise ValueError('duplicate or invalid task')
        ids = set(ids)
        if ids & seen:
            raise ValueError('task executed twice')
        if not matching(pairs[v] for v in ids):
            raise ValueError('one port has two partners within an epoch')
        st, en = ep.get('start'), ep.get('end')
        if type(st) is not int or type(en) is not int or en <= st:
            raise ValueError('invalid epoch times')
        if st != (0 if i == 0 else previous_end + cert['rho']):
            raise ValueError('incorrect setup/drain boundary')
        records = ep.get('events')
        if type(records) is not list or len(records) != len(ids):
            raise ValueError('missing events')
        local = set()
        for ev in records:
            if type(ev) is not dict:
                raise ValueError('invalid event')
            v, a, b = ev.get('task'), ev.get('start'), ev.get('finish')
            if type(v) is not int or v not in ids or v in local:
                raise ValueError('invalid event identity')
            if type(a) is not int or type(b) is not int or not st <= a < b <= en or b - a != duration[v]:
                raise ValueError('incorrect service interval')
            local.add(v)
            allocation[v] = i
            eventmap[v] = (a, b)
        if en != max(eventmap[v][1] for v in ids):
            raise ValueError('epoch must finish on its last event')
        for v in ids:
            if not pred[v] <= done | ids:
                raise ValueError('epoch prefix is not an ideal')
        if mode == 'saturated' and not is_saturated(ids, done, pairs, pred):
            raise ValueError('false saturation claim')
        # Also independently execute the admitted batch and compare the ASAP duration.
        exact, replay_events = interpret(ids, done, pairs, duration, pred)
        if any(eventmap[v] != (st+a, st+b) for v, a, b in replay_events):
            raise ValueError('event is not the canonical ASAP execution')
        if en - st != exact:
            raise ValueError('certificate is not the canonical ASAP execution')
        seen |= ids
        done |= ids
        previous_end = en
    if seen != set(range(n)):
        raise ValueError('unfinished tasks')
    for v in range(n):
        for u in pred[v]:
            if allocation[u] > allocation[v] or eventmap[u][1] > eventmap[v][0]:
                raise ValueError('precedence violation')
    # Direct interval check, including tasks on the same pair.
    _check_endpoint_intervals(pairs, eventmap)
    if type(cert.get('makespan')) is not int or cert['makespan'] != previous_end:
        raise ValueError('incorrect makespan')
    return {'valid': True, 'tasks': n, 'epochs': len(epochs), 'makespan': previous_end,
            'meaning': 'feasible canonical timeline, not a proof of optimality'}


def check_collective(raw, cert):
    """Check bounded symbolic coverage; source values are captured at task start.

    Missing semantics means a generic task instance. A present but unrecognized
    declaration is rejected rather than silently exempted. The checker limits
    symbolic storage to 65,536 (chunk, endpoint) cells; this is an implementation
    limit, not a restriction on the mathematical scheduling theorems.
    """
    check(raw, cert)
    if 'semantics' not in raw:
        return {'applicable': False}
    semantics = raw['semantics']
    if semantics not in ('broadcast', 'allreduce'):
        raise ValueError('unknown collective semantics')
    ports, chunks = raw['ports'], raw.get('chunks')
    if type(chunks) is not int or not 1 <= chunks or ports * chunks > 65536:
        raise ValueError('invalid symbolic chunk count or cell budget')
    expected = (1 << ports) - 1 if semantics == 'allreduce' else 1
    for t in raw['tasks']:
        if type(t.get('chunk')) is not int or not 0 <= t['chunk'] < chunks:
            raise ValueError('invalid semantic chunk')
        if any(type(t.get(k)) is not int or not 0 <= t[k] < ports for k in ('src', 'dst')):
            raise ValueError('invalid semantic endpoint')
        if set((t['src'], t['dst'])) != set(t['pair']):
            raise ValueError('semantic endpoints disagree')
        if t.get('phase') not in ('reduce', 'broadcast'):
            raise ValueError('unknown semantic phase')
        if semantics == 'broadcast' and t['phase'] != 'broadcast':
            raise ValueError('reduction is not a broadcast operation')
        if type(t.get('value')) is not int or not 1 <= t['value'] <= expected:
            raise ValueError('invalid symbolic source value')
    values = {(c, u): (1 << u if semantics == 'allreduce' else (1 if u == 0 else 0))
              for c in range(chunks) for u in range(ports)}
    # At a shared timestamp, all finishes become visible before any starts.
    timeline = []
    for ep in cert['epochs']:
        for ev in ep['events']:
            timeline.extend([(ev['start'], 1, ev['task']), (ev['finish'], 0, ev['task'])])
    captured = {}
    for _, start, v in sorted(timeline):
        t = raw['tasks'][v]
        c, src, dst = t['chunk'], t['src'], t['dst']
        if start:
            if values[c, src] != t['value']:
                raise ValueError('symbolic source value unavailable at start')
            captured[v] = values[c, src]
        elif t['phase'] == 'reduce':
            if captured[v] & values[c, dst]:
                raise ValueError('duplicate summand')
            values[c, dst] |= captured[v]
        else:
            values[c, dst] = captured[v]
    if any(v != expected for v in values.values()):
        raise ValueError('collective postcondition fails')
    return {'applicable': True, 'valid': True, 'chunks': chunks,
            'meaning': 'exact symbolic data coverage, not floating-point or device execution'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('packet', type=Path)
    args = ap.parse_args()
    try:
        packet = json.loads(args.packet.read_text())
        result = check(packet['instance'], packet['certificate'])
        result['collective'] = check_collective(packet['instance'], packet['certificate'])
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        ap.exit(2, f'rejected: {exc}\n')

if __name__ == '__main__':
    main()
