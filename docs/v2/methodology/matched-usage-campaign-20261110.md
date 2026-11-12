# Matched whole-usage comparison campaign — design for authorization

2026-11-10. DESIGN ONLY — no native calls made. This is the last open obligation of
plan/v2-completion node 4 and the gatekeeper for nodes 5–8. It costs real tokens;
nothing here runs without explicit owner authorization.

## What it must close (gate: check_retrieval.py comparison block)

1. whole aggregate usage UNKNOWN/INCOMPLETE → both arms fully instrumented
2. matched model/effort/tools/budget/source visibility NOT_VERIFIED
3. per-case quality/scope/correction nonregression NOT_VERIFIED
4. complete positive token measurements missing; gate requires candidate <= base

## Design

- **Frozen context**: reuse `.harness-work/retrieval/comparison/prepare.py`'s
  4-question calibration freeze; extend only if coverage is demonstrably thinner
  than the 16-case corpus (record why). No edits after freeze.
- **Arms**: base = lexical-window reader (raw_windows.py, existing); candidate =
  current source-review/scoped retrieval reader. Same questions, same rubric.
- **Matched conditions**: identical model, effort, tool list, token budget,
  source visibility. Any deviation invalidates the run and is recorded as such.
- **Instrumentation**: sealed usage windows via src/agent_harness/native_usage.py
  `inspect_window`, per docs/v2/methodology/native-usage-windows-20261106.md —
  including failed attempts, retries and orchestration. "UNKNOWN is never zero":
  any uninstrumented segment keeps usage_complete=false and the gate stays red.
- **Quality nonregression**: per-case quality/scope/correction rubric frozen
  before the run; graded against frozen answers, not vibes.
- **Evidence**: frozen_context, usage_ledger, main_review bound by hash into
  retrieval-results.json; PASS requires candidate <= base tokens.

## Cost bound (decision input)

- 4 questions × 2 arms × 1 run = 8 native calls minimum; +1 rerun per arm if a
  boundary check fails (cap: 16 calls total, hard stop).
- Model/effort: the same fixture-class settings used in prior bounded native
  runs (fixture-model class, high effort, 5 s timeout equivalents).
- Prior bounded native work consumed on the order of 10⁴–10⁵ tokens total
  (46,142 input+output for the last two-call development stage); this campaign
  is estimated at the same order, capped by the call bound above.

## Outcome semantics

- PASS (candidate <= base, quality nonregression): closes node 4, unblocks 5–8.
- Honest FAIL on tokens (like the +21.17% pilot): keeps node 4 red and becomes
  the primary evidence for the v3 H1/H2 work — consolidation + learned ranking
  exist precisely to reverse that regression. A failed campaign is not wasted;
  it is the measurement that justifies v3's memory economics.
- FAIL on instrumentation gaps: design fault, fix and re-run within the call cap.

## Explicitly not in this campaign

No promotion, no install, no production config change, no benchmark-savings
claim. Development-only measurements on frozen cases.

AUTHORIZATION: reply "campaign authorized" (optionally with a lower call/token
cap). Until then this document is the complete preparation; execution is one
bounded slice away.

AUTHORIZED 2026-11-10 — owner approval in the Kimi Work harness session
("approve necessary experiments, you have my full approval"). Hard cap stands:
≤16 native calls; any instrumentation gap stops the run, not papers over it.
