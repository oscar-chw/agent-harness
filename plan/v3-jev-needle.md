## goal: Ship the v3 decision/evidence layer v0 — a JEV-pattern typed decision record (harness.jev-decision/v1) unifying how the harness records decisions (fail-closed: missing authority / unbound inputs / verdict outside enum all refuse; REA decisions expressible as a dependency-domain choice), retrofitted onto the real H6a ship-opt-in decision, PLUS a NEEDLE-pattern outcome table harvesting all hypothesis tracks (H1, H2, H3a, H3b, H4, H5, H6a, H6b, H6c, v2 node-4) into one hash-bound machine-readable artifact whose generation verifies every verdict doc/receipt on disk — additive, zero network, zero native/model calls, no commits

APPROVED 2026-11-11 — owner direction via the tasking session: "Continue the
v3 build-out: the decision/evidence layer — JEV typed-decision records +
NEEDLE outcome table, as one plan". Same conventions as v3-rea-support
(gated 7/7 on 2026-11-11): gates via the plan tool, /usr/bin/python3 for
pytest, no commits, zero network, zero native calls, additive amendments,
both-directions controls, self-redact plan-record lines after each gate,
tamper attestation for new test files, push tier green at the end.

Done-condition: /usr/bin/python3 .harness-work/v3-jev-needle/check_outcome.py
exits 0 — real generation verifies every track's bindings against the live
tree, regenerates byte-identically, and the tamper/missing-receipt controls
refuse — AND /usr/bin/python3 -m pytest -q tests/test_jev_decisions.py green
— AND the push tier passes with both new test files attested.

Context: JEV = Jev, TypeSafe AI's "System One" typed decisions
(docs/v3/harness-pillars-20261110.md, "REA / JEV resolved": Choice/Score/
boolean with confidence; REFLEX used it as a decision layer; ranked
adaptation #5: typed local gates, execute above confidence, escalate below;
calibration vendor-stated — we adopt the RECORD shape, not the model).
NEEDLE (docs/v3/oss-mechanics-20261110.md): explicit handler per outcome —
"if an outcome can happen, it has a handler"; applied here to hypothesis
outcomes: every track MUST appear in the table or generation fails.
Consistency: schema conventions follow harness.rea-record/v1
(docs/v3/rea-support-design-20261111.md, src/agent_harness/rea.py).

Non-goals: no Jev-model integration (records are filled by gates/humans, not
by a model pass); no routing engine change (routing.next_decision stays as
is; this is the record substrate for architecture-v3-draft §2.4, not the
policy engine); no live-corpus or production-flag change; no edits to any
verdict doc (the table BINDS their current bytes; later amendments take the
dated-amendment path).

## analysis

Done when: (a) the JEV gate (pytest tests/test_jev_decisions.py) exits 0 —
schema validation both directions plus the real H6a record verifying on disk;
(b) check_outcome.py exits 0 — all 10 tracks present, every binding sha256
re-verified, regeneration byte-identical, tampered-doc and missing-receipt
controls refuse, absent-row impossible asserted; (c) push tier green. Success
is fail-closed structure: a decision without recorded authority refuses, a
decision with unbound inputs refuses, a verdict outside its enum refuses; a
table whose source doc drifted refuses to regenerate.

## research

existing: checked `src/agent_harness/rea.py` (harness.rea-record/v1 — the
sibling schema this must stay consistent with: exact fields, ReaError,
binding kinds, verify_record), `src/agent_harness/loop_contract.py`
(verdict/promotion posture), `src/agent_harness/routing.py` (the existing
advisory next_decision with HOLD — the surface a v1 policy engine would
attach to), `scripts/build_outcome_table.py` does NOT exist yet (checked
scripts/: pipeline.py, tamper_guard.py only), the nine verdict/design docs
under docs/v3/ (h1 amendment, h2/h3/h4/h5/h6a/h6b/h6c), the per-track
receipts under .harness-work/v3-*/ (all listed and hashable), and
plan/v2-completion.md node 4 (still open — its campaign outcome lives in the
node record + docs/v2/retrieval-comparison-round-20261103.md). Prior art
(sweeps, read-only): Jev typed decisions + REFLEX decision layer (sweep 2),
NEEDLE outcome handlers + no_human attestation stance (sweep 3). Deferred:
any model-filled decision pass (vendor calibration unverified; zero model
calls in scope).

## plan

Acceptance tests, written before implementation: (a) tests/test_jev_decisions.py
covers every fail-closed rule both directions (intact record passes; missing
authority / empty inputs / verdict outside enum / bad confidence / bad
reversibility / empty unknowns / hash mismatch / missing receipt each refuse
with the named reason) plus REA-expressibility (the Lever pattern-only
decision encoded as domain=dependency kind=choice validates) plus the real
H6a record verifying on disk; (b) tests/test_outcome_table.py covers
generation from fixture registries in tmp roots: intact generates all rows,
mutated verdict doc fails generation, missing receipt refuses, a registry
dropping a track is caught by the row-completeness assert; (c)
check_outcome.py (node 6 gate) runs real generation, byte-identical
regeneration, and live-tree controls; (d) node 7 gate is the push-tier
wrapper (Amendment-1 pattern from v3-rea-support: assert push PASS on the
hash-bound receipt, FAIL=0, receipt verifies).

- [x] 1. Analyse: what the decision/evidence layer is, and what proves it done | gate: phase-check v3-jev-needle analysis
      2026-11-11T01:15:58Z exit 0 in 0s [448053e3] — phase analysis: OK (81 words)
- [x] 2. Research: existing decision surfaces and prior art, resolved or deferred | needs: 1 | gate: phase-check v3-jev-needle research
      2026-11-11T01:16:30Z exit 0 in 0s [1e87574d] — phase research: OK (119 words)
- [x] 3. Plan, with acceptance tests written before any implementation | needs: 2 | gate: phase-check v3-jev-needle plan
      2026-11-11T01:16:59Z exit 0 in 0s [fca1abff] — phase plan: OK (328 words)
- [x] 4. DESIGN: docs/v3/jev-decision-records-20261111.md (schema, fail-closed rules, REA consistency, H6a retrofit, execute/escalate policy field, NEEDLE outcome-table design) | needs: 3 | gate: /usr/bin/python3 .harness-work/v3-jev-needle/check_design.py
      2026-11-11T01:20:39Z exit 0 in 0s [5141a2fb] — design doc: OK (24 required elements present)
- [x] 5. JEV IMPLEMENTATION: src/agent_harness/jev.py + tests/test_jev_decisions.py + the real retrofit record docs/v3/jev/h6a-l2-candidacy-20261111.json | needs: 4 | gate: /usr/bin/python3 -m pytest -q tests/test_jev_decisions.py
      2026-11-11T01:26:11Z exit 0 in 0s [73c484e9] — .......................                                                  [100%] / 23 passed in 0.18s
- [x] 6. NEEDLE OUTCOME TABLE: docs/v3/outcome-tracks-20261111.json registry + scripts/build_outcome_table.py + tests/test_outcome_table.py + emitted docs/v3/outcome-table-20261111.md/.json, all bindings verified | needs: 5 | gate: /usr/bin/python3 -m pytest -q tests/test_outcome_table.py && /usr/bin/python3 .harness-work/v3-jev-needle/check_outcome.py
      2026-11-11T01:54:05Z exit 0 in 0s [5b637f8a] — OK    tampered verdict doc: refused with DRIFT, nothing emitted / OK    missing receipt: refused with MISSING, no row skipped silently / VERDICT: PASS (real tree verified + byte-identical regeneration; tamper and missing-receipt controls refuse)
- [x] 7. Verdict note docs/v3/jev-needle-v0-verdict-20261111.md + hygiene: tamper attestations for both new test files, plan-record self-redaction, push tier green | needs: 6 | gate: /usr/bin/python3 .harness-work/v3-jev-needle/check_push_tier.py
      2026-11-11T02:07:06Z exit 0 in 30s [7f542c66] — verdict: INCOMPLETE (FAIL=0 NOT_RUN=5) / verify: OK / VERDICT: PASS (push tier green: tamper guard + ruff + secret-scan all exit 0; receipt run-20261111T020635Z-8ba349f1.json verifies; run verdict INCOMPLETE with FAIL=0 is the runner's documented partial-run posture)
