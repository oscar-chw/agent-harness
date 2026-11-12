# Worked decisions and the facts that would change them

Every scenario below is **hypothetical**; each recommendation is **inferred**.
“Evidence to seek” is a proposed check, not a completed result. Production-case
claims belong to the [existing sidecar](../engineering-cases-20261102.md);
foundation sources/read depth are in [decision references](decision-references.md).

## C1. A two-person team adds approvals to an internal application

**Outcome and invariant.** Add an approval flow that can be changed safely;
only an authorised reviewer may approve, and an approval must refer to the
record version reviewed. The supplied scenario has one team, one database,
modest traffic and no independent availability requirement.

**Choices and consequences.** Add an in-process approval module with a narrow
interface; create a separately deployed service; or continue adding handlers
that directly edit each other's tables. The first keeps the transaction local
while making responsibility clearer. A service adds a new failure and data
consistency boundary. Unrestricted shared writes make a later change harder to
contain. Recommend the module, including version checks at its write boundary,
without claiming it can already run independently.

**Failure and evidence to seek.** A record changes after review, then an old
approval arrives. Exercise that stale-version case, an unauthorised caller and
a real consumer of the module. A dependency lint pass alone is insufficient.
The sidecar's Shopify/Packwerk cases motivate separating organisational grouping
from executable isolation; F2 motivates counting operational costs.

**Reversal.** If a separate team needs independent releases and the workload
can own its data and failure policy, investigate a service. If it still needs
atomic updates to shared rows, independent deployment alone has not resolved
the key coupling. Re-measure migration and consistency costs before extraction.

## C2. A person books the last available workshop place

**Outcome and invariant.** A reservation is confirmed only after the authority
accepts it; capacity never becomes negative. Assume one transactional store,
two concurrent clients and no external payment in this version.

**Choices and consequences.** Show immediate “confirmed”; wait silently; or
show “reserving,” then confirmed/refused/unknown with a recovery path. Recommend
the third: timely feedback and preserved input, with atomic capacity handling
and a request identifier tied to the reservation intent. Disabling the button
can improve interaction but cannot protect the shared capacity invariant.

**Failure and evidence to seek.** Submit two clients against one place; exactly
one may win. Drop the winner's response after commit: look up the same operation
instead of silently booking again. Define same-key/different-intent behavior
and persistence together; a client-generated key alone is insufficient. F1/F3
and the sidecar's idempotency cases inform this inferred design.

**Reversal.** For a reversible display preference with no shared scarcity,
optimistic feedback plus clear recovery can be reasonable. If payments enter
the flow, this one-store design no longer covers the full invariant: payment,
reservation and partial failure require their own explicit recovery contract.

## C3. A report queue grows during a dependency incident

**Outcome and invariant.** Finish accepted reports within their useful lifetime
without duplicate publication or unbounded extra load. Assume workers can
retry, but dependency capacity and failure locality are initially unknown.

**Choices and consequences.** Increase attempts at every layer; stop all work;
or bound work at one retry owner, preserve accepted jobs durably and inspect
which dependency is rejecting. Recommend the third while maintaining the
incident's existing authority limits. Separate computation from publication:
repeated computation may be tolerable while repeated external publication is
not. Backoff controls timing; it does not establish replay safety or capacity.

**Failure and evidence to seek.** Count first attempts and retries across
layers, completion age, rejection cost and useful completions. Falling queue
depth after dropping accepted work is not evidence of successful completion.
Define what expires, what may be degraded and how users learn the outcome.
This applies the sidecar's Google overload and Amazon/Stripe cases.

**Reversal.** If rejection is local, healthy capacity is verified and replay is
safe, a bounded retry routed elsewhere may help. If rejection is widespread or
retry amplification rises, reduce retries and admission. Do not import a fleet
setting without the signals and contract that made it appropriate there.

## C4. A project assistant cannot find a cited decision

**Outcome and invariant.** Return evidence from the authorised project with
provenance, or say that evidence is missing. Assume lexical search finds exact
titles but fails some paraphrases; another project's similarly named decision
is visible in an index but is outside the selected scope.

**Choices and consequences.** Search every visible source; add embeddings;
or first diagnose within-scope acquisition, freshness and query matching.
Recommend the third. An absent source cannot be recovered by changing ranking.
If acquisition is sound and paraphrases are the actual gap, compare lexical
and hybrid routes on the same scoped cases before choosing.

**Failure and evidence to seek.** Include an exact title, a paraphrase, an
outdated decision, no matching evidence, and a tempting forbidden-source match.
Verify source spans and correction behavior as well as answer relevance.
Do not interpret a missed hit as proof the decision never existed. This is an
application of the local second-brain contract, not a measured retrieval result.

**Reversal.** Held-out paraphrase failures can justify another retrieval route;
they cannot justify broader access. An explicit source-scope authorisation can
change the allowed corpus, after which relevance still needs evaluation.

## C5. A database migration has failed partway through

**Outcome and invariant.** Recover a consistent service without silently losing
accepted writes. Assume an old backup exists; its restore was never exercised,
the migration's atomicity is unknown, and post-backup writes may matter.

**Choices and consequences.** Restore immediately; rerun the migration; or
first determine committed state and qualify recovery on an isolated copy.
Recommend preserving evidence and assessing the least destructive recovery
within existing incident authority. Do not rerun until repeatability is known;
do not equate a backup file's existence with a usable recovery path. A proposed
write freeze or production restore needs its own operational authority.

**Failure and evidence to seek.** On an authorised isolated copy, establish
schema/data consistency, exercise an actual read/write path and reconcile
accepted writes against the proposed recovery point. Record unresolved loss
and recovery time rather than reporting success after process startup alone.
F1 informs checking the final outcome; F2 informs choosing a narrow change.
No restore, migration or interruption was executed for this example.

**Reversal.** If current evidence shows a fully rolled-back transaction, a
corrected retry may be preferable. If a qualified restore meets an explicitly
accepted data-loss window and forward repair cannot meet the recovery need,
restore may be preferable under incident authority. The acceptable loss window
is a stakeholder constraint; a script cannot decide it.

## C6. A small daily choice: walk or take the shuttle

**Outcome and invariant.** Arrive for a casual meeting before 09:00. Supplied
scenario facts: it is 08:40; walking takes 12 minutes; the shuttle leaves at
08:50 and takes 5 minutes; weather and accessibility pose no constraint.

**Choices and consequences.** Walk now and arrive around 08:52; wait and arrive
around 08:55 if the shuttle runs as stated. Recommend: “Walk now; it gives you
more margin.” That answer needs no research plan or multi-role analysis.

**Failure and evidence to seek.** Times are scenario assumptions, not a live
schedule. If they are unreliable and punctuality matters, check the relevant
current source. Do not invent a traffic probability to justify the choice.

**Reversal.** If walking causes pain, or heavy rain makes it impractical, take
the shuttle when its timing is adequate; a more consequential appointment may
justify a current timing check or a different authorised option. The choice
changes because the constraints change, not because another framework is named.

## C7. A consequential choice: accept a job requiring relocation?

**Outcome and invariant.** This hypothetical candidate wants technical growth
while keeping a stated weekly in-person caregiving commitment. Offer A requires
relocation that prevents that commitment. Offer B is local and meets the
candidate's stated minimum role requirements. A's mentorship is unverified;
B's work is less novel. There are no salary, legal or market facts supplied.

**Choices and consequences.** Accept A, accept B, or seek a bounded clarification
before the actual offer deadline. On these stated values, provisionally prefer
B. Ask A only about an arrangement that could change the conflict, if time and
ordinary contact authority permit. Do not assume flexibility will be granted,
or assign a numeric value to care versus career for the candidate.

**Failure and evidence to seek.** Distinguish written offer conditions, the
candidate's own priorities and predictions about growth. Confirm the deadline
and unresolved terms in a real decision. Compare a scenario with no flexibility
against one with a confirmed workable arrangement. No message is sent by this
case; no present user circumstance or employment advice is asserted.

**Reversal.** If caregiving coverage changes by the candidate's own choice, or
A confirms an acceptable arrangement and its learning advantage is supported,
reconsider A. If the candidate values relocation itself, that also changes the
choice. If values are unknown, return a conditional comparison and ask which
constraint is binding; additional generic research cannot supply that value.
