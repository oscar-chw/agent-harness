# Read the evidence without turning it into permission

3 November 2026. Local development repair, **not stable-v2 qualification**.

A short memory note can lose an important condition. `memory-read --sources`
now returns that note's actual saved source spans and citations for inspection.
It follows retained provenance; it does not guess missing links, widen saved
lines or search other projects. Default reads emit the same packet as before.

The original fixture requires both passing checks and ticket-owner approval.
Its derived note mentions only checks. The new read exposes the omitted approval
condition, but keeps the note **pending and unusable for current decisions**.
Reading a rule does not prove approval occurred. Historical evidence does not
revive withdrawn advice. `--sources --recover` is refused; normal pending recovery
still returns HOLD. This is authorized-path evidence review, not authentication,
secret scanning, automatic semantic verification or a native permission grant.

## Verification

| Check | Root-owned result |
|---|---|
| New API/CLI checks before implementation | 45 failed: missing API option/CLI flag |
| Same focused checks after implementation | 45 passed; first run reported two unregistered-mark warnings |
| Affected memory, launch, integrity, privilege and recovery checks under the existing strict tier config | 208 passed, zero errors/failures/skips |
| Isolated deliberate defects | All four rejected: duplicate reads, omitted scope, omitted whole-response budget, false pending label |
| Candidate modules with installed package dependencies | 31 passed |
| Actual fresh installed CLI | Two before-calls reproduce missing option; seven after-calls pass source/default/scope/HOLD/stale/history checks |
| Ruff on changed production/tests and explicitly named helper scripts | Passed |

The main command was `PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider
-c src/agent_harness/workgraph/tiers/pytest.ini` with the thirteen explicit test
files recorded in `source-review/validation.json`. XML records actual selection
and zero errors/skips; passing counts overlap and must not be added together.
Framework supplied a separate bounded static review, not independent execution.
Root owns all results and the decision to install.

Mutation-runner mistakes are retained: its first result check expected a summary
suppressed by quiet pytest; later replacement preflight found a repeated code
fragment. The final runner scopes the replacement to `read_scoped`, preflights
all mutations before execution and checks JUnit failures/errors. Product tests,
acceptance and assertions were unchanged. Preliminary logs/directories remain.

## Local installation and rollback

Only `project_memory.py` and `cli.py` were replaced after exact predecessor,
candidate and staged-test checks. Source and installed copies now match the
reviewed candidate hashes. Before-files and the activation record are in
`.harness-work/retrieval/source-review/`; each module's previous installed bytes
are named in `activation.json`. No native config, guard, hook or permission
changed; no sudo, native model call, release or forced open-client reload ran.
Shell-less/MCP-only consumers do not automatically gain this new CLI option.

## Contextual safety remains separate

The installed instruction policy reports `sudo_policy=adaptive`, with no writes
on readback. The active recovery guide matches the source guide. The current
privilege/recovery subset passed 33 tests, also included in the larger check.
Judge effect, target, blast radius, reversibility, sensitivity, current state and
existing approval. Contextual lessons retain evidence and counterexamples; they
cannot create grants or global allowlists. No trained classifier or measured
safety-learning improvement is claimed. Owner-disabled hooks stay disabled.

## What is still open

Original node4 still exits1, NOT_QUALIFIED: four partial retrieval cases and the
complete matched quality/token comparison remain. This explicit source-read
foundation is not a new native strategy result. Old native observations keep
their exact old source bytes: 68 project-memory binding locations were moved
to the already-captured before-file without changing hashes, original questions
or verdicts. The initial stale-binding exit2 and old ledger are retained.

Exact commands, pins, test XML, probes, activation and historical reconciliation:
`.harness-work/retrieval/source-review/validation.json`. Overall graph remains
15/20 recorded nodes done; that count is not a capability percentage.
