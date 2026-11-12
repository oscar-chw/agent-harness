# References for concrete design choices

Use a principle to explain a consequence and its limits. Saying “first
principles,” “systems thinking” or “simplicity” earns no design credit by
itself. A useful recommendation names the constraint that makes it preferable
and an observation that would reverse it.

## Evidence inspected and the gaps it fills

Three primary additions were inspected on 2 November 2026. Existing production
cases remain in the [engineering sidecar](../engineering-cases-20261102.md).
The summaries below are documented source positions; subsequent decision
references and worked cases are authored inferences, not source quotations.

### F1. Which layer can establish the requested guarantee?

**Gap:** retry and boundary cases need an explicit reason why a lower-level
success can leave an application outcome unknown.

**Documented:** Saltzer, Reed and Clark distinguish application correctness
from lower-level assistance. Their file-transfer example checks the stored
destination; reliable transport alone does not cover every failure. Lower-level
checks may still improve performance. Their live-voice versus recorded-message
example changes the preferred tradeoff when delay and recoverability change.
The argument is conditional on identifying the relevant endpoints. Read the
paper's introduction, file-transfer/performance sections, delivery guarantees,
duplicate suppression and “Identifying the ends,” PDF pages 1–7; later history
and bibliography were not used. [End-to-End Arguments in System Design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf).

### F2. What complexity is necessary to support the outcome?

**Gap:** module counts and line counts do not capture the continuing cost of a
choice, or explain why a service boundary might sometimes simplify operation.

**Documented:** Google's SRE chapter distinguishes essential and accidental
complexity, advocates purposeful code and small APIs, and connects modularity
and versioning with independent changes. It favors smaller release batches
because their effects are easier to understand. It does not supply a universal
service count or prove that the shortest implementation is safest. Read all
chapter prose, including stability/agility, minimal APIs, modularity and release
simplicity; linked works were not followed. [Simplicity](https://sre.google/sre-book/simplicity/).

### F3. What does the person believe happened, and how can they recover?

**Gap:** authoritative write handling needs a human-facing counterpart; a
correct backend can still leave someone confused or unable to finish.

**Documented:** Nielsen's heuristics call for timely status, familiar language,
user control, prevention of costly mistakes and actionable error recovery.
They are broad interaction rules, not an application-specific validation or a
prescription to confirm every click. Read the definitions and tips for all ten
heuristics, focusing on 1, 3, 5, 8, 9 and 10; linked articles were not followed.
[10 Usability Heuristics for User Interface Design](https://www.nngroup.com/articles/ten-usability-heuristics/).

## Put a guarantee where its meaning and authority meet

**Inferred design reference.** Identify the actual outcome before choosing the
check. “The request arrived,” “the row committed,” and “the person has a usable
reservation” are different outcomes. A receipt at one boundary establishes
only the property observed there. User feedback should express that distinction.

A browser can prevent an accidental second click; it cannot decide between two
competing clients. A storage transaction can enforce a local invariant; it
cannot alone establish that an external email arrived or a separate payment
completed. When several authorities participate, explicitly model the partial
outcomes and recovery instead of claiming one local transaction covers them.

Keep useful early checks when they reduce waste or improve recovery. The rule
does not imply deleting validation, transport protection or defense in depth.
Move a function only after identifying which failures its new owner can observe
and control. See C2 and C5 in the [worked cases](worked-cases.md).

## Compare the cost of the whole change, including recovery

**Inferred design reference.** A single deployment often avoids network and
operational coordination for a small team. An independent component may become
worthwhile when it removes a demonstrated release, ownership or failure
coupling. Count data migrations, compatibility windows, on-call responsibility,
debugging and rollback alongside implementation effort. Existing investment is
relevant to migration cost; past effort alone does not justify future work.

Prefer an intermediate state that is useful even if the next stage is delayed.
A domain map may clarify ownership before isolation is feasible; an isolated
carve-out may prove a boundary while leaving most code unchanged. The sidecar's
Shopify cases document both unfinished states. Neither a diagram nor a passing
dependency rule establishes executable isolation. See C1.

## Separate uncertainty about state from uncertainty about value

**Inferred design reference.** An ambiguous write calls for authoritative status
or reconciliation. An unknown workload calls for a bounded measurement. A
missing preference about relocation cannot be resolved by another benchmark.
Match the information sought to the decision it could actually change.

Compare plausible scenarios without inventing probabilities or numeric scores.
If the same choice survives every plausible scenario, more research may not
change it. If one unknown flips the choice and a cheap authorised probe can
resolve it, acquire that evidence before an irreversible commitment. Time spent
waiting is also a consequence: an offer or a recovery window can expire.

This is an authored decision aid, not a measured psychological or financial
model. C6 and C7 deliberately use supplied assumptions rather than current
weather, job-market, legal or investment claims.

## Correctness, capacity and authority are separate constraints

**Inferred design reference.** A repeatable operation can still overload its
dependencies; available capacity does not make a duplicate side effect safe.
Treat replay safety, load budget and total deadline separately. Existing
Amazon/Stripe and Google overload cases support examining these together;
they do not authorize copying an old retry count or current endpoint behavior.
See C3 and the sidecar's evidence limits.

Likewise, broader retrieval may improve recall while crossing a source boundary.
An old note's relevance does not grant current authority. Make scope and
freshness part of the question before selecting a retrieval method. See C4.

## A recommendation needs a way to be wrong

**Inferred design reference.** State the smallest observation that would expose
a bad choice: concurrent attempts, a lost response, failure after a commit,
inability to start a claimed component, or an absent source within allowed
scope. Select a check of the claimed outcome rather than one that only
recognizes the chosen implementation's words.

After an observation, revise only the affected conclusion. A failed frontend
does not erase a still-current backend result, but the whole product cannot be
declared delivered without its integration evidence. This pack proposes checks;
it does not implement them or replace the orchestrator's acceptance gates.
