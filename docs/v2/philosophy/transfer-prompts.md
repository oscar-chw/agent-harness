# Transfer prompts: answer the situation

These are authored development probes, not executed or held-out evaluations.
Answer each scenario directly: choose, explain the material tradeoff, say what
you would need to verify and identify what changes your choice. No framework
names or fixed reasoning format are required. Do not assume authority to act
on production, contact people or broaden data access.

## T1. The boundary moves

A three-person team owns a school timetable tool with one transactional store.
The export renderer alone exhausts memory and can fail without preventing
timetable edits. Isolate it in-process, in a separately constrained worker, or
as an independently owned service? Why?

Change: rendering is now tiny, but the proposed worker needs atomic edits to
the same timetable rows. Does your choice change? Name the integration outcome
you would check, rather than only the dependency rule.

## T2. The outcome matters more than the animation

A user changes a dashboard's colour and the write fails. Should the UI apply it
immediately, wait for confirmation, or show another state?

Change: the same UI now confirms a unique room booking, and the connection drops
after the server may have committed. Explain what the user should see, how the
intent is identified and what the service must establish before replay.

## T3. An identical payload can mean a different intent

An operator asks for two identical test environments. The first request times
out; the operator deliberately starts the second. A service hashes parameters
to deduplicate both. What is wrong with the contract, and what would you use
instead?

Change: the operation is “set this named environment's description to X.” Does
it need the same machinery? What if an older retry arrives after a newer edit?

## T4. A quick recovery becomes extra load

Image processing jobs call a backend that rejects 2% of requests on one hot
instance; other instances have measured spare capacity. Decide where and when
to retry, and what budget/deadline information matters.

Change: nearly all instances reject, and three different layers each retry.
Which recommendation changes? Which invariant and measurements still matter?

## T5. More search can produce a worse answer

An exact decision lookup returns an old decision. A new scoped document
reverses it, but the index has not ingested that document. Do you add semantic
ranking, fix acquisition, or broaden search?

Change: ingestion is current, exact titles work, and relevant documents use
different language from held-out questions. Propose a comparison. Include a
no-evidence case and a very relevant result outside authorised scope.

## T6. The green check observes the wrong property

A package has zero dependency violations, yet it cannot start without the full
application. Its owner says it is independently deployable. Is that claim
established? State the smallest additional evidence and what it would prove.

Change: the team's only stated aim was preventing new forbidden imports. Is
the existing check now useful? Must every such package become a service?

## T7. Daily effort should stay small

You have a casual 14:00 meeting. It is 13:40; the walk takes 10 minutes, while a
verified shuttle leaves at 13:50 and takes 6 minutes. Accessibility and weather
are unconstrained. Give the useful answer in at most two sentences.

Change: walking is painful and the shuttle timing is sufficient. Answer again.
These are supplied scenario facts; do not browse a real schedule.

## T8. Facts cannot choose a person's priority

A candidate says staying near family is non-negotiable. A remote offer meets
their minimum role needs; a second offer requires relocation and may offer
better mentorship, which is unverified. Give a conditional recommendation and
name the information that could actually change it. Send no messages.

Change: the candidate actively wants to relocate and has arranged the family
commitment. How does your comparison change? What remains uncertain? Do not
invent salaries, promotion odds, legal terms or personal circumstances.
