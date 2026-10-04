# Scholarly comparison and citation scope

The bibliography contains 27 distinct scholarly entries: 12 TPDS articles, five adjacent published conference papers, five methodological journal articles, and five explicitly versioned preprints. This partition describes the bibliography, not a numerical TPDS policy. Reference counts cannot establish novelty. The catalog records author-version versus final-publication access and distinguishes full substantive reading from selected technical passages. A DOI string, an accessible abstract, and an inspected full paper are different kinds of evidence; no blanket claim of full publisher-PDF or online DOI-endpoint verification is made.

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

Each catalog row has one BibTeX key, canonical title/author spelling, year, publication identity or exact preprint revision, a scholarly address, a supported claim, and its main-paper location. The paper build requires equality of the explicitly cited keys, bibliography keys, and generated bibliography entries; it forbids blanket nocite. The count is 27, not a padded bibliography of uncited entries. The original ten references have been retained or updated only when relevant. The EJOR author is **Arno Sprecher**, not Andreas Sprecher. The GPU interconnect article's publication year is 2020 despite its 2019 DOI/author-preprint date. BandPilot's author v5 reports the 2026 TPDS issue/DOI; an unavailable final page range is left unspecified. Five preprints are visibly identified as such.

Some public access is through author versions or a mirror of the actual paper, not a publisher landing page. No third-party PDFs, scraped paper text, or unverified redistribution licenses are bundled. The `source_read_scope` field is authoritative: neither abstracts nor selected passages are silently counted as full-paper reading. The detailed final TPDS online submission rules were not readable from the JavaScript-only page and are not asserted as verified.

## Role of calibration

The selected TPDS papers span finite scheduling proofs, communication-cost models, resource contention, measured interconnect behavior, and application-level optimization. This is deliberately broader than the direct optical-scheduling neighbors. Their explanatory patterns inform the manuscript; their device measurements and empirical conclusions are not reused as evidence for this scheduler. The compact matrix in the research plan identifies the lesson, evidence type, and reading/version limitation for each sample. Citation count and sample count are never treated as an acceptance criterion or a substitute for the normal-form proof.
