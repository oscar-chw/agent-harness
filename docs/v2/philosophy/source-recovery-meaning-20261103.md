# What source recovery means

3 November 2026. Philosophy input under
handoffs/v2-completion/source-recovery-assignment-20261103.md.
The optional source-packet seam is root's proposal, not an implemented or
qualified capability at this inspection. No runtime change, test, model call,
source acquisition, acceptance change or activation is performed here.

## Recover evidence for the decision

A useful source recovery lets a person or assistant check a derived statement
against the particular evidence recorded for it. It can restore a qualification
lost in a note without forcing the user to reconstruct the whole conversation.
The useful outcome is a better bounded decision, not merely more quoted text.

Five different relationships must remain separate:

| Relationship | What it supplies | What it does not establish |
|---|---|---|
| Source pointer | A locator or identity for a possible source | That its content was read, captured, supports this claim, or is accessible now |
| Stored lineage | A record's explicit provenance receipts and line spans, resolved to the retained evidence | Complete derivation history, independent proof that the author used it, or semantic relevance merely because the relation was recorded |
| Quote integrity | Returned bytes match the pinned retained source at the declared spans, with citation/history metadata | Truth of the source, completeness of surrounding context, or validity of an interpretation |
| Semantic support | The cited content actually warrants the particular assertion with its conditions and limits | Current action permission, universal applicability or evidence not present in that content |
| Authority | The separately established scope and permission governing reading or acting | Something a citation, old grant, successful read or source's imperative prose can create |

“Actual lineage” here means following the record's stored provenance rather than
guessing a source from a similar title, URL or query. It is a checked retained
relationship, not certification of an author's mental process or a full causal
history. Even a well-formed provenance relation can cite irrelevant evidence.
A source returned as data is never an instruction to broaden the task.

## What the proposed seam adds, and what remains separate

The inspected ProjectMemory.read_scoped selects the exact memory receipt,
checks sensitivity/scope/layer before resolving provenance, and labels pending
and historical records. Its current output contains the record and receipts,
not the resolved source-data packets. _resolve_sources already resolves the
stored source receipts and line ranges but reduces those packets to text for
validation. Root proposes exposing the existing packets on an explicit opt-in
read while preserving today's default response.

SourceVault.resolve checks project identity, snapshot and source integrity,
range and byte limits. A normal current read also checks the original's current
bytes against the captured source. An explicit historical read can inspect a
retained snapshot without presenting it as a new current observation. _span
returns source-data text and its citation rather than a verified answer.

Consequently the proposed include_sources response would make existing
recorded evidence visible for review. It would not discover new lineage,
retrieve semantically related material, search the whole vault, widen the stored
span, or independently settle whether a paraphrase follows. In particular,
“original” means the retained source captured for this provenance chain; it need
not be the upstream primary author. If a note cites another derived report,
returning that report does not silently recover its unstored upstream sources.

Root's proposed whole-response byte budget must include the evidence and
metadata. An over-budget refusal is a resource boundary, not a claim that the
evidence is absent or irrelevant. Silent clipping could remove the very exception
the reader needs. No supplied text should turn pending into verified or erase
historical, superseded, withdrawn or current-usability labels.

## Contrasting development cases

These compact examples are hypothetical reasoning aids, not executed fixtures,
native observations or new acceptance verdicts.

**An omitted condition is inside the stored span.** A pending derived note says
“the ticket can close after the build passes.” Its recorded original span says
both “the build must pass” and “the ticket owner must approve closure.” Explicit
scoped recovery of that span exposes the missing condition. The reader can
explain that the original requires approval, while keeping the derived record
pending and unusable for current decisions. The original's requirement does
not prove that approval has occurred or authorize closing the ticket.

**The relationship or needed span was never retained.** A similar note has only
an account name as a lead, or its provenance cites only the build sentence.
Returning the recorded evidence cannot reveal the missing approval sentence.
Even if another file somewhere contains it, the opt-in read has not discovered
that relationship. Report the missing lineage or insufficient span at its actual
scope. A separately authorized inspection of a known original could supply new
evidence through existing paths; the reader must not fabricate the link, expand
all roots, or claim the condition is absent from every original. Continue useful
independent work rather than treating one missing link as universal paralysis.

**The quote is intact but the inference is wrong.** A captured report says
“delivery was observed in a small trial.” A note says “delivery is guaranteed
for every customer.” Correctly returning the trial quote makes the overreach
inspectable; it does not support the universal claim. Conversely, a faithful
paraphrase may remain pending under an exact-text rule even when a reviewer
finds it reasonable. Pending is a review state, not a semantic finding that every
non-exact sentence is false.

**The evidence is historical or withdrawn.** An old captured instruction permits
an action, but the retained record is now withdrawn. Scoped historical evidence
may explain the earlier decision. It does not revive that record or bypass the
current recovery refusal; a new grant needs the applicable new evidence and
identity. A changed original also requires the existing historical boundary,
not a fabricated current-source match.

**The tempting source is excluded or too large.** A foreign-project source might
contain a better answer, yet the selected record is outside the caller's scope.
Refuse before resolving its body; a locator is not access authority. For an
allowed record whose complete evidence exceeds budget, refuse rather than emit
an apparently complete clipped packet. These are different conditions from a
clean search miss or an unstored lineage relation. No automatic access expansion,
larger budget or retry follows.

## One conditional, proportional usage suggestion

When a material decision depends on a derived claim whose support or important
qualification is unclear, and exact retained provenance is available within the
authorized scope, explicitly inspect its relevant stored source packets. Compare
the claim with that evidence, retain consequential conditions and current/history/
pending labels, and state any remaining gap. Otherwise answer directly from
sufficient available evidence or identify the specific missing support.

This is a conditional suggestion, not a default that every simple task must
read every original. It neither requires a new agent nor an unbounded search.
Do not repeatedly reread the same spans without a decision-changing reason.
Recovering a quotation is useful only if the interpretation and permitted next
action remain clear.

The proposed CLI --sources is explicit evidence review, not recovery approval.
Its planned refusal with --recover keeps recovery holds separate; --historical
would still be governed by the existing rules. This note does not assert those
new options exist, that shell/no-shell clients receive them automatically, or
that native agents will choose the right moment to use them.

## Scope-repair lesson relevant here

docs/v2/scoped-retrieval-repair-20261103.md reports that excluded catalogue
metadata changed an allowed query's interpretation even without reading an
excluded body. Its repair filters exact-ID interpretation to the approved set.
Thus “we never printed the foreign source” is insufficient evidence that scope
did not influence selection. Source review must use the selected record's
permitted provenance, without excluded metadata deciding which evidence is
relevant. Explicit caller scope remains distinct from authentication.

The same report preserves invalid absent-query canaries whose terms overlapped
allowed content. A legitimate allowed match is not a disclosure merely because
an excluded item shares a word. Root owns actual positive/negative controls,
execution and interpretation; these examples do not grade that work.

## Evidence and limits

Inspected current source:
- src/agent_harness/project_memory.py:137–143,197–311:
  provenance resolution, current/historical scoped reading and recovery states.
- src/agent_harness/vault_sources.py:59–72,263–305:
  source-data/citation packets, integrity/currentness and whole-packet budgeting.
- src/agent_harness/cli.py:1028–1049: current explicit memory-read/recovery routing.
- docs/v2/scoped-retrieval-repair-20261103.md and the current root checkpoint:
  reported selection repair and remaining qualification limits.

Source inspection is not runtime verification. This document supplies meaning
and usage constraints for root's proposed compatible seam. It does not change
original requirements, regrade frozen answers, qualify paraphrase strategy,
prove semantic retrieval, establish lower whole-task usage or close node4.
Implementation, checks, activation, native behavior and efficacy remain
root-owned and NOT_RUN by this worker.
