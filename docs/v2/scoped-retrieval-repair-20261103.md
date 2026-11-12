# Scoped retrieval repair — 3 November 2026

A real retrieval bug is fixed and locally installed. This is a development
increment, not a completed v2 release or an all-device rollout.

## The defect and repair

An approved note contained `quartzterm`. Adding an **excluded** catalogue entry
with that ID made the same query return nothing: excluded metadata changed how
the query was interpreted. No excluded body had to be read to cause the failure.

Exact-ID matching now checks only approved documents. The allowed note stays
searchable; selected opaque IDs still work. Excluded bodies, stale source checks,
public-rights requirements and configured roots remain unchanged.

| Evidence | Result |
|---|---|
| Failing reproduction, lexical and FTS5, padded/unpadded query | 4 failed before repair; all 6 controls passed afterward |
| Expanded source/process selection suite | 74 passed, no errors, failures or skips |
| Deliberately broken variants | All 3 caught: old exact-ID routing, reading before ID filtering, omitted sensitivity filtering |
| Candidate with installed dependencies | 6 passed |
| Actual installed CLI, same frozen fixture | Bug reproduced before; allowed answer returned after; opaque-ID, no-match and non-public refusal controls retained |
| Independent source review | No material issue found; static review only |

The 74 checks cover project roots, approved IDs, sensitivity, task scope and
memory layers, including fresh CLI consumers. A separately measured stronger
foreign match cannot change allowed results or scores. Retained lead IDs
19/20/104 and their synthetic locator do not expand the reader's roots. Excluded
stale sources cannot poison allowed recall; selected stale sources still refuse.
This is an explicit caller-scope contract, **not authentication or proof every
native model follows it**.

## Invalid fixtures corrected openly

Two canaries accidentally overlapped permitted text: `FOREIGN_ONLY` matched an
allowed `foreign` locator; `excluded-exact-sentinel` matched the allowed word
`exact`. Those permitted hits were not evidence of disclosure. I changed only
the supposed absent-query identities, kept every exclusion assertion, and added
six overlap controls proving legitimate allowed hits remain available. Original
failed tests, frozen inputs and fixtures remain inspectable. One preparation
command also failed before the correction ran; its subsequent unchanged failed
run is retained. No product change was made to satisfy these faulty expectations.

## Current qualification boundary

The original cross-project exclusion case now has bounded local process evidence.
Four original cases remain partial: source-coverage meaning, current-search
meaning, learning prerequisites and paraphrase recovery strategy. Complete
matched usage and per-case nonregression remain unproven. The original gate exits
**1 / NOT_QUALIFIED**, retaining the same sixteen-case requirements.

The code repair changed a source used in an earlier native answer batch. The old
source bytes and answers were preserved as historical evidence; their hash was
not replaced with the new code's hash. The resulting stale live-path failure is
retained. The result ledger now locates those exact historical bytes explicitly.
That earlier batch is not claimed rerun or current-candidate native qualification.
No new native evaluation call, remote service or promotion was introduced here;
worker/root usage is not asserted to be zero or complete.

## Files and recovery

- Main evidence: [scope-round/root-review.json](../../.harness-work/retrieval/scope-round/root-review.json).
- Before/after installed CLI: `scope-round/installed-cli-{before,after}.json`.
- Exact backup, installed/config hashes: `scope-round/activation.json`.
- Frozen inputs, failed and passing XML, retained disposable fixtures and mutation
  logs: `.harness-work/retrieval/scope-round/`. Do not reuse its `--basetemp` paths.
- Four specialist inputs: Framework's selection contract and source review,
  Methodology's memory-selection tests, Vault's shared-selection tests, and
  Philosophy's answer-completeness candidate. Root ran the checks. The proposed
  completeness mechanism is not enabled or claimed effective without evaluation.

Only `vault_retrieval.py` was updated in the installed library. Native permission
settings and guards were unchanged; already-loaded imports and other devices
are not claimed refreshed. Original history, failed attempts and the strict
quality/token acceptance rule are retained.
