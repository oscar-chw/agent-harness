# Reuse researched capability knowledge

A capability is a meaningful task family, such as research-paper writing or a
database migration. Its individual tool calls inherit that research context.

Before using a new task family, inspect its saved research and user preferences.
Use `harness research check <capability>` where a shell is available, or the shared
KB's `RESEARCH.md` index and scoped memory tools. Known research should be reused.
A missing record leaves local coverage unassessed. Inspect broader capability
records, existing skills, knowledge sections and the shared vault first. For
example, peer review may already be covered by research-paper guidance. Reuse
applicable sources and register missing provenance. Research remaining gaps in
practical skill, methodology, reasoning and representative examples. Record sources,
read depth, assumptions, applicability, counterexamples and evaluation limits.
Distill guidance into the central knowledge/skill system and register its source
hashes. Ordinary execution can then retrieve the relevant section directly.

Save newly learned documents under `${HARNESS_HOME:-$HOME/.agent-harness}/vault`.
Records for these files use `"source_root": "vault"` and paths relative to that
directory. The vault and research history survive package updates. Shipped base
knowledge remains under `content/knowledge`; avoid writing learned material into
that replaceable package tree. Scope retrieval and retain source provenance.

## Updates and saved preferences

Reuse a completed current record until the user asks for an update. A changed or
unavailable source is visible as a review requirement. Inspect that discrepancy
before deciding whether research needs renewal. Time passing alone triggers no
new campaign. A missing current fact in the user's task can still require a
targeted lookup within the existing capability.

Save explicit user preferences with their source and scope. During an upgrade
with saved preferences, show them concisely and ask the user to confirm what
should carry forward. Preserve them while waiting. After actual confirmation,
bind the update to the current preference digest and previous research record.
A stale digest requires a fresh read. The digest detects changes; the client
remains responsible for evidence of the human's answer.
Updates retain the prior research record in local history. Bounded storage stops
further writes at its limit and asks for preservation; it never silently prunes
research or saved preferences.

## Withdrawal and requalification

Withdraw rejected capability research with `harness research withdraw <capability>
--expected <record_sha256> --reason <reason> --source <review-reference>`.
The structured lifecycle takes precedence over matching source hashes and update
intent. A fresh `research check` returns `WITHDRAWN`. Source files, prior records
and saved preferences remain available for review. Withdrawal also works when a
pinned source has disappeared. Freeform quality notes have no lifecycle effect.

After deliberate source review, use `harness research record <capability> --input
<record.json> --expected <withdrawn-record_sha256> --requalify --reason <reason>
--source <review-reference>`. Every supplied source must match its current hash.
Confirm current saved preferences using `--confirmed-preferences <digest>` after
the actual human answer. Ordinary updates cannot clear withdrawal. Stale writers
must reread. Withdrawal and requalification preserve their provenance and the
preceding record digest in bounded history. A requalified research record is
eligible for advisory reuse. Model adherence and efficacy require separate
measurements, and procedure adoption retains its own evaluation gate.

## What registration establishes

A current source-bound record means the saved research can be found and checked.
Its examples and source links support inspection. Performance, successful model
use and scientific truth require their own evidence. Store learned procedures as
candidates until their existing evaluation gate permits adoption. Keep the shared
task board focused on status, results and next action, with links to this durable
knowledge. Use cross-session messages only when work needs active intervention.
