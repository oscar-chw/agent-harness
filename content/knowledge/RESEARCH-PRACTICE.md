# Scientific research and paper writing

## Framing the question

State the phenomenon, setting, comparison, intended contribution and observation
that could change the conclusion. Explain why resolving the uncertainty matters.
A descriptive claim needs credible measurement and coverage. A causal claim needs
justified variation and assumptions. A theorem needs premises and an argument.
Match the evidence to the claim before choosing an impressive method.

This is a practical synthesis. Hamming's retrospective advice supports choosing
important, tractable problems as a heuristic. It supplies personal experience,
with selection and survivorship limits. [Hamming transcript](https://www.cs.virginia.edu/~robins/YouAndYourResearch.html).

## Literature and research specifications

Read first for relevance, then for the claim, assumptions and evidence. Reconstruct
a derivation or run an artifact when your own result depends on it. Record the
depth actually reached. Keshav's three-pass approach is researcher advice.
[How to Read a Paper](https://cs.uwaterloo.ca/~brecht/courses/854-http-video-2012/readings/keshav-paper-reading.pdf).

Keep a compact source matrix with question, population/data, comparison, method,
result, uncertainty, limitations and read extent. Follow original methods,
contradictory findings and replications. Keep dates and inclusion decisions when
making review-coverage or novelty claims. A research specification exposes the
question, closest checked work, competing explanation and next decisive test.
This procedure is authored synthesis. A verified implementation example is the
pinned interview/research-spec template, whose scientific efficacy is unmeasured.
[Research-spec example](https://github.com/pedrohcgs/claude-code-my-workflow/blob/fe7077463c06e6d1572bb6c13d1b00525a4ff28e/.claude/skills/interview-me/SKILL.md).

## Method and evaluation decisions

Define the independent unit, outcome, data boundaries, comparator, meaningful
effect, resource budget and stopping rule. Match preprocessing, access, tuning
opportunities and evaluation protocols. For efficiency, include costs that could
explain the gain. Preserve group dependencies and prevent leakage. Use ablations
for component contributions and combinations when interaction is the question.
Choose the design from the objective. Blocking can control important nuisance
factors and permits comparisons within those blocks. These are methodological
principles whose application needs project-specific justification.
[NIST design selection](https://www.itl.nist.gov/div898/handbook/pri/section3/pri33.htm),
[Blocking](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm).

## Interpreting weak or negative evidence

Report effect sizes, uncertainty and analysis choices. A threshold crossing alone
does not establish scientific importance. An inconclusive comparison leaves
meaningful benefit and harm unresolved. Evidence of practical equivalence needs
justified bounds and suitable analysis. State whether variation concerns people,
tasks, datasets or runs. For paired data, analyze paired differences.
[ASA release](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf),
[Equivalence testing primer](https://pure.tue.nl/ws/portalfiles/portal/80918653/lakeequi2017.pdf).

Preserve exploratory discoveries, dated changes, failed attempts and unresolved
limits. After seeing a result, identify the gap between the original claim and
what was established, compare plausible causes, and select a discriminating
check. Adding complexity is justified only when it resolves that gap.

## Cases that change a plan

Published examples illustrate why protocols and distribution matter. ImageNetV2
found accuracy drops on newly curated test sets while relative progress continued.
The cited RL study showed that evaluation choices and uncertainty affect benchmark
comparisons. Their findings have their own scope. Their raw experiments were not
reproduced during this research. The application to harness design is inference.
[ImageNetV2 paper](https://proceedings.mlr.press/v97/recht19a.html),
[RL evaluation paper](https://proceedings.neurips.cc/paper_files/paper/2021/file/f514cec81cb148559cf475e7426eed5e-Paper.pdf).

A hypothetical retrieval gain accompanied by changed deduplication calls for
matched preprocessing before attributing the effect to retrieval. A wide interval
around a small gain calls for justified precision or narrower claims. These
examples explain decisions; they are not measured harness outcomes.

## Writing, visuals and review

Draft early to expose unclear reasoning. Build the paper around a central idea,
refutable contributions and claim-to-evidence links. Peyton Jones offers this as
practitioner guidance. A figure should resolve the reader's comparison, with
units, readable scales, defined uncertainty and a caption explaining the evidence.
Verify the rendered figure against its data and inspect it at publication size.
[Peyton Jones writing guidance](https://www.microsoft.com/en-us/research/uploads/prod/2016/07/How-to-write-a-great-research-paper.pdf),
[Figure guidance](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003833).

For each substantive review concern, retain the concern, evidence, decision and
revised location. Investigate exposed flaws, clarify ambiguity or justify a
disagreement. Recheck the target venue's actual rules before submission.
Authorship and publication decisions remain accountable human responsibilities.
[NeurIPS checklist](https://neurips.cc/public/guides/PaperChecklist).

## Local retrieval and provenance

`harness research check research-paper` retrieves source-bound capability status.
The installed `research-paper` skill routes to framing, methods/evaluation and
writing/review references. Use the shared KB for one relevant section of this
chapter. [Source ledger](RESEARCH-SOURCES.md) records 18 inspected sources,
read depth and access limits. [Retrieval pins](research-source-pins.json) retain
17 content checksums and the failed retrieval of the remaining paper. A source
record establishes provenance. Model-performance adoption needs its own eval.
