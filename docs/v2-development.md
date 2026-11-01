# V2 development candidate — 2.0.0.dev0

## Quick read

This is a testable development build, not a live upgrade.

- Choose permission control once at installation; updates retain the choice.
- Reuse one task workspace instead of scattering temporary files.
- Keep documents readable: answer first, linked detail, and visuals chosen for the task.
- Existing memory and workflow features remain; lossless recall and all-device rollout are unproven.

The mechanisms and evidence below are reference detail. Start with the relevant
section; a simple question does not require reading this whole note.

2 November 2026. This branch integrates the existing memory/discovery development
line with bounded project artifact navigation and a tested literal-output guard
correction. The version is a development milestone, not a stable v2 qualification,
an all-device deployment or a demonstrated improvement over native clients.

## Aim and mechanism

Provide a coherent local foundation across coding clients: one navigable project
state, scoped source-backed memory, proportionate execution, checks that can fail
and inspectable candidate learning. Keep sophisticated internals where needed;
make their responsibilities and evidence visible. An uncomplicated front door
must not conceal an unmanaged collection of agents, files and background jobs.

Use the existing method decision, graph and task context. A ready small outcome
can go directly to execution and its check; dependencies justify a graph,
consequential uncertainty justifies research/clarification, and observed failures
justify returning to the relevant stage. None requires spawning another agent.
An advisory route does not grant native permissions or establish completion.

## Artifact organization

First reuse the project's established task location. When none fits a material
task, prepare one workspace from the project directory:

```sh
harness workspace --task example --init
harness workspace --task example
```

```text
.harness-work/
  .gitignore      protects newly created untracked workspaces from ordinary add
  example/
    README.md     current output/evidence pointers and next action
    outputs/      deliverables worth keeping
    scratch/      reusable intermediate logs and experiments
```

There is one index, not a new dated summary on every turn. Repeated initialization
preserves it. Task/handoff templates point to the existing artifact location;
the graph and original checks retain completion authority. A simple reply needs
no workspace or document. This CLI adds no MCP definition to every prompt.

Inspection reads metadata only. It does not ingest file contents, contact another
session, scan unrelated tasks, prune files or change a completion mark. Missing
workspaces report NOT_CREATED; incomplete layouts report INCOMPLETE. A successful
inventory reports NOT_EVALUATED for completion.

Inspection refuses symlinks/special files, invalid task IDs, depth over 16 and
over 1,000 entries. It lists at most 40 files within an 8 KiB compact metadata
budget, with full bounded totals and explicit omitted counts. Scratch above
32 MiB triggers a warning, not deletion or a disk quota. Keep final artifacts at
the agreed delivery path; links do not replace verifying their contents.
Initialization creates the managed root's ignore file if absent, without editing
the project's own rules. An existing custom file is preserved and reported as
unverified. Ignore rules do not untrack files already committed or prevent a
deliberate force-add. For a newly prepared root, explicitly copy selected publishable
deliverables to the repository's established output location. Do not force-add
private scratch or histories. The tool does not eliminate arbitrary files that a
native model chooses to create elsewhere, and is not a filesystem sandbox.

## Recent references: compare before adopting

The [Instagram mind map](https://www.instagram.com/p/DfII2pXyjoS/) was read through
its public caption and visible diagram. It inventories reasoning, frameworks,
memory, tools, orchestration, stack, observability/evaluation and security.
That is useful coverage, not a measured architecture. Existing mechanisms cover
parts of those categories; the map omits source correction/withdrawal, typed
failure/recovery, scope-bound approval consumption, ownership, artifact lifecycle
and independent promotion evidence. Do not install every named product.

| Reference checked | Useful mechanism | Decision for this dev candidate |
|---|---|---|
| [Microsoft LLMLingua](https://github.com/microsoft/LLMLingua) | Learned prompt compression; older 2023/2024 research | Reference only. No lossy compressor or extra model dependency installed; this is not a verified newly released "Token Saver" product. |
| [Microsoft Agent Framework compaction](https://learn.microsoft.com/en-us/agent-framework/concepts/agents/conversations/compaction) | Atomic tool-call/result groups and selectable compaction policies; marked experimental | Borrow bounded output/reference design. Its in-memory history compaction does not take over service-managed native conversation history. |
| [Microsoft Agent Lightning v1.0](https://www.microsoft.com/en-us/research/blog/agent-lightning-v1-0-a-3500-line-lightweight-agentic-rl-framework-for-training-agents-with-real-harnesses/) | Training through real harnesses; October 7 article | Research reference. RL training and endpoint redirection are not subscription quota savings or a drop-in local learning loop. |
| [DeepSeek Harness rc.5](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.2.1-rc.5) and [alpha.2](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.2.2-alpha.2) | Capability declarations, lifecycle ownership, experimental delegation/worktrees | Keep the current graph and adapters. Alpha features are not rc features; no wholesale runtime replacement or inherited permission-bypass defaults. |
| [DeepSeek superagent prototype](https://github.com/deepseek-ai/dsh-superagent-prototype/tree/6337fc823ce20251c8de8085948165c81aaa701e) | Explicit work items and authorization separated from incoming context | Design reference. Pinned README says research-only, not an official product, with article designs still unimplemented. No unattended executor enabled. |

Primary-source review, not local execution, supports the table. Microsoft and
DeepSeek research were independent bounded investigations; the main loop checked
the relevant primary material. No account, API purchase, endpoint replacement,
new model, service, dependency or scheduler was enabled.

Compression needs matched tasks, source visibility and aggregate token/quality
measurement. Rewriting reusable prefixes may hurt provider cache reuse; that is
a design risk to measure, not an observed regression here. Existing bounded
source retrieval and metadata-only workspace output reduce unnecessary injected
text mechanically, but do not establish end-to-end token savings.

## Readable output and appropriate visuals

The owner's requested output policy is delivered through the on-demand
[`clear-docs` skill](../content/skills/clear-docs/SKILL.md): plain language,
an immediately useful overview and detail behind links. It routes exact lookup
to tables, relationships to diagrams, real numerical patterns to charts and
specific interface locations to screenshots. Motion needs a reason; simple
answers and straight steps can stay as text. The rule adds no hook or model judge.

Its [source notes](../content/skills/clear-docs/references.md) distinguish official
guidance and specific learning studies from an unmeasured application to AI output.
[Positive and negative cases](../content/skills/clear-docs/cases.md) make the intended
decisions inspectable. Structural validation and prompt-budget checks do not prove
that readers understand faster or that aggregate token usage improved.

The separately requested [Unslop UI skill](https://github.com/heydamir/unslop/tree/a6f121eee5f29c2f74976b75456feae8b66afb3a)
is an optional external extension, not a new mandatory backend/research pipeline.
It is not bundled here or claimed installed on other devices. Its attribution
license, optional browser/video tooling and separately authorized image services
remain distinct from this standard-library harness.

## Capability and qualification boundaries

### Installation policy choice

An interactive first installation asks once for explicit review, native workspace
autonomy, or preserving current settings. Later updates reuse the recorded choice.
Unattended `--yes` by itself preserves settings; it never selects more autonomy.
Use `--permission-profile explicit`, `autonomous` or `preserve` to choose deliberately.

Claude's autonomous candidate selects native `auto` and replaces only this
installer's blocking command/edit/Stop hooks with passive capture/recall. Other
owners' hooks and deny rules are preserved. Project-only auto installs are refused
before writing because the documented setting needs user scope. Explicit review
selects native `default` and retains the harness checks.
See [Claude permission modes](https://code.claude.com/docs/en/permission-modes).

Codex's autonomous candidate selects workspace-write, on-request and native
automatic approval review; explicit review selects read-only and human review.
The obsolete untrusted policy is not generated. Native or organization restrictions
still win; unsupported client versions may reject or limit these settings.
See [Codex sandbox defaults](https://learn.chatgpt.com/docs/sandboxing#configure-defaults).
Other client adapters do not acquire a universal policy API from this choice;
their native approval controls remain unchanged.

This is not unrestricted host access, a password provider, a new per-command LLM
hook, or proof that every sudo/remote-admin operation will run. Root/home-wide
deletion, protected secrets and external authority restrictions must not be
described as harmless routine work. A fully unrestricted mode cannot honestly
promise a narrow safety net where the client lacks that mechanism. Exact native
behavior still needs an authorized client trial; generated configuration tests do
not remove that qualification requirement. No live policy was changed here.

### Historical failure review and controller responsibility

The supplied conversation contains repeated concrete failures: printed examples
blocked as execution, permanently blocking hooks phrased as approval requests,
repeated consent without a consumer, stale version/install identity, and guards
duplicating native checks. A prior bounded inspection covered four relevant
threads/twelve returned turns. This is not an exhaustive read of every private
chat; indexed search also reported evictions, so absence is not a history census.

The central controller should own intent, shared state, source authority, a scoped
policy choice and concise receipts. Native clients execute their own permissions;
the controller must distinguish task consent, native trust and organization rules.
Never ask twice for the same valid grant or promise that chat consent can override
an interface with no approval consumer. Keep a refusal receipt and diagnose the
specific layer, with tests for benign text, real side effects, stale grants,
changed targets and cancellation. Do not add a second arbitrary classifier to
every command or silently remove another owner's protection.

Current local readback found installed agent-harness declared 0.9.1.dev0, source
declared 2.0.0.dev0 on this dev branch, and a different PATH plan launcher. No v1.2
tag/source was established in the inspected repository, install or bounded task
search. A named v1.2 milestone elsewhere is unresolved, not disproved. Reconcile
those identities before any live migration; do not overwrite a different active
controller based on this branch name.

| Area | Development functionality | What this does not establish |
|---|---|---|
| Coding workflow | Work graph, leases, node gates, method advice, bounded native launch | Every native session follows it automatically |
| Shared memory | Scoped facts, source receipts, corrections, handoff inspection and cold-read tests | Lossless recall or all-history knowledge-graph coverage |
| Research | Scoped lexical retrieval, source vault, bounded official-source discovery | Every retained link read, hybrid/graph superiority, autonomous fact verification |
| Learning | Proposal/source lifecycle with held activation | Unattended self-training or approved native promotion boundary |
| Clients | Existing Claude Code, Codex, Copilot and other adapters | Equal feature support or a tested rollout on every OS/device |
| Guard | Existing corpus plus narrowly tested Python literal-output repair | Complete safety, live installation of the patch or qualified remote approval/resume |
| Organization | Workspace CLI and optional task/handoff template pointers | A hard disk cap, automatic cleanup or prevention of all model-created clutter |
| Operations | Existing reversible scheduler and runtime-inspection mechanisms | Healthy storage on a user's live installation or exactly-once external effects |

## Trying it safely

Use the exact development commit, a clean checkout and a disposable home before
changing an active client. Python 3.9+ and the standard library run the harness;
pytest/ruff/setuptools/wheel are test/build dependencies. Do not substitute a
paid API when included native account access is unavailable.

```sh
python3 bin/harness --help
python3 bin/harness --home /path/to/disposable-home install --yes --tools codex
```

The disposable directory must be newly allocated for the trial. This tests
configuration generation, not real native login, model quality or every feature.
Inspect the generated files and use `status --matrix` for support differences.
There is no stable `v2.0.0` tag, no automatic update-channel switch and no live
configuration migration in this publication. Keep the current install/backup
until the specific client and required workflow pass their own trial.

## Verification and remaining work

New workspace acceptance cases were written before implementation: missing
command failed first; added metadata-budget and incomplete-layout cases also
failed before repair. Tests cover repeated setup, owner edits, contents excluded,
task isolation, paths, symlinks, special files, inventory/depth limits and warnings
without deletion. The integrated release gate must run on the exact clean
publication snapshot. CI, publication and live deployment are separate evidence.

Before calling v2 stable: qualify native approval/resume through its supported
maintenance interface; resolve operational storage limits without purging user
evidence; complete matched retrieval/routing/learning evaluations; verify intended
clients/devices; then admit the stable release. Preserve failed candidates and
explicit NOT_RUN/HOLD outcomes. A larger version number does not clear those holds.
