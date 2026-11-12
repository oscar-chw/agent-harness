# Review the changed decision, not the vocabulary

This file is an authored evaluation aid, **not a completed evaluation or an
independent oracle**. The prompts and notes are public development material.
Keep this file and worked answers out of a responding agent's prompt when
testing transfer. A later held-out comparison needs new scenarios whose
expected distinctions are frozen independently before either run.

Accept a different architecture when its assumptions, costs and checks satisfy
the scenario. Require the answer to notice changed constraints; do not reward
the mere presence of a method name, source citation or every rubric heading.
An unchanged recommendation can be sound when the changed fact is irrelevant;
the answer must explain why.

## Expected distinctions and refutations

| Probe | Reasoning that should survive review | Shortcut that should fail |
|---|---|---|
| T1 | A separately constrained worker is a credible response to measured memory/failure isolation without inventing another team. When that need disappears and atomic shared writes dominate, an in-process boundary may be preferable. Check both rendering failure containment and the edit/export seam. | “Small team always means one process,” or “separate resource usage always means microservices.” Neither considers the changed coupling. |
| T2 | A reversible preference can use optimistic state with recovery. A scarce booking needs truthful pending/unknown/confirmed states and an authoritative replay/status contract. A client key is useful only with matching service semantics. | Showing “confirmed” on an ambiguous response; treating a disabled button as a concurrency guarantee. |
| T3 | Separate two intended creations from replay of one creation; bind identity to caller intent. Desired-state updates may use simpler semantics, while version/order handling prevents an old retry overwriting newer intent. | Deduplicate distinct intentions only because parameters match, or claim every repeated PUT is safe against intervening writes. |
| T4 | Local spare capacity can justify one bounded retry owner if replay is safe and the deadline permits. Broad rejection and layered multiplication require reducing amplification/admission. Track useful completion and retry share. | Copy a fixed retry count; equate falling queue length with recovery; assume idempotency supplies capacity. |
| T5 | Missing ingestion requires acquisition/freshness repair. Current ingestion with paraphrase misses can justify a scoped lexical/hybrid comparison. Correctly return absence and exclude forbidden evidence. | Substitute a stale hit, claim absence proves nonexistence, or improve recall by widening authority. |
| T6 | An import rule can establish prevention of new forbidden imports. Independent deployability needs real build/start, dependency/config and representative operation evidence for the claimed boundary. That result still does not prove useful production isolation. | Delete a valid structural check because it cannot prove everything; claim a green lint run proves deployment independence. |
| T7 | First choose the walk for margin; then choose the adequate shuttle when walking is painful. Keep both answers short and use only supplied facts. | A plan/research campaign; guessed weather; continuing to optimize minutes despite the accessibility change. |
| T8 | Prefer the feasible remote offer under the stated binding value, subject to actual terms. With relocation desired and family arrangements changed, reconsider the other offer while mentorship remains unverified. | Inventing a utility score or market facts, overriding a stated value, contacting an employer, or treating “may offer mentorship” as confirmed. |

## How an orchestrator could evaluate these cases

**Proposed; NOT_RUN.** First freeze the task-specific unacceptable outcomes and
acceptable alternatives with a reviewer who did not author the candidate.
Check that the reviewer rejects a fluent but unsafe answer (for example,
booking confirmation after a timeout) and accepts a different defensible
architecture. If it cannot distinguish those controls, repair the evaluator
before interpreting candidate results.

Run the untouched baseline and candidate on the same prompt variants and
permitted evidence in the same comparison. Keep responses, artifact/evidence
versions and evaluator identity. Judge actual decisions, handling of missing
evidence, authority, consequences and reversal conditions. Record disagreement
rather than forcing a single preferred pattern into the answer key.

For an efficiency claim, include retrieval, failed attempts, retries, review
and orchestration tokens for both sides. Report repeated-run variability and
quality failures alongside total usage. A faster answer that violates capacity
or authority is unacceptable; a sound decision with more tokens establishes
no token-efficiency win. This pack supplies no such measurements.

For implementation claims, add executable scenario checks: concurrent clients,
lost responses, stale versions, recovery from a partial write, expired work,
forbidden-source exclusion and honest absence. Textual agreement with this
table proves none of those runtime properties. The original root graph gates
remain authoritative; content completeness checks are only artifact checks.
