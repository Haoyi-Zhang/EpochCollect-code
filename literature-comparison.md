# Scholarly comparison and citation scope

The bibliography covers optical-switch scheduling, collective communication, scheduling dominance, and resource-constrained optimization. These areas supply the comparisons and mathematical foundations for the model below. Published articles and preprints retain their publication identities; their device measurements are not evidence for this scheduler.

The central question is whether arbitrary nonpreemptive admissions can be replaced by complete-task event thresholds on maximal matchings **without postponing any task**, after earlier completed sets have changed. Merely distinguishing service cost from setup count, choosing a holding duration, using dynamic programming, or appealing to active schedules is not the new result.

| Closest comparison | Existing result or decision | Additional obligation here | Where the manuscript resolves it |
|---|---|---|---|
| Kesselman--Kogan, Nonpreemptive Scheduling of Optical Switches | A demand matrix, configuration holding costs and setup; whole aggregate entry assigned to a matching | Repeated pair queues and cross-pair dependency release are not a single aggregate-demand entry | II, III, VII.A; identical-demand/different-dependency construction |
| Eclipse, SIGMETRICS 2016 | Joint matching and duration choice; clipping demand to holding time; fixed-window throughput | Clip only complete indivisible FIFO tasks; prove coverage and relative-time monotonicity after earlier ideals expand | IV, Lemmas 2--3 and Theorem 3; VII.A |
| Harvest, arXiv v1 | Completion/setup optimization over contiguous intervals of a fixed collective-step word | Select arbitrary completed ideals, not only fixed-word prefixes, and prove a dominant event transition class | IV--V; VII.B |
| ProjecToR, SIGCOMM 2016 | Hardware and online flow-bundle/controller design | A different fixed-DAG model; neither runtime deadlock analysis nor empirical hardware performance is inherited | II, VII.A/D |
| Bridge and SWOT | Reusable subrings or overlap across independently reconfigured switches | Those capabilities violate the single-partner/global-setup assumptions used in the proof | VII.B; no cross-model speedup table |
| SCCL, TACCL, HeteCCL | Collective/routing synthesis and execution backends; TACCL also fixes link order at a later synthesis stage | The present fixed pair/DAG/FIFO input is narrower; horizon-normalization is not a new collective algorithm synthesizer | I, VII.B |
| Active/semi-active/non-delay schedules | Existing dominance terminology and regular-objective principle | Specialized complete-task timetable proof plus counterexample to unrestricted-saturation maximality | IV, VII.C |
| DCP, HEFT and PEFT | Criticality, optimistic finish estimates and heterogeneous placement | Placement is already fixed here; these are context, not defeated runtime baselines | VII.C |

The manuscript contains the full specialization proof rather than inferring novelty from different application names. No source inspected was found to state that entire specialization. This is a bounded literature comparison, not a global priority proof, an external novelty review, or an assertion that unpublished results do not exist.

## Identity and claim checks

The manuscript associates cited results with their publication records. The EJOR scheduling work is by **Arno Sprecher**. The GPU interconnect article was published in 2020; its DOI and author preprint date from 2019. BandPilot reports a 2026 TPDS issue and DOI; its unavailable final page range is left unspecified. Preprints are identified as preprints.

Some public access is through author versions or a mirror of the actual paper, not a publisher landing page. No third-party PDFs, scraped paper text, or unverified redistribution licenses are bundled. The `source_read_scope` field is authoritative: neither abstracts nor selected passages are silently counted as full-paper reading. The detailed final TPDS online submission rules were not readable from the JavaScript-only page and are not asserted as verified.

## Current source-to-result check (2026-10-14)

The current bounded review separately read the complete 14-page author-hosted
SIGMETRICS 2016 Eclipse text, including its appendix, and the complete 19-page
Harvest arXiv:2602.09188v1 text, including the topology formulation appendix.
These are specific source versions, not a certification of all 51 technical
references or of their final publisher layouts. Primary copies used for the
private review are not redistributed in this artifact.

Eclipse Section 2.3, Remark 1 permits shortest demand coverage via fixed-window
throughput; Sections 3.1--3.3 already clip aggregate demand and choose holding
times, with demand-support breakpoints. Harvest Section 4, Equations (5)--(7)
and Theorem 1 already use topology interval costs and a count/service recurrence
over a fixed step word. The present proof obligation is narrower and different:
whole FIFO-task coverage (main Lemma 2), timetable monotonicity after completed
ideals expand (Lemma 3), and the taskwise no-later replacement (Theorem 3).
The shared Prefix baseline has the same inputs and makespan guarantee; the
independent assignment oracle checks a separate implementation. None of these
facts establishes priority over all active-schedule specializations. Current
full-text verification of the Kesselman--Kogan and Sprecher--Kolisch--Drexl
published articles remains a literature-review boundary, not a claimed new result.

## Role of calibration

The selected TPDS papers span finite scheduling proofs, communication-cost models, resource contention, measured interconnect behavior, and application-level optimization. This is deliberately broader than the direct optical-scheduling neighbors. Their explanatory patterns inform the manuscript; their device measurements and empirical conclusions are not reused as evidence for this scheduler. The compact matrix in the research plan identifies the lesson, evidence type, and reading/version limitation for each sample. Citation count and sample count are never treated as an acceptance criterion or a substitute for the normal-form proof.
