# Reconfiguration-safe optical epochs

This standalone research artifact accompanies **Time-Preserving Admission in Drained Matching Epochs**. It implements completion-horizon admission, exact service/count frontiers, an independent event interpreter, bounded assignment oracles, static interval planning, and whole-phase deadline queries. It is an offline scheduling reference, not an optical controller or a GPU collective library.

## Result and model

A task uses one **unordered** endpoint pair for a positive, nonpreemptive service time. Input order fixes the FIFO order on each pair. Supplied precedence and FIFO edges form the augmented task DAG. An epoch installs a matching, executes its admitted tasks at their earliest feasible times, and drains all of them before a globally blocking, uniform, nonnegative setup. Initial installation is free. Ready but unadmitted tasks may remain queued. Storage is reserved; there are no external releases, buffer waits, failures, task preemption, or overlapping setups.

Unrestricted saturation preserves minimum epoch count but can lose a factor approaching floor(n/2) in makespan, even at the same minimum count. Completion-horizon admission is different: it selects only tasks that can **finish completely** within a relative horizon. The written normal-form theorem transforms any selective schedule into horizon-complete batches on maximal installed matchings, with no more epochs and no later completion of any task, simultaneously for every nonnegative uniform setup cost. This does not mean that saturation preserves time, that timestamps remain identical, or that every exact-count spectrum entry survives. The nondominated service/count frontier survives.

The event planner optimizes **makespan**. Its count/service labels do not optimize weighted task completion or arbitrary per-task deadlines. Static interval planning optimizes worst-case makespan of a fixed batch sequence; it does not provide an adaptive scheduling policy. A whole-phase deadline query reuses an already completed exact frontier and returns the largest feasible uniform setup. The complete model, theorem proofs, counterexamples, and executable contracts are in `proofs/`.

## Requirements and first run

Use Python 3.10 or newer. The implementation needs only the standard library. The historical full-campaign platform is Linux, with resource and CPU-affinity controls. An explicit portable option now permits Windows with verified one-lane affinity and no claimed Linux memory cap. Solver, regression and retained-result checks need no Linux controls. Experiments require no network, external solver, model API, GPU, or private trace. The paper's LaTeX dependencies are separate.

From this directory:

```sh
python reproduce_all.py
```

This runs the current default suite's **99 test methods** and verifies both retained result sets. A method may enumerate multiple inputs or parameter settings; 99 is not a count of scheduling cases or counterexamples. It does not recompute the full campaigns. Comparing supplied results with retained data does not by itself establish fresh optimization. The historical 82-method record is unchanged.

The six original checker-index controls are included in default discovery via
the small test-module adapter. They can also run separately with
`python -B tests/checker_index_regression.py`.
They compare independent FIFO reconstruction on 6,912 bounded encodings,
strict admission and call-locality controls, direct half-open overlap tests,
canonical timelines and symbolic start-capture/budget controls. These are finite
follow-up checks, not a new reproduction or timing receipt for the retained campaign.

To recompute all numerical evidence in a separate directory:

```sh
python reproduce_all.py --full --output-dir reproduced --seconds 20
```

The wrapper requires an empty output directory, executes both campaigns in bounded sequential chunks, then validates spectra, certificates, exact envelopes, search outcomes, and generated tables. It writes logs beneath that directory and fails if its chunk allowance is exhausted. Use the low-level commands, not another full fresh invocation, to resume an explicitly matching partial campaign.

CPU time, elapsed time, and peak memory vary between runs and are not compared as scientific invariants. The retained stress failures are work-limit outcomes; a slower host may hit its wall-time limit first and will then report a different, explicitly incomplete search. No capped search is reported as an optimum. The wrapper rejects attempts to overwrite retained evidence with fresh output.

The scientific workflow runs from a flat artifact repository on Ubuntu 24.04. It runs the full wrapper in normal and optimized Python on pushes to `main` or manual dispatch, with a 900-second limit per full command, a 3 GiB virtual-memory limit and the existing search/chunk limits. Failure gates remain enabled. It uploads `scientific-output`, including complete or partial raw outputs.

## Example

The original eight-task path construction has six endpoints and five epochs in both policy optima. At unit setup, selective admission costs 16 and unrestricted saturation costs 30:

```sh
python epochs.py inputs/example.json --rho 1 --mode selective --output example-certificate.json
python checker.py example-certificate.json
python epochs.py inputs/example.json --rho 1 --mode saturated --output saturated-certificate.json
python checker.py saturated-certificate.json
```

These commands use the original bounded subset reference. The newer API is illustrated by `tests/test_horizon.py`, `tests/test_robust.py`, and `tests/test_queries.py`. For example:

```python
from queries import setup_budget
print(setup_budget({4: 41, 6: 38}, 45))
# Finite maximum_setup = Fraction(7, 5), attained by six epochs.
```

The deadline function assumes an exact, completed frontier; it cannot authenticate global optimality of arbitrary caller-supplied numbers. Certificate checking likewise establishes canonical feasibility, not optimizer optimality.

## Implementations and independence

`horizon.py` implements finite-event transitions and count/service Pareto labels. `prefix.py` enumerates Cartesian products of FIFO queue prefixes using the **same** state engine, pruning, maximal matchings, and limits. It is a controlled admission-branching ablation, not an independent oracle. A common one-matching fast path is enabled for both.

`epochs.py` is the inherited ideal-subset reference (at most 16 tasks). `oracle.py` independently enumerates task-to-epoch assignments and invokes `checker.py`, whose heap-based event interpreter does not call either planner's path recurrence. Its FIFO map is rebuilt locally from strictly validated unordered pairs on every call; it is not imported from or shared with a planner. Its separate direct endpoint-interval check groups the validated intervals by used port, retaining the same half-open overlap rule and two bucket entries per task plus linear sorting/check temporaries under the unchanged 10,000-task input cap. No timing gain or search-coverage improvement is claimed for these checker-only changes. The assignment oracle defaults to four tasks; the explicit larger validation passes a bound of six. The event planner defaults to a 512-task input ceiling but can still exhaust state, candidate, matching, transition, or time limits far below that size. A task ceiling is not a tractability claim.

`robust.py` plans at the upper corner of a rectangular service/setup uncertainty set and replays the resulting fixed batches under admissible realizations. `queries.py` implements exact whole-phase setup-budget inversion with rational thresholds. Integer certificate data require explicit common scaling for rational service/setup values.

## Coverage and results

The numerical counts and CPU figures below are the retained Linux-host campaign. The current regression suite adds two mocked-clock checks of the one-matching shortcut's search budget and has also been run separately on Windows; those checks do not replace or pool the historical performance measurements.

The two complete labeled small domains contain 1,728 three-task and 5,184 four-task encodings, totaling **6,912**. They are not nonisomorphic graphs or all weight assignments. The original independent oracle examines **1,373,760** assignments, with **48,320** valid. A further **48** fixed five/six-task cases examine **1,194,744** assignments. All compared exact frontiers agree.

Across the entire nonnegative setup range, **24 / 6,912** small encodings and **54 / 240** weighted inputs exhibit a strict saturation loss. Their maximum ratios are **10/7** and **41/10** respectively; the latter is in a deliberately adversarial construction family. All **120** weighted tree-Allreduce inputs and **20** pair-exchange inputs remain tied for all setup costs. These are important null results, not omitted observations.

The **210** larger stress inputs are 120 structured collective DAGs and 90 random DAGs. Under identical caps, Horizon completes **180**, Prefix **174**; all **174** common optima agree. Six complete only under Horizon and thirty under neither method. The largest completed instance has **192 tasks in a structured tree**; this is not a claim that arbitrary 192-task DAGs are tractable. On the common 174 cases, attempted candidates total 1,012,426 versus 2,701,611, states 67,040 versus 81,661, and observed CPU time 5.124 versus 13.611 seconds. Candidate units differ between methods, so states and measured time are reported alongside them.

The inherited campaign additionally retains **80** analytical-family cases up to 64 endpoints/95 tasks, **3,000** symbolic collective checks, and **960** duration replays. Large constructed schedules rely on written optimality proofs and independently interpreted feasible certificates, not large exhaustive searches. Symbolic data coverage does not prove floating-point equivalence or runtime deadlock freedom.

## Layout and data lineage

- `inputs/`: exact consumed JSONL inputs, including the original sets and explicit copies used by the event campaign. Fixed selection rules are in `generators.py` and `evaluate_horizon.py`.
- `results/`: original 7,232-row reference campaign, 320 certificate packets, legacy derived data, and resource records. These are preserved supporting evidence, not obsolete alternative claims.
- `results/horizon/`: complete event, prefix, all-matching, independent-oracle, and stress records; exact envelopes; regenerated main-paper tables and plot data.
- `make_tables.py` and `make_horizon_tables.py`: validated derivation of numerical tables. The latter checks input results before writing the four main-paper data products.
- `proofs/`: complete readable mathematical arguments and certificate/uncertainty contracts.
- `claim_evidence_ledger.csv`: claims mapped to arguments, tests, and retained data.
- `references.bib`, `reference_catalog.csv`, `literature-comparison.md`, `external_resources.csv`: scholarly provenance, read scope, technical relationships, and rights notes. No third-party paper PDF is redistributed.

A low-level resumable run uses `reproduce.py --output-dir fresh-base --seconds 20` and `evaluate_horizon.py --output-dir fresh-event --seconds 20`; repeat each until its summary says complete, then use the corresponding `verify_results.py` or `verify_horizon.py` verifier. `reproduce_all.py` is the documented one-command alternative. Input regeneration is optional and overwrites named files; ordinary reproduction consumes retained inputs rather than silently regenerating them.

## Current controlled reproduction and full offline costs

The dated `evidence/20261014/` directory keeps current raw observations separate
from the unchanged historical `results/`. Normal and optimized full campaigns
each recompute 7,232 original and 7,410 extension rows. Their Windows 11,
CPython 3.12.14 receipts verify affinity to one logical processor and explicitly
record no Linux address-space cap or RSS measurement. Current total wall times
are 48.875 and 50.312 seconds; they are not device-speedup measurements.

From the artifact root, use an empty output directory:

```text
python -B reproduce_all.py --full --portable --output-dir own-normal --seconds 20
python -B -O reproduce_all.py --full --portable --output-dir own-optimized --seconds 20
python -B workflow_cost.py --portable --output-dir own-workflow
python -B verify_workflow.py own-workflow --frontiers own-normal/event/weighted.jsonl
```

On Linux omit `--portable`: the original verified affinity and 3 GiB limit stay
enforced. On Windows the flag is explicit and does not simulate Linux controls.
`--full` rejects nonempty directories before launching any child; low-level
commands still permit explicit resumption. Child interpreters preserve `-O`.
Default discovery includes the six original checker-index controls. Scientific
agreement/formula gates are explicit failures and cannot disappear under `-O`.
Envelope APIs require positive strict integer count/service fields; the result
reader permits canonical JSON decimal count keys, not aliases such as `01`.
Envelope intervals are `[lo, hi)`; the smaller-count row owns a shared breakpoint.

The same-information Prefix comparator and Horizon return the same frontiers,
four setup-cost certificates and whole-phase deadline decisions on all unchanged
240 weighted inputs. Three alternating-order repetitions yield 720 pairs and
1,440 stored executions per mode. Timed stages include input decoding, planning,
reconstruction, semantic/feasibility checks, serialization and consumer replay,
and the deadline query; file loading before the timer and benchmark logging are
excluded. No new generated workload is introduced. Normal-mode total-time ratio
Prefix/Horizon has median 1.162, range 0.243--12.208, with 76 faster Prefix pairs;
optimized mode gives 1.144, 0.440--13.591, and 64 faster Prefix pairs. The independent
consumer interprets 5,760 certificates per mode and recomputes deadline caps by
direct rational algebra. Repeated local interpreter timings are not independent
workload samples or GPU/network execution. All 120 Allreduce nulls and every
stress failure remain in the evidence.

## Limits and rights

No model is trained, so the relevant bias is selective instance design, not learned-parameter overfitting. Complete declared small domains, fixed larger families, all-setup envelopes, independent implementations, negative controls, and retained failures address that risk within the stated domain. They do not make generated inputs representative of deployed workloads.

Readable proofs support the general results; finite checks test implementation consistency without proof-assistant verification. The implementation is not hardened against arbitrary hostile input or offered as production control software. Human authors must examine correctness, authorship, and current publication policies before external use. Source/generated inputs and written materials carry the licenses in `LICENSE`, subject to the rights of the eventual human copyright holders; see `THIRD-PARTY-NOTICES.md`.
