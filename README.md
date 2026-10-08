# Reconfiguration-safe optical epochs

This standalone research artifact accompanies **Time-Preserving Admission in Drained Matching Epochs**. It implements completion-horizon admission, exact service/count frontiers, an independent event interpreter, bounded assignment oracles, static interval planning, and whole-phase deadline queries. It is an offline scheduling reference, not an optical controller or a GPU collective library.

## Result and model

A task uses one **unordered** endpoint pair for a positive, nonpreemptive service time. Input order fixes the FIFO order on each pair. Supplied precedence and FIFO edges form the augmented task DAG. An epoch installs a matching, executes its admitted tasks at their earliest feasible times, and drains all of them before a globally blocking, uniform, nonnegative setup. Initial installation is free. Ready but unadmitted tasks may remain queued. Storage is reserved; there are no external releases, buffer waits, failures, task preemption, or overlapping setups.

Unrestricted saturation preserves minimum epoch count but can lose a factor approaching floor(n/2) in makespan, even at the same minimum count. Completion-horizon admission is different: it selects only tasks that can **finish completely** within a relative horizon. The written normal-form theorem transforms any selective schedule into horizon-complete batches on maximal installed matchings, with no more epochs and no later completion of any task, simultaneously for every nonnegative uniform setup cost. This does not mean that saturation preserves time, that timestamps remain identical, or that every exact-count spectrum entry survives. The nondominated service/count frontier survives.

The event planner optimizes **makespan**. Its count/service labels do not optimize weighted task completion or arbitrary per-task deadlines. Static interval planning optimizes worst-case makespan of a fixed batch sequence; it does not provide an adaptive scheduling policy. A whole-phase deadline query reuses an already completed exact frontier and returns the largest feasible uniform setup. The complete model, theorem proofs, counterexamples, and executable contracts are in `proofs/`.

## Requirements and first run

Use Python 3.10 or newer. The Python implementation needs only the standard library. Linux is the evaluated full-campaign platform: campaign entry points use `resource` and CPU affinity. Solver, regression and retained-result checks do not require those Linux controls; they can also be run on Windows. Experiments require no network, external solver, model API, GPU, or private trace. The paper's LaTeX dependencies are separate and are not needed by this repository.

From this directory:

```sh
python reproduce_all.py
```

This runs the regression suite's **82 test methods** and verifies both retained result sets. A method may enumerate multiple inputs or parameter settings; 82 is not a count of scheduling cases or counterexamples. It does not recompute the full campaigns. The output explicitly distinguishes these actions. Comparing a supplied result directory with retained data does not, by itself, establish that a fresh optimization occurred.

Six additional checker-index controls run separately with
`python -B tests/checker_index_regression.py` and explicitly in scientific CI.
They compare independent FIFO reconstruction on 6,912 bounded encodings,
strict admission and call-locality controls, direct half-open overlap tests,
canonical timelines and symbolic start-capture/budget controls. These are finite
follow-up checks, not a new reproduction or timing receipt for the retained campaign.

To recompute all numerical evidence in a separate directory:

```sh
python reproduce_all.py --full --output-dir reproduced --seconds 20
```

The wrapper executes both campaigns in bounded sequential chunks, then validates spectra, certificates, exact parameter envelopes, search outcomes, and generated tables. It writes logs beneath the requested output directory. If the finite maximum chunk count is reached, it fails rather than treating partial results as complete; an explicit rerun with the same directory resumes. Do not reuse a directory from an unrelated input set.

CPU time, elapsed time, and peak memory vary between runs and are not compared as scientific invariants. The retained stress failures are work-limit outcomes; a slower host may hit its wall-time limit first and will then report a different, explicitly incomplete search. No capped search is reported as an optimum. The wrapper rejects attempts to overwrite retained evidence with fresh output.

The scientific workflow is prepared for a flat artifact repository on Ubuntu 24.04. It runs the full wrapper on pushes to `main` or manual dispatch, with a 900-second whole-command limit, a 3 GiB virtual-memory limit and the existing per-search/chunk limits. Failure gates remain enabled. It always attempts to upload only `scientific-output`, including the whole-run log and any partial numerical output. A configured workflow is not evidence that a hosted run has occurred.

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

## Limits and rights

No model is trained, so the relevant bias is selective instance design, not learned-parameter overfitting. Complete declared small domains, fixed larger families, all-setup envelopes, independent implementations, negative controls, and retained failures address that risk within the stated domain. They do not make generated inputs representative of deployed workloads.

Readable proofs support the general results; finite checks test implementation consistency without proof-assistant verification. The implementation is not hardened against arbitrary hostile input or offered as production control software. Human authors must examine correctness, authorship, and current publication policies before external use. Source/generated inputs and written materials carry the licenses in `LICENSE`, subject to the rights of the eventual human copyright holders; see `THIRD-PARTY-NOTICES.md`.
