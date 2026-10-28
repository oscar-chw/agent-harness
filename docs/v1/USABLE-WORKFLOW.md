# V1 integrated workflow candidate

One core, the native client you already use, and the existing project graph.
This is a development guide, not a released version or an automatic-learning
claim. Memory, source histories, corrections and existing skills are retained.

## Start with the outcome

From the project, inspect `plan resume`. Continue the matching graph. For new
reversible work already authorized by the user:

```sh
plan new example "Describe the actual outcome" --autonomous
plan context example 1
```

Fill the analysis/research/plan sections, with a check that can fail and real
implementation nodes. The built-in phase checks check planning substance;
they do not prove that the implementation or research conclusion is correct.
Use `plan gate example ID` after doing each node, and `plan status example` for
progress. `--autonomous` removes a redundant planning sign-off only; it does not
grant permissions, allocate new model usage or release irreversible actions.

The existing plan prompt now points at this graph instead of putting a second
plan into the short state summary. No new task database or scheduler is added.

## How work loops

| Observation | Next action |
| --- | --- |
| Acceptance or intended user is unclear | Clarify the contract before implementation |
| Evidence missing, stale or contradicted | Revisit research; retain the source and status |
| Repeated implementation friction exposes a wrong interface | Revisit the design, then its dependent checks |
| Reproduction or regression fails | Debug the cause and rerun affected checks |
| Environment or quota prevents a check | Record blocked/unrun; do not grade the task from that failure |
| Independent checks pass | Record their evidence and complete the graph node |
| Verified experience suggests a reusable method | Prepare a source-bound candidate; do not silently change active skills |

Parallel workers need disjoint write ownership, bounded resources and a final
integration check. Reuse installed tools/skills only when they fit the task.
Model tier and domain role are different decisions. Requested routing is not
evidence of the effective model, and a worker report is not a completion gate.

## On-demand templates

The installed `content/templates/` directory contains:

| File | Purpose |
| --- | --- |
| `task.md` | Goal, authority, source versions, acceptance and recovery |
| `worker.md` | Minimal delegated context, output ownership and stop conditions |
| `handoff.md` | Current evidence, next step and remaining budget after restart |
| `source.json` | Source aliases, read depth, mechanisms, effects, limitations and requirement links |
| `procedure.json` | A method specification with explicit task/evidence files |
| `learning-review.md` | Baseline, independent evaluation, context cost and rollback contract |

These are optional artifact shapes, not six new mandatory context files. Fill
only what the task needs. A source template is not a completed canonical registry:
unread entries stay pending; deferred and rejected research remains retained.

## Turn experience into a reviewable method

1. Keep actual task inputs and observed check results inside the project. Do not
   fabricate experiences, copy one observation twice or import unrelated history.
2. Copy `procedure.json` to a private task file and replace the sample text.
   Each episode supplies `task_id`, `path` and `task_path`, relative to the git
   project root. Files must exist, remain in the project and fit 64 KiB each.
3. Prepare hashes without modifying the sources or the procedure store:

```sh
umask 077
harness improve --project "$PWD" --prepare-procedure method.json > bound-method.json
```

Check the exit code before using the output. Preparation emits JSON on success;
a refusal is not a candidate. Different hashes establish different bytes, not
independent experience or semantic correctness. No source content is included
automatically; the explicitly written steps are part of the candidate.

4. Save the draft through the existing lifecycle:

```sh
harness improve --project "$PWD" --draft-procedure bound-method.json
harness improve --project "$PWD" --inspect-procedure PROPOSAL_ID
```

The draft is **proposed**, never auto-injected as an active skill. If an episode
changed after preparation, draft validation refuses the stale binding. The
inspector shows status, original candidate and correction links.

5. Correct a named method with new source-bound steps:

```sh
harness improve --project "$PWD" --correct-procedure OLD_ID --draft-procedure replacement.json
```

This atomically withdraws the old advice and leaves the replacement proposed.
An identical retry returns the same replacement; a conflicting retry fails.
`--rollback ID` withdraws an active method while retaining its evidence. Do not
insert active rows manually to make a development candidate appear promoted.

Automatic promotion remains held until independent native actor/oracle isolation,
effective model and usage provenance, frozen grading, per-case non-regression and
aggregate tokens no greater than baseline are qualified. Capture, hashing and
drafting are useful preparation, not proof that a model learned or improved.

## Composition decision

Pstack's design-sketch and executable-review ideas complement the existing loop.
We retain this harness's project identity, graph, source receipts and promotion
boundary. We do not install a second startup controller, force multiple models
for every design, or infer an improvement from upstream popularity. See the
[pinned comparison](pstack-composition.md). This guide and its templates are our
implementation, not a copied upstream skill stack.

## What completion still requires

The source/CLI/template tests qualify only these interfaces. The existing
three-case Codex recall smoke receipt does not prove compaction recovery,
cross-client coherence, complete history migration, self-learning transfer or
lower total token usage. Fleet rollout must separately verify Studio, Air and
each server account, with shared binaries and private per-user memory and login.
V1 release and live migration remain held; no evidence or memory is deleted to
make a storage or release check pass.
