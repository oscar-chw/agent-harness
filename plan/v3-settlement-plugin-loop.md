## goal: Ship the v3 final-sweep build-out v0 — Pi-style settlement hooks (an action is not done until its settlement receipt closes: a fail-closed checker scans plan/workgraph activity for done-nodes whose gate receipts never closed; unsettled ≠ settled) PLUS the DSH plugin admission loop (discovery → qualification: an REA record is REQUIRED → typed decision: a JEV domain=adoption record is REQUIRED → admission: no REA record refuses, no JEV decision refuses, below-threshold confidence escalates, never auto-admits) with a hash-bound registry, retroactively processing the Lever pattern capability whose REA record already exists — additive, zero network, zero native/model calls, no commits

APPROVED 2026-11-11 — owner direction via the tasking session: "Final sweep
build-out: Pi-style settlement hooks + the DSH plugin loop, as one plan".
Same conventions as v3-rea-support and v3-jev-needle (both gated 7/7 on
2026-11-11): gates via the plan tool, /usr/bin/python3 for pytest, no
commits, zero network, zero native calls, additive amendments,
both-directions controls, self-redact plan-record lines after each gate,
tamper attestation for new test files, push tier green at the end.

Done-condition: /usr/bin/python3 .harness-work/v3-settlement-plugin-loop/check_settlement.py
exits 0 (the three v3 plans scan with zero unsettled done-nodes, and the
fabricated-done / tampered-receipt controls refuse) AND
/usr/bin/python3 .harness-work/v3-settlement-plugin-loop/check_plugin_loop.py
exits 0 (the Lever pattern capability admits with full receipts; the
no-REA / escalated-verdict / tampered-record controls refuse) AND both new
pytest suites green AND the push tier passes with both new test files
attested, run with the settlement opt-in flag exercised against the v3
plans.

Context: Pi (docs/v3/oss-mechanics-20261110.md): "awaited subscribers count
toward run settlement → a hook can reliably gate progress"; the sweep's
adaptation note: our pytest gates ARE awaited subscribers blocking
settlement — v0 makes settlement itself auditable: a done-mark without a
closing receipt is reported, never assumed. DSH: everything is a plugin the
kernel mounts; v0 adopts the ADMISSION discipline for external
capabilities, not the Cordis runtime (rejected per the sweep). Consistency:
schema/validator idioms follow src/agent_harness/rea.py and
src/agent_harness/jev.py (exact fields, fail-closed, on-disk verification
separate from pure validation, promotion always NOT_GRANTED).

Non-goals: no new pipeline tier (the receipt schema pins TIER_ORDER; a
seventh tier would invalidate verify() for every historical receipt —
settlement is wired as an opt-in flag that appends to the push tier only
when explicitly requested, default byte-identical); no workgraph/plan.py
core change (the redaction-under-MCP leak found during design probing is
documented for v1, not fixed here — changing signature inputs repo-wide is
its own workstream); no model-filled decisions; no live admission of any
capability beyond the one retroactive Lever example; no registry daemon
(the registry is emitted by a script, like the outcome table).

## analysis

Done when: (a) tests/test_settlement.py and tests/test_plugin_loop.py are
green under pytest AND unittest; (b) check_settlement.py settles every done
node in the three v3 plans (fabricated-done and tampered-receipt tmp
controls refuse); (c) check_plugin_loop.py admits the Lever pattern with
hash-bound REA+JEV records (no-REA, escalated-verdict, tampered-evidence
controls refuse); (d) push tier green via the wrapper, with the pipeline's
settlement opt-in exercised. Success is fail-closed structure: a done-mark
without a verifiable receipt is reported unsettled (UNKNOWN is never zero);
an admission without an REA record refuses; a below-threshold JEV verdict
escalates and never auto-admits.

## research

existing: src/agent_harness/workgraph/plan.py (the workgraph: node lines,
NOTE_RE exit-lines with 8-hex gate signatures, per-node record files with
fenced Attempt bodies; gate_signature = sha1 over the redacted, normalised
WHOLE output; probed live: stored body + "\n" reproduces the signature on
all v3-jev-needle nodes except where post-gate sed redaction mutated the
bytes — the checker needs an inverse-redaction candidate set, tokens sourced
from the runtime environment so no identifier is stored), src/agent_harness/
rea.py + docs/v3/rea/lever-20261105.json (the existing qualification record,
pattern-only decision, verified on disk), src/agent_harness/jev.py +
docs/v3/jev/h6a-l2-candidacy-20261111.json (the adoption-decision record
shape to reuse), scripts/pipeline.py (TIER_ORDER pinned by the receipt
schema; main() additive flag is the safe wiring; tests/test_pipeline_runner.py
injects stub registries and tolerates it), .harness-work/eval-pipeline
-20261110/runs/ (the v3-rea-support push receipt to bind as the JEV
receipt). Prior art (sweep 3, read-only): Pi settlement subscribers, DSH
plugin mounts, NEEDLE outcome handlers, no_human attestation. Deferred:
plan.py redaction-under-MCP root/home resolution (v1).

## plan

Acceptance tests, written before implementation: (a) tests/test_settlement.py
over fixture plans in tmp roots: a done node with note + record + matching
signature settles (both directions: intact settles, fabricated done-mark
without receipts is reported unsettled, a tampered record body fails
signature verification, an open node is listed but never fails, a missing
record file fails); (b) tests/test_plugin_loop.py over fixture
REA/JEV/candidate files in tmp roots: intact pipeline admits and emits a
hash-bound registry entry; admission without an REA record refuses; a JEV
verdict below the policy threshold escalates and refuses; a verdict
mismatch refuses; a tampered REA/JEV file refuses at hash binding; (c)
check_settlement.py (node 5 gate) scans the three v3 plans plus tmp-skeleton
controls; (d) check_plugin_loop.py (node 6 gate) runs the real Lever
admission plus tmp-skeleton controls; (e) node 7 gate is the push-tier
wrapper (Amendment-1 pattern) extended to exercise pipeline --settle.

- [x] 1. Analyse: what settlement + plugin admission are, and what proves them done | gate: phase-check v3-settlement-plugin-loop analysis
      2026-11-11T02:28:01Z exit 0 in 0s [126b59e2] — phase analysis: OK (89 words)
- [x] 2. Research: existing plan/workgraph/pipeline surfaces and prior art, resolved or deferred | needs: 1 | gate: phase-check v3-settlement-plugin-loop research
      2026-11-11T02:28:19Z exit 0 in 0s [bd214afb] — phase research: OK (145 words)
- [x] 3. Plan, with acceptance tests written before any implementation | needs: 2 | gate: phase-check v3-settlement-plugin-loop plan
      2026-11-11T02:28:33Z exit 0 in 0s [c7498a34] — phase plan: OK (347 words)
- [x] 4. DESIGN: docs/v3/settlement-plugin-loop-design-20261111.md (settlement record schema, signature re-derivation rule, pipeline opt-in wiring decision, admission loop stages, registry schema, Lever example) | needs: 3 | gate: /usr/bin/python3 .harness-work/v3-settlement-plugin-loop/check_design.py
      2026-11-11T02:34:23Z exit 0 in 0s [fd05c145] — design doc: OK (32 required elements present)
- [x] 5. SETTLEMENT IMPLEMENTATION: src/agent_harness/settlement.py + scripts/check_settlement.py + pipeline --settle opt-in + tests/test_settlement.py | needs: 4 | gate: /usr/bin/python3 -m pytest -q tests/test_settlement.py && /usr/bin/python3 .harness-work/v3-settlement-plugin-loop/check_settlement.py
      2026-11-11T02:49:44Z exit 0 in 0s [326fda2b] — OK    fabricated done: reported failed, exit 1 (unsettled ≠ settled) / OK    tampered receipt: verification failed, exit 1 / VERDICT: PASS (real plans settle; fabricated-done and tampered-receipt controls refuse)
- [x] 6. PLUGIN LOOP IMPLEMENTATION: src/agent_harness/plugin_loop.py + scripts/admit_capability.py + docs/v3/jev/lever-pattern-adoption-20261111.json + candidate + registry + tests/test_plugin_loop.py | needs: 5 | gate: /usr/bin/python3 -m pytest -q tests/test_plugin_loop.py && /usr/bin/python3 .harness-work/v3-settlement-plugin-loop/check_plugin_loop.py
      2026-11-11T03:05:07Z exit 0 in 0s [34cf24af] — OK    below-threshold confidence: ESCALATED, refused, never auto-admitted / OK    tampered REA record: refused at the declared hash / VERDICT: PASS (Lever pattern admitted with full receipts; no-REA, escalation and tamper controls refuse)
- [x] 7. Verdict note docs/v3/settlement-plugin-loop-v0-verdict-20261111.md + hygiene: tamper attestations for both new test files, plan-record self-redaction, push tier green with --settle exercised | needs: 6 | gate: /usr/bin/python3 .harness-work/v3-settlement-plugin-loop/check_push_tier.py
      2026-11-11T03:21:14Z exit 0 in 30s [2f3f4d2e] — verdict: INCOMPLETE (FAIL=0 NOT_RUN=5) / verify: OK / VERDICT: PASS (push tier green: tamper guard + ruff + secret-scan + settlement scan over 3 plans all exit 0; receipt run-20261111T032044Z-ccefefce.json verifies; run verdict INCOMPLETE with FAIL=0 is the runner's documented partial-run posture)
