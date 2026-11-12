# DQ1 — v2 node 4 terminal red: decision brief

2026-11-11. Informs owner decision DQ1 of `docs/v3/session-bridge-20261111.md`
(v2-completion nodes 5–8). Evidence is hash-bound under
`.harness-work/v2-completion/matched-usage-20261110/`; the decomposition doc
(`token-decomposition-20261110.md` there) is the primary analysis. This brief
decides nothing.

## What is blocked

Node 4 ("Qualify source-to-claim retrieval, correction and cross-session
handoff on real local content") is terminally red. Nodes 5–8 need it:

- 5 — independent learning evaluation, held-out quality + complete usage
- 6 — proportional native task behavior and token outcome vs frozen baseline
- 7 — integrated release-candidate review
- 8 — installed-client / device verification with rollback

v2-completion stands at 51/56: everything else is done and gated.

## What was measured

Matched-usage campaign (frozen prompts, model, effort, sandbox, MCP env,
argv; config hash checked before/after every call): 4 cases × 2 arms, 8
sealed model calls, 12 attempts / 11 model-reaching of a 16-call cap.

Aggregate: candidate 124,536 vs base 113,681 total tokens = **+10,855
(+9.55%)** → the node-4 token gate FAILED.

## Why the FAIL is confounded (decomposition, hash-bound)

Every model-visible input component was inventoried from the preserved
rollouts; a three-parameter least-squares fit reproduces all eight sealed
input totals with max residual 78 tokens (0.26%), so no unexplained input
component exists.

- The ambient Codex skills/plugin snapshot (`skills_instructions`)
  flip-flopped between calls minutes apart: 14,717 vs 38,794 chars (sequence
  A A B A A B B B). It is not campaign content and not either arm's
  treatment; all frozen conditions held byte-identically — the drift sits
  outside them.
- Cases 2 and 4 landed candidate-on-big / base-on-small: token-confounded.
  Cases 1 and 3 are clean matched pairs.
- ≈105% of the aggregate excess (+11,398 est of +10,855) is that ambient
  drift. On the controlled component (prompt payload + output), the
  candidate is **−306 tokens (≈ −0.27%)** — no treatment regression. The
  candidate payload is in fact 5,579 chars *smaller* than the base's across
  the campaign.
- Decomposition verdict (question 3): **NO** bounded candidate-side change
  can offset the excess; deleting the entire candidate payload could not.
  Chasing it would be manufacturing a fix against a confound.

## Why it cannot be re-measured today

- Instrumentation: codex CLI 0.167.0-alpha.3.2 emits exactly one
  `token_count` record for a one-shot exec turn; the frozen instrument needs
  ≥ 2 anchors per sealed window. Pilot-era 0.165 sealed cleanly (9 surviving
  rollouts). No in-mandate restructure exists (multi-turn, warm-up, forced
  second request all break completeness or comparability).
- The v2 ambient-pinned re-run aborted fail-closed at call 3: the variant
  drifted within 72 s and no CLI-side pin exists
  (`TERMINAL_V2_ABORTED_AMBIENT_VARIANT_MISMATCH`). Amendment-2 froze the
  remaining 5 of 16 calls.

## The decision (nodes 5–8)

**(a) Accept-annotated.** Annotate `matched_context` with the confound
finding and amend node 4's gate semantics to "no candidate-side regression
on the controlled component" (which passed at −0.27%), then proceed 5–8.
Defensible only because the decomposition *proves* the failure is ambient
with hash-bound evidence — but it amends a failed gate after measurement,
which is precisely the move the harness's gates exist to prevent. Sets a
precedent the tamper guard and settlement hooks argue against.

**(b) Leave red — recommended.** Node 4 stands as the recorded, hash-bound
disconfirmation: v2's measurement demand (complete sealed usage under an
ambient the campaign does not control) is unattainable in this environment.
That artifact is the standing justification for v3's evaluation architecture
(owned fixtures, controlled ambient, pipeline tiers). Nodes 5–8 must not
silently vanish: their substance maps to living items — 5's held-out
learning evaluation was exercised by the H5/H6 tracks on frozen corpora;
6's token-proportionality question re-opens as a v1 item under a
harness-owned ambient (the pin v2 lacked); 7's release review was exercised
by the dev9 staging (audit + rollback rehearsal); 8's device verification
stays owner-side. Anything not mapped stays explicitly open.

**(c) Re-measure.** Requires an ambient pin (isolated CODEX_HOME or a CLI
with a stable skills snapshot) and 8 fresh calls — both arms, since a
candidate-only re-run breaks matching against the drift-exposed sealed base.
Not possible today (72 s drift, no pin). Re-openable any time the ambient
becomes pinnable; the 5 frozen slots stay frozen regardless.

## Recommendation

**(b)** — with the node 5–8 substance re-homed as named above, and the
token-proportionality question carried as an explicit v1 measurement item
rather than abandoned. The campaign's cost (11 model-reaching calls) bought
the strongest possible evidence for exactly this shape of conclusion.

## Evidence index (all hash-bound)

`results.json` (campaign outcome + diagnosis) · `token-decomposition-20261110.md`
(component inventory, fit, per-case answers, verdict) ·
`receipts/decomposition-hashes.json` (8 rollouts + 8 attempt receipts,
sha256) · `freeze.json` (current freeze, v3) + superseded v1/v2 freezes ·
`amendment-20261110.md`, `amendment-2-20261110.md` (call-cap freeze) ·
`usage-ledger.json` (seals and totals) · `main-review.json` (grading).
