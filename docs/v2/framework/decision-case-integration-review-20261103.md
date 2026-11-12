# Decision-case integration source review

3 November 2026. Bounded Framework review requested by root. **One P2
calibration finding; execution NOT_RUN by this reviewer.** Root retains all
verification, SQL execution-safety review, integration and claim authority. This
review changes only this new file and does not qualify the original node.

## Finding

### P2 — A nonempty subset can silently remove a decisive consequence

`docs/v2/check_decision_cases.py:133–139` derives an outcome dictionary but only
checks the keys supplied by the case's `expected_observable_distinctions`.
Requiring that dictionary to be nonempty prevents the earlier empty-object
defect; it does not require the consequence fields that make a particular
variant discriminating. The SQL fixture calibration at lines 140–147 does not
close that contract-completeness gap for the other families.

A concrete source-level countercontrol for root: in `DC-03.systemwide`, replace
the expected dictionary with `{"deadline_ms": 500}`. This key is returned by
`consequences`, its value matches, and the expected dictionary remains nonempty,
so the inspected validation path has no rejection for losing both the
`max_total_rpc_attempts` and `extra_attempts` requirements. That variant then
ceases to check the consequence that distinguishes system-wide overload. The
role, supplied/effective facts and nonempty alternatives remain intact.
Similarly, `DC-02.no_contract` can retain only
`{"duplicate_effect_guarantee": "not established"}`, losing its explicit
zero-create and unknown-visible-state requirements. These are static path
analyses, **not executed mutation results**.

`tests/test_decision_cases.py:33–46` currently checks an entirely empty
dictionary, not loss of an essential field while other valid fields remain.
The seven existing negative controls add/change a wrong value; they do not
exercise deletion of a distinguishing claim. Consequently a PASS can mean
"every retained expected field agrees" while a decisive part of the contract
has disappeared.

Smallest repair: independently retain the required outcome keys for each
frozen variant/contrast (or validate them against a separately pinned frozen
contract) and reject missing required keys before value comparison. Do not
require every key returned by `consequences`: the current variants deliberately
check different subsets, and some returned keys are not applicable claims.
Root should first preserve a failing deletion control, then demonstrate that
the unmodified contract and legitimate alternative SQL query remain accepted,
and rerun the original affected gate. This is a calibration coverage issue;
it does not establish that any current supplied expected value is wrong.

## Reconciliation and claim boundaries

- The inspected supplied cases are internally consistent at their stated finite
  scope: invoice amounts sum to 200, payments to 130, the raw line/payment join
  contributes 400 + 100 = 500, and amount DISTINCT gives 100. The second customer
  has zero activity. `INVOICE_QUERY`, `PAYMENT_QUERY` and the correlated invoice
  alternative express the specified grains; the two named bad queries express
  the intended fanout/amount-deduplication mistakes. These are source/arithmetic
  observations, not observed SQLite outputs from this reviewer.
- The overload control supplies 100 ms elapsed plus 100 ms for an alternate
  response under a 500 ms deadline. Its cache and bounded-retry alternatives are
  both permitted. The changed variant removes alternate capacity; the checker
  then derives no extra attempts. The everyday supplied arrivals are 08:52 and
  08:55; the accessibility variant removes walking from the feasible set.
- API replay guarantees in this checker are finite consequences of the supplied
  synthetic server contract, not traces of a server implementing that contract.
  Approval rejection, renderer containment and correction/history states are
  likewise asserted model requirements, not executed application properties.
  Their implementations and source entailment still need separate evidence.
- `decision-case-review-20261103.md` states those limits per family. The checker
  returns `native_decision_quality` and `comparative_quality_total_usage` as
  `NOT_RUN`, and its scope explicitly excludes actor reasoning and implementation
  proof. `decision-cases.md:73–79` preserves the same boundary. No accidental
  promotion to native reasoning, implementation proof, held-out transfer or
  efficacy was found in the inspected claims.
- The selective KB test reads only the SQL navigation section and checks an
  unavailable heading. That can establish section selection once root runs it;
  it does not establish semantic case fitness, instruction resistance, source
  currentness or learner use. The methodology contract correctly requires
  separate outcome, semantic/native and total-usage evidence.

This review did not inspect `sql_outcome` implementation or validate its SQL
read-only/execution-safety claims, root's reported historical test runs, primary
web passages, native behavior or total usage. It neither confirms nor disputes
those separate evidence layers.

## Exact inspected identities

Hashes were read with `shasum -a 256` (exit 0). They identify the source snapshot
reviewed; they are not test receipts. Full source text was inspected for the
first four files and the methodology Markdown. For philosophy JSON, inspected
scope was its opening classification/boundaries/actor-view/source pointers and
all six families' IDs, supplied facts, goals, invariants, variant roles/overrides,
permissible decisions and expected observable distinctions. Repeated materialized
effective-fact blocks and remaining author notes were not exhaustively read.

| Repo-relative file | SHA-256 |
|---|---|
| `docs/v2/check_decision_cases.py` | `5399a9878ba64a21a6840db52d97dae42da5dbd8b59aef149f513331a23952ba` |
| `tests/test_decision_cases.py` | `51ab9cb1f03b5f328584b32c3d5c49e2c1a11c685d58121bca26da2acb078df7` |
| `docs/v2/decision-case-review-20261103.md` | `8a5548cc5ba69168df2e3355ca4389ce45dade5dd60a2a6e4ea7727edae016ce` |
| `docs/v2/decision-cases.md` | `61956bd86b64ee7eb89a0cf6db91fd5a438de8a765656c80ab56126cfd79fce5` |
| `docs/v2/philosophy/decision-contract-20261103.json` | `9fd78c01f8e4d656595dd4f2733301ae1d1a5ff71ed1442d712173e34d1d712d` |
| `docs/v2/methodology/decision-eval-contract-20261103.md` | `d631924e710c55188811165f9e695632e2529fd14e79e216cb2ea58dd061f328` |

No tests, SQL queries, mutation controls or models were run for this assignment.
Only bounded local source reads, source-field projection and hashing preceded
this output. Root must execute/reconcile the proposed deletion controls before
reporting their results or resolving this finding.
