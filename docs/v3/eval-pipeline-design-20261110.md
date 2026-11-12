# Evaluation pipeline design — 2026-11-10

Input: `.harness-work/eval-pipeline-20261110/inventory.json` (11 surfaces, 11 absent,
counts re-derived and gated). Constraints (owner directive + repo reality): stdlib-only
runtime, Python ≥ 3.9, local-first (no hosted service required to produce evidence),
zero native/model calls in any gated path, no commits from the agent, existing tests /
gates / configs orchestrated READ-ONLY.

Measured facts that shape this design: the full suite (`pytest -q tests eval`,
2,569 collected) exceeds **300 s wall** on this machine — timed out twice at 300 s and
290 s (the second run excluded the 6 integration-marked tests, so the time is spread
across the ordinary suite, not concentrated in the integration marks). Push-time
checks must therefore be a separate, fast tier; "just run the suite" is not a
pre-push answer.

## The six tiers, fixed order

`push → unit → integration → e2e → perf → ship`

| # | tier | question it answers | EXISTS (inventory ids) | missing | local command(s) |
|---|------|----------|------------------------|---------|------------------|
| 1 | push | clean enough to leave this machine? | `standards-ruff` (ruff.toml, hosted lint.yml), `scripts-check-suite` (secret-scan.sh) | ruff in NO local flow (check.sh omits it; lint.yml is hosted-only); nothing runs before push | `python3 -m ruff check --config ruff.toml .`; `bash scripts/secret-scan.sh --tree-only` |
| 2 | unit | are the components correct? | `tests-suite` (141 files, 2,569 collected), free part of `eval-instrument` | tier marks not self-applied (no root pytest.ini); no declared fast subset of a >300 s suite | `/usr/bin/python3 -m pytest -q tests eval` |
| 3 | integration | do the boundaries hold? | 6 integration-marked tests in `tests-suite`; `deploy-audits` cross the install boundary | marks unregistered at repo root — `-m integration` is convention, not enforcement | `/usr/bin/python3 -m pytest -q tests -m integration` |
| 4 | e2e | does a real journey work end to end? | `scripts-check-suite` demo.sh (throwaway-home install + guard smoke); paid arm of `eval-instrument` (manual, spends model usage) | no no-model journey beyond install smoke; the paid arm can never be a gate | `bash scripts/demo.sh` |
| 5 | perf | is it still fast enough? | `benchmarks` measures retrieval QUALITY, not code perf; one ad-hoc read-budget measurement (18,944 → 400 bytes) | the entire tier: no baseline, no thresholds, no regression detection | none — empty tier, reports NOT_RUN |
| 6 | ship | may this leave the building? | `ci-github` (hosted ci.yml + lint.yml), `deploy-audits` (hash-bound, rollback), `plan-gating` per-node receipts, `loop-contract` schema precedent | no local receipted pipeline; no promotion chain consuming receipts; hosted CI not reproducible locally as one command | receipt assembly + verdict; hosted adapter LATER |

## Tier details

### Tier 1 — push

Fast (< ~60 s), local, pre-push. ruff correctness lint plus the tree-only secret
scan. The full history scan stays in `scripts/check.sh` and the hosted adapter —
history does not change between local pushes, so tree-only locally is not a weakened
gate, it is the same gate scoped to what changed.

### Tier 2 — unit

The whole collected suite, unmodified. Its >300 s latency is a measured fact of the
suite, not a defect this plan fixes; scoping to the files a change owns remains a
per-plan-node gate convention (the tiers template's lesson), and a declared fast
subset is future work, not sneaked in here.

### Tier 3 — integration

`-m integration` over `tests/`. Six tests today; the tier exists so the number can
only grow. Applying the four-tier marker scheme to this repo (root pytest.ini with
`--strict-markers`) is deliberately NOT in this plan — it modifies existing config
and belongs to its own gated node.

### Tier 4 — e2e

`scripts/demo.sh`: a real install into a throwaway home, `doctor`, and the guard
blocking a catastrophic command. The model-in-the-loop eval stays manual and paid;
it is an evaluation campaign, not a pipeline gate.

### Tier 5 — perf

Empty today. An empty tier reports NOT_RUN and makes the run INCOMPLETE — never a
pass (the repo's own tiers/pytest.ini lesson: an empty tier failing is deliberate).
First candidates when this tier is filled: KB read latency, guard overhead per
command, MCP round-trip latency — each needs a baseline and a pre-registered
threshold before it may gate.

### Tier 6 — ship / CI-CD

No new execution. Assembles the run's verdict from the tier receipts, records tree
state (git HEAD + dirty flag), and answers promotion eligibility. Deploy audits stay
the mechanism (hash-bound, `.runtime-backups` rollback); promotion stays human.
The `workgraph-gate-scripts` category (43 `check*.py` across workstreams) stays
change-scoped: they are per-plan-node gates invoked by the `plan-gating` surface,
not absorbed into the runner; ship-tier evidence references plan-gate outcomes, and
the `gate-scripts` category is where new evidence-style checks (like this plan's
own) keep landing.

## Gaps ranked by risk

1. **No fail-closed local pipeline with evidence (ship).** Every surface exists on
   its own; nothing demonstrates the chain. check.sh omits ruff and writes no
   receipt, so "it was green" is currently unprovable locally. Risk: silent
   regression ships behind sincere but unverifiable green claims.
2. **Push tier effectively absent locally (push).** ruff runs hosted-only; the
   secret scan runs only when someone remembers check.sh; nothing fires before
   `git push`. Risk: defects and secrets reach origin before any gate.
3. **Perf tier absent entirely (perf).** No baseline for KB read latency, guard
   overhead, or MCP round-trips; the one perf-ish measurement on record was ad hoc.
   Risk: perf regressions are invisible until a deploy audit happens to catch one.
4. **Tier marker scheme not self-applied (unit/integration).** case/property/eval
   marks unused, integration a convention; without `--strict-markers` a typo'd mark
   selects nothing and reports green over zero tests.
5. **E2E thin without models (e2e).** demo.sh is an install smoke, not a user
   journey; the real eval is paid and manual.
6. **Suite latency >300 s with no declared fast subset (unit).** Slow suites get
   skipped; skipped suites are absent suites.

## Coding standards

**Choice: ruff remains the single enforced tool**, moved into the LOCAL push tier.
Rationale: already configured (`ruff.toml`), zero runtime dependencies, one static
binary, fully offline, py3.9-compatible, version-pinned in lint.yml (0.16.10) and
available locally (0.16.3 via `/usr/bin/python3 -m ruff`). Rule set stays **E9 + F**
(correctness only) — widening rules (I/UP/B/…) is a separate gated decision because
it rewrites many files at once, and this plan touches no existing config.

**Formatter: rejected.** README and docs cite source line numbers; a formatter
rewrapping code silently rots every citation (ruff.toml documents this). Style stays
a review concern, not a machine rewrite.

**Typechecker: deferred.** mypy/pyright would be the first heavyweight non-stdlib
dev tool here and the codebase has no annotation culture; structural validation
(`loop_contract.py`'s `_require` checks) already carries part of the contract load.
Revisit if the public contract surface grows.

**Secret hygiene stays in push**: `secret-scan.sh --tree-only` locally, full
history scan in check.sh and the hosted adapter. Both directions of its
`--self-test` remain the control.

The `standards-skills` surface (content/skills/standards — test tiers, the eight
properties of a real gate, vacuous-test shapes) remains the process bar every gate
in this pipeline is written against; it is enforced by review, not by the runner.

## CI/CD, local-first

The **local runner is the CI**. One entry point — `python3 scripts/pipeline.py` —
runs the tiers in fixed order, fail-fast, and writes one hash-bound receipt per run
(`harness.pipeline-receipt/v1`) under `.harness-work/eval-pipeline-20261110/runs/`.
A green receipt is the unit of evidence; "green" without a receipt does not exist.

**Hosted CI is a later adapter, not a source of truth.** The `ci-config` category
(ci.yml and lint.yml) stays as the hosted smoke; a future workflow should call the
same `scripts/pipeline.py` entry point and archive the receipt it emits, so hosted
and local evidence are the same artifact. This plan wires nothing hosted.

**CD stays human.** The ship tier computes promotion eligibility from receipts;
deploy audits remain the hash-bound mechanism with rollback; nothing auto-deploys.

## Runner contract

- `python3 scripts/pipeline.py` — all six tiers, fixed order, fail-fast.
- `python3 scripts/pipeline.py --tier push [--tier unit …]` — subset, still in
  fixed relative order.
- `python3 scripts/pipeline.py --list` — print the tier registry.
- `python3 scripts/pipeline.py verify <receipt.json>` — recompute every hash and
  the verdict; refuse tampering.
- Exit codes: 0 PASS, 1 FAIL, 2 INCOMPLETE, 64 usage.
- Receipt: `{schema, run_id, started_utc, repo:{root, git_head, tree_dirty},
  tiers:[{name, status, commands:[{argv, exit, duration_s, stdout_sha256,
  stderr_sha256, artifacts:{path: sha256}}]}], verdict, receipt_sha256}` — statuses
  PASS / FAIL / NOT_RUN; any FAIL ⇒ run FAIL (later tiers NOT_RUN); any NOT_RUN
  with none FAIL ⇒ INCOMPLETE. Stdlib only, py3.9-compatible, per-tier timeout
  budgets (a hung tier is a FAIL, not a skip).

## Non-goals

No hosted-CI wiring; no formatter; no root pytest.ini or other existing-config
changes; no modifying existing tests/gates/scripts; no perf thresholds yet (the tier
exists, its commands are a later node); no auto-deploy.

## Amendment 1 — 2026-11-10: recording hygiene (node 10)

The first push-tier runs surfaced a systemic leak class: the plan tool recorded gate
output verbatim, so absolute repo/home paths landed in `plan/` notes and records —
exactly what the secret scan refuses. Resolution, owner-directed: (1) root cause —
`plan.py` redacts home/repo prefixes in the RECORDED form only (`<repo>/…`, `~/…`;
display stays verbatim; new signatures computed over the redacted content; stored
signed notes are historical records and are not rewritten); (2) the 9 historical
record-file lines were redacted in place (the receipt JSONs they point to are
untouched); (3) four signature-bound main-plan files — `plan/v2-completion.md`,
`plan/v3-h1-consolidation.md`, `plan/v3-h2-reranking.md`, `plan/v3-eval-pipeline.md`
— keep their signed text verbatim and are exempted from the scanner's IDENTIFIER
class only (credentials stay fatal there; everything else in `plan/` is scanned in
full). The directive named three files; `v2-completion.md:170` is the same
signature-bound class and is the fourth — documented here per the node-10 record. If
those four files are ever committed, the history scan needs the same scoping — noted
here, deliberately not pre-solved.

## Amendment 2 — 2026-11-11: tiers filled, markers self-applied, hosted-CI adapter path (nodes 11–15)

Scope evolution, all additive: the perf tier now has a real command
(`scripts/perf_probe.py`, thresholds locked from calibration); the e2e tier adds
`scripts/e2e_journey.py` alongside `demo.sh`; the root `pytest.ini` self-applies
the tier marker scheme (node 13 — the non-goals above said "no root pytest.ini";
the plan's node 13 made it a deliverable, proven collection-neutral against a
pre-ini capture); `pipeline.py --fast` runs a declared 34-file unit subset
(node 14); and the runner itself stages `HARNESS_STAGING_PYTHON` with check.sh's
probe, so a bare pipeline run tests exactly what check.sh tests (node 15).
The inventory gained one surface along the way: `tier-markers` (the root
`pytest.ini`), moved from absent to present in `survey.py` at node 13.

`check.sh` is now an ADAPTER over the pipeline: it stages the wheel-capable
Python, runs `python3 scripts/pipeline.py` (push → unit → integration → e2e —
demo.sh included — → perf, fail-fast, one hash-bound receipt), verifies the
receipt with `--allow-not-run ship` (ship stays human, so INCOMPLETE-at-ship is
the adapter's definition of success), then runs the FULL-HISTORY secret scan the
push tier deliberately scopes to the tree. Ordering and fail-fast semantics match
the old script; nothing pre-existing was dropped.

Hosted-CI adapter path (documentation only — no hosted wiring created): a future
workflow job calls `python3 scripts/pipeline.py` on the runner image and archives
`.harness-work/eval-pipeline-20261110/runs/run-*.json` as a build artifact;
`pipeline.py verify <receipt>` re-checks it anywhere. ci.yml/lint.yml keep
working unchanged until that adapter is written. The receipt is the contract
between local and hosted runs: same tiers, same order, same verdict rules.

Live findings surfaced by these nodes (owned by other workstreams; recorded here
for the backlog):
1. `tests/test_mcp.py::ProfileAndConflictTests::test_default_paths_include_profile_folder_and_resolve_relative_kb_paths`
   is cwd-contaminated by design (TmpCase never chdirs): from the repo root the
   KB indexes the real `docs/` tree, and docs growth has pushed `build_index()`'s
   8 KB budget past the point where detail lines survive — the test fails from
   the repo root and passes from `/tmp` (A/B-verified 2026-11-11). Failing from
   the repo root means `check.sh` and the hosted suite run red until its owning
   workstream isolates the test.
2. The seven `tests/test_v1_staging.py` reds under a bare `pytest` run were the
   missing `HARNESS_STAGING_PYTHON` staging contract, not a code regression;
   the runner now stages it and they pass (verified 2026-11-11 with
   `/opt/homebrew/bin/python3.11`).

## Amendment 3 — 2026-11-11: test-tamper guard in the push tier (node 17)

`scripts/tamper_guard.py` integrates the qualified v0 prototype
(`.harness-work/tamper-guard-20261110/`, 9/9 fixture criteria; design:
`docs/v3/tamper-guard-design-20261110.md`) into the push tier as its FIRST
command — a trip stops the tier before ruff/scan spend a second.

The hard problem was the dirty tree: the repo carries legitimate uncommitted
owner work, so a naive diff-vs-HEAD flags the owner's own pending changes.
Resolution — a fail-closed acknowledgment loop instead of a commit anchor:

- The baseline (`.harness-work/tamper-baseline.json`) is the LAST-GREEN test
  surface, refreshed only on PASS (clean or attested), never on TRIP/NOT_RUN/
  ERROR — a weakened tree can never become the new baseline.
- Bootstrap anchors on the HEAD tree's bytes (`git show`), deliberately NOT
  the prototype's bless-the-current-tree D7: the first run flags exactly the
  uncommitted diffs instead of absorbing them silently.
- ANY diff vs baseline is a finding (new/changed/deleted file under tests/ or
  eval/), keeping the prototype's mechanical sub-signals on changed files
  (function drop, new skip/xfail, assertion-density drop > 20%).
- A finding is excused only by an attestation entry
  (`.harness-work/tamper-attestations.json`, schema
  `harness.tamper-attestations/v1`) matching path AND current sha256 (baseline
  sha256 for deletions) with a non-empty dated reason. Unrecorded diffs fail
  the tier; a tampered or stale-hash entry simply does not match, so the
  finding stands; a structurally invalid attestation file is an ERROR
  (fail-closed). Stale entries are reported, not fatal.

Policy decision — the prototype's per-file function-drop flag is ON. v0 tripped
on NET function count only, so a drop in one file masked by growth in another
escaped; here every finding is the reviewer's surface, so the per-file drop is
first-class (test: `test_per_file_function_drop_not_masked_by_growth`).

Receipt binding: the pipeline gained a generic `evidence_file` channel — a
command may declare a JSON document it rewrites every run; the runner deletes
it pre-run (stale content can never pose as this run's evidence), embeds its
parsed content into the command record, and fails the command fail-closed if a
passing run leaves no parseable evidence. The volatile verdict file is NOT
artifact-pinned (pinning a per-run file would invalidate every older receipt);
the guard SCRIPT stays artifact-pinned like every invoked file. The receipt
thus carries the applied attestations (hashes + reasons) verbatim, inside the
self-hashed body.

Known blind spots, unchanged from the v0 design and accepted: value-changed
assertions and fixture edits keep the same mechanical shape and evade static
detection — covered by the repo's mutation controls on critical suites, not by
this guard. Detection of tautologized assertions stays density-heuristic.

## Amendment 4 — 2026-11-11: deterministic tool resolution + named tool errors (node 19)

Motivation, same day: the runner built every command from `sys.executable`, so
when the managed venv lost ruff mid-session (runtime recreated underneath the
session), the push tier died with a bare `exit 1 in 0.0s` and no named reason;
green only returned by re-invoking the whole pipeline via `/usr/bin/python3`.
The runner now treats the tool interpreter as a resolved dependency instead of
an accident of launch.

**Resolution order** (module-invoked tools only): (a) `HARNESS_PIPELINE_PYTHON`
env override, (b) `/usr/bin/python3` when present, (c) `sys.executable` fallback.
The resolved interpreter AND the resolution source are recorded in the receipt
per tool command (`tool.interpreter`, `tool.resolution`). Audit of the registry:
the only module-invoked tools are ruff (push) and pytest (unit, integration).
Repo scripts (`tamper_guard.py`, `e2e_journey.py`, `perf_probe.py`,
`check_settlement.py`) deliberately stay on the runner's own interpreter — they
are repo-versioned code, artifact-pinned into the receipt, needing only stdlib +
the repo; bash commands carry no interpreter.

**Named-error policy**: immediately before a tool command executes, the runner
probes `import <module>` in the resolved interpreter. A missing tool fails the
command WITHOUT executing it (`not_executed: true`, exit 1) and names both the
tool and the interpreter in the receipt (`tool ruff unavailable in
/usr/bin/python3: No module named 'ruff'` — the interpreter's own reason carried
verbatim); a probe crash is fail-closed (treated as unavailable). Fail-fast and
the guard-first ordering are unchanged: probes happen per command at execution
time, so the tamper guard still runs before any tool probe can stop the tier.

**Version-drift policy**: the tool's `--version` output is recorded per command
(`tool.version`, `tool.version_raw`). ruff's hosted pin (lint.yml: **0.16.10**;
the local interpreter carries 0.16.3) is recorded as `tool.pinned`; a mismatch
adds a `version_drift` NOTE and the run stays green — **only a MISSING tool
fails, never a drift** (the local tier is a pre-push smoke; the hosted workflow
remains the pinned authority). An indeterminate version probe is likewise noted,
never fatal.

Receipt binding: the `tool` block is additive inside the self-hashed body —
older receipts still verify, and `verify` needs no schema bump (the block is
optional content, covered by the receipt's own sha256 like every other field).
Self-hash care for this amendment: `scripts/pipeline.py` is off the tamper
guard's surface (tests/ + eval/ only), so no attestation covers it; the guard
attestation for `tests/test_pipeline_runner.py` was amended old-sha -> new-sha
(h6c-style, old sha retained in the reason). Fast-tier receipts that
artifact-pinned the old bytes of `test_pipeline_runner.py` no longer verify —
artifact binding working as designed (same acceptance as node 16's pre-flight
find). Nodes 9 (master) and 16 (capstone) re-gated green after the change.
