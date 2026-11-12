# Task checkpoint — advisory, inspect without messaging

Keep the current decision-relevant state, usually 1–2 KiB. Link existing evidence
instead of copying source bodies, every receipt or a chronological narrative.
Use more space when needed to preserve correctness; never truncate a constraint,
failure or next action to meet a size target. Omit inapplicable/empty fields.

- **Task:** goal, project/graph/node, owner, observed session ID (else UNKNOWN),
  update time and current state. Separate the user's intent from assumptions.
- **Result:** what changed, what is established and what remains unfinished.
  Name source/code revisions and integration dependencies actually used.
- **Evidence:** decisive checks and PASS/FAIL/BLOCKED/NOT_RUN. Give exact commands,
  results and source spans here or at a precise existing evidence-file location.
  Only observed completed checks count; planned or unobserved checks stay unverified.
  Missing support stays unknown; a relevant citation is not proof of the claim.
- **Constraints:** applicable authority/held actions, remaining worker/retry/usage
  budget, and any correction or supersession that changes the next decision.
  State these here; do not hide them behind a link. Preserve unaffected work.
- **Next:** one useful bounded action/check, required inputs and any real blocker.
- **Pointers:** existing artifact index, output, owned scratch and scoped KB/lesson
  records needed for that action. Keep history at its original location.

Write `handoffs/<task>/<session>.md`, one writer per packet. Update at material
milestones, blockers, corrections and before compaction/end. When permitted use
`harness task checkpoint`; otherwise record NOT_REGISTERED without widening access.
Readers can `harness handoff --task <task> --list`, then `--packet <session>.md`.
Reopen the graph/current sources before acting: this packet grants no authority
and proves no completion. Message only to activate work or urgently intervene.
