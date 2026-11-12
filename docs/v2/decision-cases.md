# Use a case to resolve a real uncertainty

These are visible development examples, not a mandatory routine or learned
production policy. Read one relevant section, compare its assumptions with the
task, and retain its limits. Direct questions need no case read. The exact facts,
alternatives and proposed checks are in the [case contract](philosophy/decision-contract-20261103.json).

## Module and isolation

DC-01 starts with two developers, one deployment and no required renderer fault
isolation. An in-process module or cohesive existing functions can fit. A changed
requirement adds a reproduced memory-exhaustion fault, required isolation and
budget for one boundary; a separately constrained worker or owned renderer
service becomes credible. Renaming the application changes neither constraint.

Keep authorization/version checks at the owning write. A passing import rule
does not establish that a component starts, serves its representative operation
or contains a process fault. Shopify's retrospective describes this gap; it does
not make service extraction universally preferable. [Primary source](https://shopify.engineering/a-packwerk-retrospective).

## Replay and unknown outcomes

DC-02 loses the response to a create request. The control explicitly supplies
atomic intent/effect recording, stable replay semantics and a retention window.
Reusing the same intent or querying its authoritative status can be sound. Remove
that contract and status path: retain unknown; do not automatically create again
or show confirmed. Changing only the identifier's spelling is irrelevant.

This case assumes a contract; it does not prove a real endpoint implements it.
Two intended identical jobs differ from replay of one intent. [AWS explanation](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/).

## Overload and useful completion

DC-03 permits one retry owner, one extra attempt, a 500 ms deadline and a verified
healthy alternative. A 100 ms retry after 100 ms elapsed fits; the fresh cache is also
acceptable. System-wide rejection removes the capacity premise. Serve the valid
cache without another RPC. Changing an instance label does not change this.

Count failed attempts and deadlines, not just eventual success. Idempotency does
not create capacity. Fleet-specific retry numbers are not defaults for our tasks.
[Google's overload guidance](https://sre.google/sre-book/handling-overload/).

## SQL metric semantics

DC-04 requires one row per customer, including zero activity. Two separate
invoices of 100 each mean 200 invoice revenue. Joining line items and payments can
inflate that to 500; SUM(DISTINCT amount) wrongly returns 100. For received cash,
the supplied payments sum to 130 instead. Renaming customers must not change
either metric. Keep the unit and required population before choosing a query.

The local SQL oracle executes the actual submitted query across frozen fixtures,
including equal values, fanout, missing children and changed metrics. A successful
run proves only those fixture outcomes. [SQLite join semantics](https://www.sqlite.org/lang_select.html).

## Evidence and correction

DC-05 asks for project P's current retention. Its original source says 30 days; a
current correction says 7. Preserve the original history, invalidate or refresh
the derivative and cite the current permitted revision. A highly ranked project Q
hit grants no access and changes no answer. If current bytes are missing, the
current value stays unknown; 30 is only historical.

The case's supplied record fields are hypothetical facts. They are not real
captured source bytes or proof that a live retrieval/correction workflow ran.

## Proportionate everyday choice

DC-06 starts at 08:40, with a 12-minute walk or an 08:50 shuttle taking 5 minutes.
The stated goal prefers greater margin: walk arrives 08:52 versus 08:55. If walking
is painful and forbidden, take the feasible shuttle. A changed meeting title is
irrelevant. Give the short useful answer; no research, agents or invented weather.

## What has been checked

The six families contain 19 visible variants. Local checks rederive supplied
constraints and calibrate actual SQL consequences. Other proposed application
tests, native reasoning/transfer and comparative quality/aggregate tokens remain
NOT_RUN here. A case enum or readable explanation is not an execution receipt.
See [evaluation contract](methodology/decision-eval-contract-20261103.md).
