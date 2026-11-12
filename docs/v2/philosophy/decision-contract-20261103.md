# Decision contract — 3 November 2026

[Six bounded development families](decision-contract-20261103.json) translate
existing references/cases into supplied facts, invariants, permissible plans,
unacceptable consequences and proposed discriminating checks. This is an
authored-inference contract for root to review and freeze, not a passed gate,
responding-agent answer set, held-out benchmark or performance result.

| Family | Material distinction | Proposed bounded evidence |
|---|---|---|
| DC-01 Module/isolation | A small one-deployment app versus an export failure that must not stop edits | Stale/unauthorised approval state and an exercised failure boundary |
| DC-02 API replay/unknown | Explicit atomic intent/replay contract versus no completion/replay evidence | Same-intent replay, changed payload, distinct intent and unknown-state trace |
| DC-03 Overload | Local rejection with alternate capacity versus a pool unavailable through deadline | Attempts across layers, deadline and valid-cache consequences |
| DC-04 SQL metric | Invoice revenue versus received payments on identical rows | Full row set: invoice total 200 or payment total 130; zero-activity customer retained |
| DC-05 Evidence/correction | Current scoped source, superseding correction, or missing current bytes | Revision/span selection, stale derivative and bounded unknown |
| DC-06 Everyday choice | Walking feasible versus explicit accessibility exclusion | Arrival arithmetic and a direct useful answer |

Each family has a control, changed constraints and a nonmaterial change that
should not cause a recommendation/effort change. DC-05 also has missing-current-
evidence control: 19 variants in total. Neutral changes concern labels or an
unauthorised distractor, not a secretly changed decision constraint.

## Important distinctions for integration

The SQL data include two distinct invoices with equal amounts. A raw child-table
join can produce 500; SUM(DISTINCT invoice amount) produces 100 and is also wrong
for the required invoice total 200. This makes the expected result discriminate
between grain repair and value deduplication. The explicit payment-metric variant
instead expects 130. These are synthetic authored arithmetic expectations,
not executed SQL results or a production data claim.

Overload budget is a maximum, not an instruction to spend attempts. A valid cache
is a permissible alternative to a healthy-route retry. When all backends remain
unavailable through the deadline, that cache can stay acceptable while retrying
cannot achieve the goal. The contract therefore does not insist that every
material change must change an already-sound chosen alternative.

Replaying an opaque request ID depends on the supplied service contract;
same payload does not identify a genuinely separate user intent. With no such
contract or authoritative status, a timeout stays unknown. Correction likewise
does not grant broader source scope, and missing current evidence does not make
a stale value current or prove that no policy exists.

## Facts, keys and source evidence have different jobs

Effective facts are materialized for each variant by replacing top-level fields
from supplied_facts; nested overrides replace the entire object/array. Root can
serve just one variant's facts, goal/invariant and authorised source context.
Do not serve paired answer expectations or other variants' answers. These
public development cases still do not become held-out after filtering.

Permissible-decision identifiers name plans, not required actor vocabulary or
an exhaustive answer-string classifier. A different plan can be accepted only
when its consequences satisfy the same facts/constraints. Enum or numeric
matching alone cannot establish why a choice is sound, semantic adequacy,
useful native judgment or transfer. Root's independent methodology and actual
bounded outcomes must establish the appropriate claim.

Source pointers include inspected local note hashes/read scope and retained
primary URLs/read receipts. Notes are distinguished from original copied source.
No new upstream fetch or broader source campaign occurred. Vault independently
reconciles primary capture availability; this document does not certify it.

## Scope and status

Only this companion and its new JSON were written. Existing handoffs, history,
case files, source vault, runtime, tests, configuration and original gates remain
untouched. No model/native/API, install, deployment, messaging or worker run.
Root owns source correspondence, fixture/oracle checks, semantic review,
integration and the original node-2 gate. Every proposed scenario check is
NOT_RUN. Comparative efficacy and full aggregate usage remain node-6 work.
