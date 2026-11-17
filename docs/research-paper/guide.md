# Research that can be explained and checked

Choose a consequential question, design evidence that could change your view, and write the claim the evidence establishes. This guide distils researcher advice, methodological arguments, published studies and venue guidance. Procedures labelled as inference are proposed applications. Scientific competence requires independent domain judgment and demonstrated work.

## Choose a question with an informative answer

Hamming's retrospective advice connects important problems with a plausible attack. Use that heuristic to identify what an answer would change and what observation is feasible. Treat his career stories as personal testimony. Define the setting, comparison and contribution before selecting a method. [HAM](https://www.cs.virginia.edu/~robins/YouAndYourResearch.html).

Read literature to establish what remains uncertain. Keshav's successive passes provide a useful reading strategy. Record the actual depth reached, then compare assumptions, populations, methods and results across papers. Follow promising and contradictory leads to primary evidence. As a practical inference, retain search dates and boundaries when claiming novelty or review coverage. [KES](https://cs.uwaterloo.ca/~brecht/courses/854-http-video-2012/readings/keshav-paper-reading.pdf).

## Choose evidence that separates explanations

The design follows the objective and factors being investigated. As a practical inference, pair each claim with its decisive observation, credible baseline, strongest relevant comparator and expected failure mode. Match preprocessing, tuning access, measurement and resource budgets. An efficiency claim needs the costs that could explain the advantage. Use ablations for component claims and combinations when interactions matter. Blocking and randomization address nuisance variation. [DESIGN](https://www.itl.nist.gov/div898/handbook/pri/section3/pri33.htm), [BLOCK](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm), [FACTOR](https://www.itl.nist.gov/div898/handbook/pri/section3/pri333.htm).

Specify the independent unit, data boundaries, meaningful effect, uncertainty analysis and stopping rule before confirmatory outcomes. Preserve exploratory discoveries and dated revisions. Nosek and colleagues explain the inferential reason for distinguishing prediction from post hoc explanation, while acknowledging limits to the experimental evidence available in 2018. [NOSEK](https://psychologicalsciences.unimelb.edu.au/__data/assets/pdf_file/0007/2888098/The-preregistration-revolution.pdf).

## Let the evidence revise the plan

**Published cases.** Recht and colleagues found accuracy drops on newly curated test sets alongside continued relative model progress, motivating a distribution-based interpretation. Agarwal and colleagues found evaluation protocols and few-run uncertainty could alter benchmark comparisons. The planning inference is to diagnose sampling and measurement before expanding a method or making a causal claim. [IMG](https://proceedings.mlr.press/v97/recht19a/recht19a.pdf), [RLI](https://proceedings.neurips.cc/paper_files/paper/2021/file/f514cec81cb148559cf475e7426eed5e-Paper.pdf).

**Hypothetical cases.** If a retrieval gain follows changed deduplication, hold preprocessing fixed and test the component's contribution. If a wide interval includes a practically useful gain, retain uncertainty and reassess precision. Both changes preserve the observation while revising the claim. The progressive evaluation reference supplies the full cases. [Method, design and evaluation](../../content/skills/research-paper/method-design-eval.md).

Report negative findings, failed comparisons and limitations. ASA guidance supports reporting effect magnitude, uncertainty and context. Lakens explains how prespecified equivalence bounds can support the absence of a meaningful effect. Inference should preserve the distinction between an inconclusive result and evidence of practical equivalence. [ASA](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf), [LAK](https://pure.tue.nl/ws/portalfiles/portal/80918653/lakeequi2017.pdf).

## Write an assessable argument

Peyton Jones advises early drafting, a clear central idea, refutable contributions and reader feedback. Apply this by connecting each claim to a result or proof and retaining its assumptions. Write the abstract from the completed evidence. Choose figures for the comparison readers need, with units, readable scales, defined uncertainty and explanatory captions. [SPJ](https://www.microsoft.com/en-us/research/uploads/prod/2016/07/How-to-write-a-great-research-paper.pdf), [FIG](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003833).

Use the target venue's actual edition for submission decisions. NeurIPS 2025 reviewer guidance provides an illustrative lens on quality, clarity, significance and originality. Turn substantive review concerns into an evidence check, explanation change or justified disagreement, then revise affected claims. [NRG](https://nips.cc/Conferences/2025/ReviewerGuidelines).

## Make the record reproducible and responsible

As a practical inference, retain source/data revisions, environments, commands, raw observations, exclusions, analysis and figure provenance, and expected versus observed results. The ImageNetV2 artifact illustrates named dataset revisions and a documented curation/evaluation pipeline. SIGCOMM 2026 provides distinct criteria for artifact availability and functionality. State the actual verification level achieved. [IMGART](https://github.com/modestyachts/ImageNetV2/blob/0b0c3fe89058e4c7ee2348938b3f4f706a931bf3/README.md), [SIG](https://conferences.sigcomm.org/sigcomm/2026/artifacts/).

ORI's definition addresses fabrication, falsification and plagiarism. Preserve attribution and accurate records, apply relevant consent and data-use obligations, and verify generated claims and citations. The inspected NeurIPS checklist offers venue-specific prompts for limitations and reproducibility. Author accountability requires judgment throughout the work. [ORI](https://ori.hhs.gov/definition-research-misconduct), [NCP](https://neurips.cc/public/guides/PaperChecklist).

## Use the progressive material

- [Entry skill](../../content/skills/research-paper/SKILL.md) routes to the current research stage.
- [Framing and literature](../../content/skills/research-paper/framing-literature.md) develops the question and reading record.
- [Method, design and evaluation](../../content/skills/research-paper/method-design-eval.md) explains comparisons, statistics and plan changes.
- [Writing, figures and review](../../content/skills/research-paper/writing-figures-review.md) connects claims to the manuscript and artifact.
- [Source ledger](sources.md) records read depth, provenance and limits, with [retrieval pins](../../content/knowledge/research-source-pins.json).
