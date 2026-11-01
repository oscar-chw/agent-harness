# Source-grounded editing candidate: held

26 October 2026. This is a dormant research candidate, not an installed skill
or evidence that prose can be made detector-proof. The method is an original,
reader-focused synthesis; no upstream code was copied. The
[blader/humanizer](https://github.com/blader/humanizer) and
[shir-danishyar/humanize](https://github.com/shir-danishyar/humanize) projects were inspected as
references for editing patterns and register awareness. Their popularity or
claims do not establish a benefit in this harness.

The frozen synthetic case uses the [Linux Foundation's 22 October 2026 AAIF
announcement](https://www.linuxfoundation.org/press/agentic-ai-foundation-announces-four-new-projects-agent-skills-open-responses-openenv-and-opensandbox).
It tests a supported announcement, a contradicted Alibaba contribution, an
unsupported 30% coding claim, fabricated first-person attendance, an unlisted
study citation, and a memory-loss assertion beyond the source. The supplied
source packet is an offline excerpt, not proof that a model visited the URL.

An exploratory paired run used the same installed Codex model and user task in
two ephemeral, read-only sessions. The only prompt addition in the candidate
arm was the skill body. The control prompt SHA-256 began `fd7d2e90c87a4ff7`;
the candidate prompt began `e4a90dd6e88e7ec2`. Both outputs marked the six
cases correctly, removed the unsupported assertions, and preserved the
qualification. The control reported 56,061 input tokens (35,584 cached), 774
output and 326 reasoning; the candidate reported 69,046 input (33,920
cached), 907 output and 503 reasoning. Cache differences and one case prevent
a precise causal token estimate. The tested prompt also preceded a later
description-only edit, so this is not a qualification of the file now here.

**Decision: do not install or auto-trigger.** No material quality gain was
observed, and the candidate did not meet the strict aggregate-token rule. A
future attempt needs more held-out, source-accessible cases, an independent
claim-support grader, a matched baseline, and a measured gain before release.
For urgent work, ask the existing agent to verify every adjacent citation and
fact against the source it can actually open; mark unavailable evidence rather
than inventing a source. This is a task instruction, not a new harness feature.
