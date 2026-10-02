"""Exact bounded scheduling for drained matching epochs (standard library only)."""
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class Task:
    pair: tuple[int, int]
    p: int
    pred: tuple[int, ...]


def integer(x: Any, name: str, lo: int, hi: int) -> int:
    if type(x) is not int or not lo <= x <= hi:
        raise ValueError(f"{name} must be an integer in [{lo}, {hi}]")
    return x


def parse(raw: dict) -> tuple[int, tuple[Task, ...]]:
    if not isinstance(raw, dict):
        raise ValueError("instance must be an object")
    ports = integer(raw.get("ports"), "ports", 2, 10000)
    data = raw.get("tasks")
    if not isinstance(data, list) or not 1 <= len(data) <= 10000:
        raise ValueError("tasks must contain between 1 and 10000 entries")
    tasks: list[Task] = []
    last: dict[tuple[int, int], int] = {}
    for i, obj in enumerate(data):
        if not isinstance(obj, dict):
            raise ValueError("task must be an object")
        q = obj.get("pair")
        if not isinstance(q, (list, tuple)) or len(q) != 2:
            raise ValueError("pair must have two endpoints")
        a, b = (integer(v, "endpoint", 0, ports - 1) for v in q)
        if a == b:
            raise ValueError("self-circuits are excluded")
        pair = tuple(sorted((a, b)))
        p = integer(obj.get("p"), "service", 1, 10**12)
        deps = obj.get("pred", [])
        if not isinstance(deps, list):
            raise ValueError("pred must be a list")
        ds = set(integer(d, "predecessor", 0, i - 1) for d in deps)
        if pair in last:
            ds.add(last[pair])
        tasks.append(Task(pair, p, tuple(sorted(ds))))
        last[pair] = i
    return ports, tuple(tasks)


def bits(mask: int):
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


class Exact:
    """Enumerates ideals and matching-compatible ideal differences; N <= 16."""
    def __init__(self, raw: dict):
        self.ports, self.tasks = parse(raw)
        self.n = len(self.tasks)
        if self.n > 16:
            raise ValueError("exact search supports at most 16 tasks; use certificates for larger cases")
        self.pred = [sum(1 << u for u in t.pred) for t in self.tasks]
        size = 1 << self.n
        self.full = size - 1
        self.ideal = bytearray(size)
        self.feasible = bytearray(size)
        self.ideal[0] = self.feasible[0] = 1
        self.duration = [0] * size
        self.support = [0] * size
        pair_tasks = {t.pair: sum(1 << j for j, s in enumerate(self.tasks) if s.pair == t.pair)
                      for t in self.tasks}
        conflict = [sum(1 << j for j, s in enumerate(self.tasks)
                        if s.pair != t.pair and set(s.pair) & set(t.pair)) for t in self.tasks]
        for mask in range(1, size):
            v = mask.bit_length() - 1
            rest = mask ^ (1 << v)
            self.ideal[mask] = self.ideal[rest] and (self.pred[v] & mask) == self.pred[v]
            self.feasible[mask] = self.feasible[rest] and not (rest & conflict[v])
            self.support[mask] = self.support[rest] | pair_tasks[self.tasks[v].pair]
            if self.feasible[mask]:
                finish = [0] * self.n
                for u in bits(mask):
                    finish[u] = self.tasks[u].p + max((finish[d] for d in bits(self.pred[u] & mask)), default=0)
                self.duration[mask] = max(finish)
        self.dp: dict[str, list[dict[int, int]]] = {}
        self.parents: dict[str, dict[tuple[int, int], int]] = {}
        self.stats = {"tasks": self.n, "ideals": sum(self.ideal), "arcs": 0, "saturated_arcs": 0}

    def closure(self, done: int, support: int) -> int:
        for v in range(self.n):
            if (support >> v) & 1 and self.pred[v] & done == self.pred[v]:
                done |= 1 << v
        return done

    def solve(self) -> dict[str, dict[int, int]]:
        self.stats["arcs"] = self.stats["saturated_arcs"] = 0
        arrays = {mode: [{} for _ in range(self.full + 1)] for mode in ("selective", "saturated")}
        parents = {mode: {} for mode in arrays}
        for arr in arrays.values():
            arr[0][0] = 0
        for j in range(1, self.full + 1):
            if not self.ideal[j]:
                continue
            i = (j - 1) & j
            while True:
                s = j ^ i
                if self.ideal[i] and self.feasible[s]:
                    self.stats["arcs"] += 1
                    modes = ["selective"]
                    if self.closure(i, self.support[s]) == j:
                        modes.append("saturated")
                        self.stats["saturated_arcs"] += 1
                    for mode in modes:
                        for k, value in arrays[mode][i].items():
                            value += self.duration[s]
                            old = arrays[mode][j].get(k + 1)
                            if old is None or value < old:
                                arrays[mode][j][k + 1] = value
                                parents[mode][j, k + 1] = i
                if i == 0:
                    break
                i = (i - 1) & j
        self.dp, self.parents = arrays, parents
        return {mode: dict(sorted(arr[self.full].items())) for mode, arr in arrays.items()}

    def schedule(self, rho: int, mode: str = "selective") -> dict:
        integer(rho, "rho", 0, 10**12)
        if mode not in ("selective", "saturated"):
            raise ValueError("unknown mode")
        if not self.dp:
            self.solve()
        values = self.dp[mode][self.full]
        k = min(values, key=lambda k: (values[k] + (k - 1) * rho, k))
        masks, j, count = [], self.full, k
        while j:
            i = self.parents[mode][j, count]
            masks.append(j ^ i)
            j, count = i, count - 1
        return certificate(self.tasks, list(reversed(masks)), rho, mode)


def certificate(tasks: tuple[Task, ...], batches: list[int], rho: int, mode="selective") -> dict:
    """Emit a concrete ASAP timeline; checking is implemented separately."""
    epochs = []
    now = 0
    for i, mask in enumerate(batches):
        if i:
            now += rho
        start = now
        finished = {}
        events = []
        for v in bits(mask):
            st = max((finished[d] for d in tasks[v].pred if d in finished), default=start)
            finished[v] = st + tasks[v].p
            events.append({"task": v, "start": st, "finish": finished[v]})
        now = max(finished.values())
        epochs.append({"tasks": list(bits(mask)), "start": start, "end": now, "events": events})
    return {"mode": mode, "rho": rho, "epochs": epochs, "makespan": now}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("instance", type=Path)
    ap.add_argument("--rho", type=int, default=1)
    ap.add_argument("--mode", choices=["selective", "saturated"], default="selective")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        raw = json.loads(args.instance.read_text())
        engine = Exact(raw)
        spectrum = engine.solve()
        result = {"instance": raw, "certificate": engine.schedule(args.rho, args.mode),
                  "spectrum": spectrum, "search": engine.stats}
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    except (ValueError, KeyError, OSError, TypeError) as exc:
        ap.exit(2, f"error: {exc}\n")

if __name__ == "__main__":
    main()
