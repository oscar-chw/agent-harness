# v0.9 development candidate

Package version `0.9.1.dev0` identifies a **development branch**, not a tagged
release. This branch consolidates general-purpose source-backed local memory,
durable project task state, versioned work-graph checks, explicit bounded
Codex launch, and Claude Code/Codex/Copilot adapter work. The source remains
portable Python; it does not include the author's private plans, transcripts,
active client configuration, model receipts, or machine-specific memory.

## What the evidence supports

- Local unit and process-boundary tests can establish that project-scoped
  receipts, lease fencing, cold recovery, and installer rollback behave in
  disposable projects and homes.
- `examples/sandbox_demo.py` is a **CPU-only structural demonstration**. It
  makes no model call and reports token/cost fields as `UNKNOWN`. Its local
  checks do not establish model quality.
- A single synthetic coding task was tested privately through an explicit
  native Codex launch and an independently frozen grader. One task passing
  cannot establish general quality, hidden-grader isolation, or token/cost
  superiority. No raw native session or pilot receipt is published here.

## What remains unqualified

The personal-v1 acceptance gate, effective paired model identity, complete
selector/reviewer/failed-attempt overhead, all-tool grader isolation,
automatic wake-up of idle chats, and cross-device operational sync remain
`NOT_QUALIFIED` or unverified. A lease means claimed work, not proof that a
model is running. A work-graph node is done only when its own independent gate
passes.

The default global adapters would edit user instruction/config files, install
hooks, and add persistent approval for the harness MCP server. **Inspect an
exact redacted diff and backup/rollback plan before active installation.** A
package-only virtual environment or a disposable-home install is a narrower
way to try the CLI without modifying a live Claude, Codex, or VS Code setup.
Installation does not start unattended dispatch or install extensions; the
existing `harness run` command remains an explicit user-invoked capability.
