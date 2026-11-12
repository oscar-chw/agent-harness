# Original retrieval gate: thin integration contract

3 November 2026. Static design input only. No gate, runtime, acceptance input or
test changed; no verification/native call run by this worker. Root owns original
node4, implementation, execution, semantic adjudication and acceptance authority.

## Reuse and immutable subject

Implement the missing `.harness-work/v2-completion/check_retrieval.py` as a thin
reader of the original case contract plus a root-owned, evidence-bound result
sidecar. Reuse `agent_harness.qualification.Bindings` for reads and `finish()`;
do not build a second path/hash validator or repurpose the H05-specific
`qualification.validate` schema. A small node-specific reader is sufficient.
No new engine, service, database, model grader or native launch belongs in it.

Inspected original input: `docs/v2/vault/acceptance-cases.json`, SHA-256
`dfc21103e64ae00d4bc9e6404aaa1481c440b18e8f11d020686be2574dac7343`.
It contains eleven SOURCE_ANSWER cases and five other cases: correction replay,
two scope controls, paraphrase challenge and cold handoff. Preserve exact IDs,
questions, answer requirements, must-not conditions, setups and run contract.
Validate full coverage against that input, not a worker-created shorter list.
Missing/duplicate cases, omitted requirement indices or unknown substitute cases
must not quietly reduce the denominator. Keep the input's historical NOT_RUN
fields intact; current adjudication belongs in the bound sidecar.

`qualification.py` inspected SHA-256:
`5c5a776191a80b87199b8b2e665e8c5baa283727c8046a7d0dc329fd42bc6e7e`.
Bindings rejects unsafe/credential/symlink paths, nonregular or changing files,
hash mismatch and byte-limit excess; it checks cached bindings again at finish.
It does not execute checks, authenticate a receipt author or infer entailment.
Keep its limits. Large raw streams need root-defined bounded independently
hashed evidence segments/indexes, not loosened limits or silently omitted debt.
Any segmentation must retain linkage to the original complete attempt.

## Four proof layers that the gate must not conflate

| Layer | Evidence consumed | Insufficient substitute |
|---|---|---|
| Actual local tests | Root-executed commands, exits/logs, test/checker and subject revisions; relevant negative and positive controls | A declared exit0, source presence, test count or worker report alone |
| Semantic answers and real replay | Exact case/prompt/response/retrieved spans and root's pre-frozen criteria; per-requirement support and forbidden-consequence review; actual state/access/correction traces for replay kinds | Enum/keyword scoring, provided-excerpt answers standing in for discovery, or a description of a replay |
| Receipt consistency | Current subject, contract, source, prompt/context, response/artifact, invocation and grader bindings through the existing reader | Matching hashes proving provenance, truth, native behavior or completion by themselves |
| Matched whole usage | Predeclared comparable arms, scope/reader/budget conditions and complete attempt/overhead ledger, with explicit accounting semantics | Native subtotal, successful last attempt, smaller source bytes, cached-token savings or UNKNOWN treated as zero |

Local checks remain real checks run by root, with their commands/results linked
in the sidecar. Gate receipt validation is a separate operation. A test passing
for the instrument does not pass a source question or native consumer. Historical
test logs may support historical subjects; changed subjects need applicable new
evidence, not a silently updated subject hash.

For each SOURCE_ANSWER case, root must actually read the response and permitted
source spans against every original requirement and must-not. A citation must
support the adjacent claim. Correct uncertainty can satisfy a requirement for
unknown identity/content; missing required evidence cannot become a generic
"unknown" success. Keep report-versus-primary and historical-versus-current
qualifications. The current r5 correction is additive evidence: explain the
earlier defined denominator/read-depth snapshot and its correction, rather than
silently replacing original requirements or claiming fresh primary reads.

For the five other cases retain their actual input/setup obligations. Observe
old/new receipts and affected/unaffected work for correction; scoped before-
scoring behavior and foreign-cache exclusion for cross-project control; a real
warmed/revoked cache and effective revocation for revoked-access; an actual
derived-view omission with original-source recovery for paraphrase challenge;
and the fresh authorized worker's canonical-file/graph pickup for cold handoff.
Shared primitives are reusable evidence, not permission to substitute one kind
of case for another. A chmod control readable by the executor stays NOT_VERIFIED.

## Sidecar acceptance and process result

Keep the sidecar finite: original contract reference; frozen case/arm criteria
and source versions; one explicit result per original requirement and forbidden
condition; exact response/trace/reviewer/control pointers; missing/invalid reasons;
and the comparison/usage ledger. All referenced evidence and checker subjects
are byte-bound with the existing reader, with final `finish()` before reporting.
Require root adjudication for semantic meaning; caller-authored PASS fields must
not masquerade as independently observed results. This proposal adds no trusted
signature service: root's controlled execution and recorded review remain an
explicit trust assumption, not cryptographic authentication.

The original command exits zero only when all sixteen cases meet the frozen
applicable obligations, no per-case quality/scope/correction regression occurs,
and complete matched aggregate candidate tokens are no greater than baseline.
Safety/scope failures cannot be averaged away. An improvement claim additionally
needs evidence of benefit; mere equality is not measured improvement. Semantic
arms require separate authorization; do not introduce them just to fill a row.

Emit useful partial results but stay nonzero for absent script/evidence, invalid
binding, unresolved required outcome, unrun required axis or unavailable whole
usage. Preserve FAIL, NOT_RUN, UNKNOWN and INVALID distinctions in the report;
do not make an informational "contract valid" exit0 the node's completion gate.
No native/model call is automatically launched when the gate is rerun. Native
experiments require their own prior freeze/authority, budget and retained debt.

## What must remain nonzero now

The current root packet and original graph still report the missing script and
node4 pending. The four-question section/window pilot was supplied-evidence
development calibration; some original answer qualifications were omitted and
the window arm used more native tokens. Eleven SOURCE_ANSWER questions are not
all qualified by that result. The newly assigned all-eleven pass is not executed
evidence at this writing.

Root's completed-chain `receipts/scope-r2-root-review.json` reports
PASS_BOUNDED_NATIVE_COMPLETED_HANDOFF for observed original cold-pickup behaviors.
That real increment should remain credited at its bound scope. It does not
establish all sixteen cases, the remaining actual control replays, same-visibility
comparative recovery or complete aggregate usage. Prior scope failure, timed-out
producers and UNKNOWN usage debt remain. Do not require every historical failed
attempt to become PASS; preserve it and include its applicable cost rather than
letting it permanently forbid a legitimately new qualification.

A future zero needs root-observed complete answers, actual remaining replay/
scope/recovery traces, current bindings, exercised instrument controls and a
prospectively frozen matched comparison with complete accounting. Producer,
maintenance, retrieval, workers, orchestration, grading, retries and failed arms
cannot disappear from the relevant total. If historical total usage cannot be
recovered, report it UNKNOWN; only a separately scoped complete prospective
comparison can support its own claim, never retroactively repair the old total.
Root must reconcile that scope with the original node requirement before closing
it. No widened acceptance, promotion, installed rollout or stable-v2 claim follows.

Root-owned integration controls should include missing-case/required-field
deletion; stale response/source/checker binding; fluent unsupported answer versus
supported alternative; replay described but never executed; foreign/revoked text;
omitted failed-call cost; missing usage and candidate total above baseline.
Reject each for its intended defect while retaining sound controls. These are
proposed controls, NOT_RUN by this worker.
