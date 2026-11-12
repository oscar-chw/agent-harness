# V2 benchmark campaign

Status: **end-to-end qualification is unfinished**. A local LongMemEval retrieval
component run is recorded in [the results](RESULTS.md); official QA and leaderboard
scores remain NOT_RUN. Passing unit tests or one handoff reader is not a score.

| Capability | Benchmark to qualify | Why include it | Current admission gap |
|---|---|---|---|
| Repository repair | [SWE-bench Verified](https://www.swebench.com/SWE-bench/guides/evaluation/) | Real patches and repository tests | Pin dataset/images; qualify native worker and official grader |
| Terminal work | [Terminal-Bench 4.0](https://www.tbench.ai/run) | Current terminal-task campaign | Official current runner includes GPU tasks; no paid cloud allocation granted |
| Historical terminal comparison | [Terminal-Bench 2.0](https://www.tbench.ai/?version=2.0) | Separately labelled historical comparability | Pin task pack; never combine its score with 4.0 |
| Skill benefit | [SkillsBench 1.1](https://www.skillsbench.ai/) | Paired with/without skills | Pin upstream and validate skill-loading instrumentation |
| Long-term memory | [LongMemEval](https://github.com/xiaowu0162/LongMemEval), [V2](https://github.com/xiaowu0162/LongMemEval-V2) | Separate memory task sets | Pin each variant, retrieval and official scoring route |
| Conversational recall | [LoCoMo](https://github.com/snap-research/locomo) | Complementary recall tasks | Freeze variants and provided versus regenerated summaries |
| Research | [DeepResearch Bench](https://github.com/Ayanami0730/deep_research_bench) | Reports and citation-grounding evaluation | Default evaluators require service keys; native-only replacement must be labelled adapted |
| Tool use | [BFCL V4](https://gorilla.cs.berkeley.edu/leaderboard.html) | Function selection and arguments | Pin upstream; separate model API capability from harness effects |
| Stateful interactions | [tau2-bench](https://github.com/sierra-research/tau2-bench) | Agent/user interaction | Qualify both roles and count both; default API setup is not authorized |
| Our actual failures | Original16 + guard/recovery/learning regressions | Corrected sources, scope, restart and false completion | Original gates remain authoritative and unfinished |

These are complementary tests, not interchangeable rankings. SWE-bench Lite may
be a setup smoke but is not an independent win over an overlapping Verified set.
A broad coverage review must also consider browser/GUI, security, test-honesty and
maintainability benchmarks before claims in those areas. They are not declared
supported or passed by omission. Pure model-knowledge exams cannot establish a
harness improvement.

## Frozen comparisons

Before inference, pin harness commit/build, native client, model, effort, service
tier, task/data/grader hashes, environment, permitted tools and source visibility.
Choose task IDs independently of results. Keep development and held-out tasks
separate; do not tune on the held-out set. Compare current native workflow,
frozen previous harness, candidate, and a minimal workflow where configuration
can be isolated without removing valid safety controls. Claude runs stay NOT_RUN
under the current no-Claude instruction.

Start with upstream oracle/setup checks and a tiny prespecified sample, then a
representative sample, then the approved full run. Preserve setup failures,
timeouts and consumed attempts separately from task-quality findings. No quiet
retry, favourable task substitution, or changing the evaluator after seeing a
loss. Smoke results must be called smoke results.

## Cost and claims

The original rule stays: quality at least baseline in every required task class,
AND aggregate tokens at most baseline. Count all native agents, inference inputs,
outputs, retries, injected context, retrieval/compaction and amortized indexing/
maintenance. Cached and reasoning counts are subsets, not discounts or additions.
Unknown usage stays unknown and blocks a savings/promotion claim. Show quality,
latency, coverage, failures, safety and total tokens together with uncertainty.

Use official graders when possible. An adapted judge/provider/task pack gets a
separate label, not an official leaderboard comparison. Native subscription
login stays on its normal client; do not export credentials to benchmark code.
Docker/GPU requirements belong to benchmark environments, not everyday harness
use. No cloud purchases, host network changes, uploads or leaderboard submission
are authorized by this plan. Prepare exact artifacts/resource estimates before
requesting any necessary long-run/resource approval.

## Publication

The final release candidate must be frozen and measured after the fixes. A later
implementation change requires a new affected comparison; do not reuse the old
score under the new version. Earlier failures and consumed development attempts
remain in the result history.

Publish the exact result manifest, task IDs, reproduction commands, raw outcome
categories, environment and known limitations after privacy and release gates.
A README must distinguish structural tests, local native checks, public smoke,
full official runs and measured harness contribution. Until then: **NOT_RUN**.

## Memory backend comparison

Compare the shipped lexical search with QMD's keyword-only and hybrid search on
the same frozen, label-free source projection and questions. QMD is a candidate
backend, not a replacement for authority, source freshness or recovery controls.
Its [pinned documentation](https://github.com/tobi/qmd/blob/86d2365d17fc682e491c2c53d1e4a884aee8682a/README.md)
describes vector retrieval, reranking and query expansion, with default model
downloads of roughly 2 GB before dependencies and index storage. Those are
documented features and estimates, not measurements on our tasks. No QMD install,
model download or head-to-head result is claimed.

Use only each trial's explicit source scope; never index the owner's whole home
directory. Keep answer labels outside the retriever, enforce the same output
budget, resolve results to exact original source lines, and test stale/out-of-scope
negative controls. Measure session recall, evidence coverage and final answer
quality separately. Count index/model setup, storage, cold/warm latency and all
local and native inference work; a free local model still has resource costs.
Cases used to repair the adapter are development data. Reserve fresh cases for
the final comparison and retain errors without favourable substitutions.
