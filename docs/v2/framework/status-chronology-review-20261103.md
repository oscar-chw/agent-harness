# Status chronology: bounded source review

3 November 2026. **No actionable concrete regression found in the named diff.**
Static review only; tests, gate commands, native/model calls and activation are
NOT_RUN by this reviewer. Root owns independent verification and installation.

## Exact inspected scope

Compared the two `attempts`/`cmd_status` changes between the retained before-file
and current workgraph engine. Read all of the named chronology test file. Read
adjacent timestamp parsing, attempt-line matching, stats, repeated-failure and
routing consumers only to assess the additive field and retained ordering. No
broad history, native memory answers, root reasoning or installed state reviewed.

| Source | SHA-256 |
|---|---|
| `.harness-work/retrieval/answer-pass/workgraph-plan.before-status.py` | `93bf9a219579e113a1268727a6e02644670927490ec9134fa7b28051600040b5` |
| `src/agent_harness/workgraph/plan.py` | `cabf9d83db8e076158a3934a75d73697de8e09e6f71082c95f3965388da8465a` |
| `tests/test_plan_status_chronology.py` | `332aa7dd18f997a175a21285b623c23447d25cd7b1570a4c0b9c0c83997beb36` |

Source reads/hashing completed; hashes identify reviewed bytes, not passing tests.

## Reconciliation

- `attempts`, engine lines514–527, adds the leading timestamp from a note already
  admitted by the existing anchored attempt-line matcher. Existing code, secs,
  signature and tail fields remain; the change does not sort or discard attempts.
  Adjacent repeated-failure/routing consumers still receive their original
  sequence, while the dashboard can rank timestamps separately.
- `cmd_status`, lines1990–2005, counts all recognized attempts and nonzero exit
  codes before chronology selection. It replaces the last-loop-item choice
  with the maximum valid parsed failure time. Thus a newer failure on an earlier
  node or earlier note cannot be displaced merely by file iteration order.
- The existing `parse_iso`, lines117–121, returns UTC-aware datetimes for the
  tool's timestamp form and None for invalid dates. Failure timestamps that
  reach this parser but cannot be ranked still count as failures. They produce
  an unranked warning, and a sole selected dated failure is labelled last dated
  rather than silently claiming all failures have an established order.
- Lines2004–2018 preserve equal latest timestamps as ties rather than choosing
  an arbitrary winner. Node IDs are sorted/deduplicated for the tie summary.
  This is a coarse event-time display: it does not infer subsecond chronology.
- Successes contribute to run/duration counts but do not erase the historical
  last failure. No gate execution, node completion mark, lease, scope, permission
  or native activation authority is added by this diff.

The six test-source assertions address node-order and note-order inversions,
failure retained after success, equal-time ties, invalid-date qualification with
failure counts, and a success-only history. These are relevant regression checks
by inspection; this reviewer has not executed them or their mutants and reports
no PASS on their behalf.

No concrete counterexample requiring a change was identified in this bounded
scope. This conclusion does not certify the whole engine, all malformed-input
formats, real machine clocks, installed clients, native answers, release readiness
or efficacy. Root must run its affected checks against the current exact subject
before qualification, retaining original failures and valid negative controls.
