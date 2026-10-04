"""Queue-prefix exact baseline; same DP, more general admission enumeration.

At a state and installed matching, every admissible set is a prefix of each
fixed pair queue. Enumerating their Cartesian product is a stronger baseline
than allocating every subset of all tasks. This module deliberately shares the
label-setting DP and matching enumerator with Horizon to isolate admission
branching. It is NOT an independent correctness oracle; oracle.py is separate.
"""
import itertools
import time
from horizon import Horizon, SearchLimit
from epochs import bits


class Prefix(Horizon):
    def transitions(self, done: int):
        arcs = {}
        for matching in self.matchings:
            finish = self.completion_times(done, matching)
            queues = [[v for v,t in enumerate(self.tasks) if t.pair == q
                       and not (done >> v & 1) and finish[v] is not None]
                      for q in sorted(matching)]
            prefixes = []
            for queue in queues:
                masks, mask = [0], 0
                for v in queue:
                    mask |= 1 << v
                    masks.append(mask)
                prefixes.append(masks)
            for choices in itertools.product(*prefixes):
                self.stats['horizon_candidates'] += 1
                if self.stats['horizon_candidates'] > self.limits.transitions:
                    raise SearchLimit('prefix-candidate limit')
                if self.stats['horizon_candidates'] % 128 == 0 and time.monotonic()-self.start_time > self.limits.seconds:
                    raise SearchLimit('wall-time limit')
                added = 0
                for part in choices:
                    added |= part
                if not added:
                    continue
                reached = done | added
                if any(self.pred[v] & reached != self.pred[v] for v in bits(added)):
                    continue
                # Every included task has its full fixed-matching earliest
                # finish: an ideal contains all its required predecessors.
                service = max(finish[v] for v in bits(added))
                old = arcs.get(reached)
                if old is not None and old != service:
                    raise AssertionError('inconsistent prefix duration')
                arcs[reached] = service
        return arcs
