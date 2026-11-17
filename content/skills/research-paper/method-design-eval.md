# Method, design and evaluation

Use this reference before committing resources or interpreting a scientific comparison. The design choices below are practical inference informed by the cited sources. Adapt them to the discipline and actual estimand, the quantity the study aims to learn.

## Design for the intended claim

State the intervention or method, outcome, target population, independent unit and comparison. Explain the proposed mechanism and assumptions. Choose measurements that can fail in a way that would challenge the hypothesis. For qualitative work, justify sampling, interpretation and treatment of disconfirming cases. For theory, expose the premises, argument and boundary cases. The appropriate design follows the question. [DESIGN, experimental objectives](https://www.itl.nist.gov/div898/handbook/pri/section3/pri33.htm).

Use a credible simple baseline and the strongest relevant available comparator. Match data access, preprocessing, tuning opportunity, stopping and evaluation protocols. For an efficiency claim, account for training, search and evaluation resources. Report unavoidable mismatches and narrow the comparison accordingly. Choose baselines that could genuinely overturn the claimed benefit. The RL case below illustrates the consequence of mismatched evaluation.

An ablation changes a component to examine its contribution under specified conditions. Keep the rest of the comparison interpretable, and distinguish removing a component from retraining a system without it. Component interactions may require combinations. A two-component factorial comparison contains neither component, each individually, and both together. This can distinguish an interaction from two independent improvements. Use it when that distinction bears on the claim and resources permit. [FACTOR, full factorial design](https://www.itl.nist.gov/div898/handbook/pri/section3/pri333.htm).

Control nuisance variation by blocking comparable conditions and randomizing where appropriate. Define independent units before selecting statistics. Repeated measurements on one person, document or training run share dependencies. Preserve grouping in splitting and analysis, and check leakage, duplicates and outcome availability. These choices protect the link between the observed difference and the intended comparison. [BLOCK, nuisance factors and within-block comparison](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm).

## Plan uncertainty and negative findings

**Official statistical guidance.** The ASA's 2016 release emphasizes contextual interpretation, complete reporting and effect magnitude. Its principles warn against treating a p-value threshold as a sufficient scientific decision. Report the effect in meaningful units, uncertainty, assumptions and analysis choices. Choose the statistical method for the sampling structure and research question. [ASA, six principles](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf).

Before observing confirmatory outcomes, justify the smallest meaningful effect, desired precision or power, resource budget, exclusions, comparisons and stopping rule. Account for multiple comparisons and dependence. State whether intervals represent variation across participants, tasks, datasets, runs or another level. Explain the estimator and interval procedure. For a paired comparison, assess uncertainty in the paired difference. An interval inherits its sampling and modelling assumptions.

**Methodological guidance.** Lakens describes equivalence testing using prespecified bounds for effects small enough to be practically negligible. An inconclusive superiority test leaves meaningful benefits and harms open. Evidence for practical equivalence requires a suitable design and analysis against justified bounds. Preserve informative negative findings, diagnostic failures and uncertainty. [LAK, introduction and TOST explanation](https://pure.tue.nl/ws/portalfiles/portal/80918653/lakeequi2017.pdf).

## Cases where evidence changes the plan

### Evaluation protocol changes an apparent gain

**Published evidence.** Agarwal and colleagues reevaluated Atari 100k comparisons and found that protocol differences could explain much of some reported gains. Their analysis also exposed substantial uncertainty in few-run rankings. The source provides the actual empirical study and its scope. [RLI, Section 3 and Figure 5](https://proceedings.neurips.cc/paper_files/paper/2021/file/f514cec81cb148559cf475e7426eed5e-Paper.pdf).

**Planning inference.** If a new method appears superior but the comparators use different checkpoint-selection rules, prioritize a matched-protocol comparison before expanding the method. An unresolved ranking calls for a defensible uncertainty analysis or a narrower claim. Bootstrap analysis needs enough relevant observations and cannot supply unobserved variability.

### New test data challenges an initial explanation

**Published evidence.** Recht and colleagues repeated dataset curation and compared many classifiers. New-set accuracy fell while relative model progress persisted. Their ImageNet sampling variants also changed measured accuracy. They argued that distribution differences better explained the pattern than their hypothesized adaptive-overfitting pattern. [IMG, Sections 2, 3 and 5, Table 2](https://proceedings.mlr.press/v97/recht19a/recht19a.pdf).

**Planning inference.** A drop on new data warrants investigation of sampling, label criteria and distribution. Retain competing explanations, then measure whether they predict different patterns across models and subsets. Preserve the observed negative result while revising its interpretation.

### An ablation redirects a mechanism claim

**Hypothetical example.** A retrieval method improves only when document deduplication changes. Hold preprocessing fixed and compare the method with and without its proposed component. If the component contributes no detectable improvement, retain the observed pipeline gain and revise the mechanism claim. Consider a factorial comparison if deduplication and the component may interact. The design rationale comes from factorial reasoning. No result is asserted here. [FACTOR](https://www.itl.nist.gov/div898/handbook/pri/section3/pri333.htm).

### A wide interval changes a null conclusion

**Hypothetical example.** A study estimates a gain of 0.2 percentage points with a 95 % confidence interval from − 2 to + 3 percentage points. A prespecified meaningful gain is 1 percentage point. The interval leaves a useful gain open. Report the result as inconclusive and assess a more precise authorized study. A claim of practical equivalence needs the planned bounds and a valid equivalence analysis. These values illustrate reasoning. [LAK](https://pure.tue.nl/ws/portalfiles/portal/80918653/lakeequi2017.pdf).
