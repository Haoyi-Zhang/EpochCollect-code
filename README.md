# Reconfiguration-safe optical epochs

A standalone, standard-library research artifact for selective admission versus saturation in globally drained matching epochs. It contains complete written arguments, a bounded exact planner, a separately implemented event checker, a small exhaustive assignment oracle, exact generated inputs, and raw results. It is not an optical controller or GPU collective library. The accompanying research is an internal evidence checkpoint, not a completed or submission-ready TPDS article; significance and the required literature calibration remain open.

## Model

Each nonpreemptive positive-service task names one unordered endpoint pair. Each endpoint has at most one partner per epoch. Tasks on the same pair have input-order FIFO precedence, in addition to the supplied DAG. Admitted work completes before a uniform global reconfiguration cost is paid. Unadmitted ready work may remain queued. Sufficient storage and eventual task completion are assumptions. No buffer, GPU-kernel, optical-device, packet-forwarding, failure or production-performance claim is made.

`proofs/model.md` contains the full mathematical arguments. Saturation preserves the smallest possible number of epochs, but can cost a sharp factor floor(ports/2) in completion time, even for a path of used pairs and an out-tree dependency graph. This is a narrow mathematical result; no priority claim is certified. The workload inequality and ideal-state dynamic program are standard methodology.

## Quick example

Run in this directory with Python 3.10 or newer. No third-party Python package, model API, download, GPU or solver is needed.

```sh
python epochs.py inputs/example.json --rho 1 --mode selective --output example-certificate.json
python checker.py example-certificate.json
python epochs.py inputs/example.json --rho 1 --mode saturated --output saturated-certificate.json
python checker.py saturated-certificate.json
```

The example has six endpoints, eight tasks, and five epochs in either optimum. Its selective makespan is 16 and its saturated makespan is 30. A successful certificate check proves canonical feasibility only; exactness comes from the recurrence proof and the finite oracle comparison, not from a hidden certificate of optimizer optimality.

## Full finite reproduction

The campaign runner uses Linux `resource` and CPU-affinity support, one worker, and a 3 GiB address-space cap. It is deliberately bounded to at most 40 seconds per invocation, checked between frozen small instances. The observed complete run is shorter than one default chunk; no per-instance hard preemption is claimed. Use a new result directory so retained answers cannot be mistaken for recomputation.

```sh
python -m unittest discover -s tests -v
python reproduce.py --output-dir reproduced-results --seconds 30
python verify_results.py reproduced-results
python make_tables.py --output-dir reproduced-results
```

When the runner prints `RESUMABLE`, repeat the same reproduction command. `COMPLETE` means the finite campaign finished, not that the entire research-paper contract passed. The verification command compares exact scientific structures while excluding CPU time, wall time, and resident memory. It interprets every retained and reproduced weighted/scale certificate again. It emits no checksum, version, commit or toolchain manifest.

The command `python generators.py` can regenerate inputs, but normal reproduction deliberately consumes the exact retained JSONL rather than relying on pseudorandom-library behavior across Python implementations. It overwrites the three named input JSONL files and the example only; preserve your original inputs when experimenting. No private cache or `paper/` directory is required.

## Coverage and non-results

There are 6,912 labeled small input encodings, not nonisomorphic DAGs: 1,728 three-task cases on all six pairs of four endpoints, and 5,184 four-task cases on a three-pair path alphabet. Fixed duration vectors are (1,2,3) and (1,3,2,4), respectively. All forward precedence encodings are enumerated and pair FIFO edges are added. The separate oracle enumerates 1,373,760 assignments, of which 48,320 are valid; both full service/epoch spectra agree on all inputs.

The weighted set has 240 inputs: 120 four-endpoint tree Allreduces (three shapes, one/two chunks, 20 seeds), 30 seven-endpoint two-chunk broadcasts (three shapes, ten seeds), 20 two-chunk six-pair exchange inputs, 40 random DAGs, ten total chains, 15 weighted tight constructions and five unit-expanded constructions. Generated random service values are in {1,2,4,8}; they are abstract units, not bytes, bandwidths or calibrated hardware times. Setup costs are 0,1,4,16. All 120 Allreduce and all 20 pair-exchange cases have zero exact selective-versus-saturated gain at every setup value. These null results are retained.

The 80 scale inputs have up to 64 endpoints and 95 tasks. They use explicit feasible schedules plus the proved construction lower bounds, not large-instance exhaustive optimization. Exact optimization rejects more than 16 tasks; the independent assignment oracle rejects more than four. There are 3,000 symbolic collective checks in the weighted campaign, 960 bounded-duration replays, and 46 regression tests. The validator's symbolic storage limit is 65,536 chunk/endpoint cells. Finite tests are not machine-checked general proofs or independent human review.

## Files and evidence

- `epochs.py`, `checker.py`, `oracle.py`: independent implementation paths as described above; the assignment oracle shares the independent checker semantics, not the planner's recurrence.
- `generators.py`, `inputs/`: frozen selection and exact consumed data; `reproduce.py` evaluates all five baselines at equal inputs.
- `results/`: raw rows, 320 certificate packets, derived tables, and measured resource records.
- `claim_evidence_ledger.csv`, `external_resources.csv`: scope, provenance, and maturity.
- `proofs/model.md`, `proofs/certificate-format.md`: mathematical and executable contracts.

Written proofs are human-readable arguments prepared with substantive AI assistance. No proof assistant or independent external reviewer validated them. Authors must review all work before any external use. The source code and generated inputs are offered under the MIT license; the written scientific documentation is offered under CC BY 4.0, subject to the rights of their eventual human copyright holders. No third-party paper PDFs are redistributed. See `LICENSE` and `THIRD-PARTY-NOTICES.md`.
