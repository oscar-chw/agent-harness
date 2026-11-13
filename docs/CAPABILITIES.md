# Shipped capability catalogue

Generated from package source. Run `python3 scripts/build_capability_catalog.py --check` to detect drift.
The JSON companion provides the same inventory for tooling.

For mechanisms and worked examples, read the [four walkthroughs](walkthrough/README.md).

## What belongs where

| Layer | Purpose | Activation boundary |
|---|---|---|
| Rules and skills | Guide task framing, implementation, debugging and review | Client loads installed guidance; model compliance needs behavioral checks |
| MCP tools | Read/write scoped memory, documents and task checkpoints | Registered MCP connection; disabled flags and shell capability apply |
| Work graph | Dependency scheduling, claims, gate execution and recovery | Plan CLI or exposed plan tool; a passing gate has its declared scope |
| Guard and native controls | Screen commands and retain permission boundaries | Guard hooks exist for supported clients; native approvals and OS rights remain separate |
| Templates and presets | Start a task, source record, handoff or bounded workflow | Selected for the task; templates supply structure |
| Learning lifecycle | Draft, evaluate, correct or withdraw a reusable method | Adoption requires independently checked outcomes and complete measured cost |
| Knowledge sources | Supply domain evidence and examples | Profile-selected accessible documents, retained revisions and scoped retrieval |

## Skills

| Skill | Purpose |
|---|---|
| [clear-docs](../content/skills/clear-docs/SKILL.md) | Readable docs, wikis and slides. |
| [data-job-trial-run](../content/skills/data-job-trial-run/SKILL.md) | Run long or costly data jobs, training or migrations small first, then a sample, then in full. Use before jobs touching many files or rows, or running for minutes. |
| [debug-systematically](../content/skills/debug-systematically/SKILL.md) | Find a bug's root cause before changing code. Use when something fails, throws or misbehaves and the cause is not obvious. |
| [production-code](../content/skills/production-code/SKILL.md) | Production bar for code you write or change - errors, logging without secrets, tests that catch breakage, lint, and the checks before saying done. |
| [session-memory](../content/skills/session-memory/SKILL.md) | Inspect shared task handoffs and maintain evidence-backed memory during multi-step work. |
| [standards](../content/skills/standards/SKILL.md) | Quality bar for tests, evals, gates and review - test tiers, real gates, tests that cannot fail. Load before writing a test or eval, or reviewing a diff. |
| [verify-before-done](../content/skills/verify-before-done/SKILL.md) | Show real evidence before saying done, fixed or working. Use before any completion claim, hand-back, commit or pull request. |
| [work-loop](../content/skills/work-loop/SKILL.md) | Default loop for research, coding and dev-ops - analyse, research, plan, execute, test, loop back where the evidence points. Use for any task beyond a one-line change. |
| [write-tests-first](../content/skills/write-tests-first/SKILL.md) | Write a failing test first, make it pass, then prove the tests catch breakage. Use when adding behaviour, fixing a bug, or changing untested logic. |

## MCP tools

Default exposure assumes an enabled MCP connection. `HARNESS_DISABLE` overrides enabling flags.
Shell-less connections withhold command-executing tools. Delivery and model use have separate evidence.

| Tool | Purpose | Exposure |
|---|---|---|
| `kb_search` | Search KB when its index has no fitting section; kb_get selected ids. | default |
| `kb_get` | Read page#section; a page alone lists section ids. | default |
| `kb_toc` | List page sections, or pages without path. | default |
| `mem_add` | Save a user-stated fact (near-duplicates merge). | default |
| `mem_search` | Find facts; project is an absolute directory. | default |
| `mem_forget` | Archive a scoped fact/lesson by id. | default |
| `lesson_add` | Save a verified fail-to-pass fix or user correction. | default |
| `lesson_search` | Find lessons for the current step. | default |
| `state_save` | Save goal, stage, decisions and next steps (4096 bytes). | default |
| `state_load` | Recover saved project work after resume/compaction. | default |
| `op_state` | Shared task board. Read status; checkpoint milestones. Graph gates prove done. | default |
| `session_note` | Checkpoint changes and next action (300 chars). | default |
| `session_recent` | Recent project checkpoints. | default |
| `session_search` | Search past conversations for dated decisions. | default |
| `skill_manage` | Draft/correct sourced methods. Evaluation gates adoption. | default |
| `plan` | Goal graph. Commands: new SLUG GOAL; ready SLUG; context SLUG ID; gate SLUG ID; status SLUG. Gate exit 0 proves done. | default |
| `run_checks` | Run this project's own tests/checks (found automatically, or cmd) and return only the failures and the summary (<=2 KB). Use after your last edit. | opt-in |

Additional default-off features are `check_guard`, `memory_snapshot` and `skill_nudge`.
`check_guard` checks test changes. The command guard is a distinct control.

## CLI commands

Use `harness COMMAND --help` for exact options.

`privileges` · `evidence` · `continuation` · `install` · `uninstall` · `status` · `explain` · `doctor` · `cache-status` · `source-coverage` · `source-inventory` · `warmup` · `update` · `learn` · `sync` · `model-registry` · `daily-discovery` · `self-update` · `improve` · `discover` · `run` · `review` · `vault-read` · `vault-document` · `vault-search` · `memory-page` · `memory-read` · `op` · `task` · `launch` · `loop-check` · `method` · `preset` · `handoff` · `workspace`

The separate `plan` CLI provides graph operations including new, context, ready, claim, gate, status and run.

Internal lifecycle entrypoints are client integration surfaces.

`_hook-stop` · `_hook-kimi-stop` · `_hook-kimi-precompact` · `_hook-prompt` · `_hook-context` · `_hook-op` · `_hook-capture`

## Templates and reusable prompts

Templates are stored under `content/templates`.

[handoff.md](../content/templates/handoff.md) · [learning-review.md](../content/templates/learning-review.md) · [loop-contract.json](../content/templates/loop-contract.json) · [procedure.json](../content/templates/procedure.json) · [source.json](../content/templates/source.json) · [task.md](../content/templates/task.md) · [worker.md](../content/templates/worker.md)

Reusable prompts are stored under `content/prompts`.

[explain-this-repo.md](../content/prompts/explain-this-repo.md) · [fix-failing-test.md](../content/prompts/fix-failing-test.md) · [plan.md](../content/prompts/plan.md) · [review.md](../content/prompts/review.md)

## Task presets

| Preset | Output contract |
|---|---|
| `source-notes` | Source-linked notes with page/section coverage and explicit inference labels. |
| `draft-message` | A preview draft with checked names, dates and purpose; sending is separate. |
| `project-reconcile` | Current objectives, trade-offs, owners, dependencies, conflicting status and next checks. |
| `reproduce-science` | Bounded reproduction plan and evidence, fixed metric/seed/environment and retained negative results. |

## Models, extensions and external tools

Routing tiers are `quick`, `standard`, `deep` and `review`. `content/routing.toml` binds supported model/effort pairs from the account configuration. Advisory automatic progression ships disabled until configured and qualified.
`content/extensions.toml` contains curated optional editor extensions. `harness discover` supplies extension/plugin/MCP discovery and vetting. Installation depends on exact approval, supported pin/readback behavior and the client's installation capability. A catalogue listing does not establish installed or current compatibility.
Browser automation, GitHub/email connectors, PDF tooling and other app-provided tools are supplied by their host or explicit integrations. They are outside this package inventory. Profile-selected skills may replace or extend shipped guidance.

### Optional editor extension catalogue

These are curated source entries. Install only through supported editor tooling after reviewing the proposed list. Publisher metadata and compatibility require current verification.

| Extension | Purpose | Targets | Placement |
|---|---|---|---|
| `ms-python.python` | Python language support, environments, testing; the base every other Python tool builds on | vscode, cursor | remote |
| `ms-python.vscode-pylance` | fast type checking, completions and go-to-definition for Python | vscode | remote |
| `anysphere.cursorpyright` | Cursor's own Python language server, in place of Pylance which Cursor may not use | cursor | remote |
| `ms-python.debugpy` | Python debugger: breakpoints in scripts, tests and notebooks | vscode, cursor | remote |
| `charliermarsh.ruff` | Ruff linter and formatter: catches bugs and keeps research code tidy, in milliseconds | vscode, cursor | remote |
| `ms-toolsai.jupyter` | Jupyter notebooks and kernels inside the editor, on the server's Python | vscode, cursor | remote |
| `ms-toolsai.datawrangler` | official viewer and cleaner for CSV, Parquet and DataFrames (the CSV/Parquet viewer) | vscode | remote |
| `ms-vscode-remote.remote-ssh` | work on the Linux research server over SSH as if it were local | vscode | local |
| `anysphere.remote-ssh` | Cursor's own Remote-SSH, in place of Microsoft's which Cursor may not use | cursor | local |
| `redhat.vscode-yaml` | YAML validation and completion (CI, configs, job specs); its telemetry is turned off below | vscode, cursor | remote |
| `GitHub.vscode-pull-request-github` | review and merge GitHub pull requests and issues without leaving the editor | vscode, cursor | remote |
| `anthropic.claude-code` | Claude Code in the editor, sharing the harness setup in ~/.claude | vscode, cursor | remote |
| `openai.chatgpt` | the Codex IDE extension, sharing ~/.codex/config.toml and AGENTS.md with the CLI | vscode, cursor | remote |

### Model-family policy

These roles are declared task hypotheses. Account visibility, supported effort and independent outcomes constrain use. They carry no comparative benchmark claim.

| Family | Configured model | Effort | Intended role |
|---|---|---|---|
| luna | `gpt-6-luna` | low | bounded extraction and individual-source triage |
| terra | `gpt-6.1-terra` | medium | grouped notes and routine synthesis, subject to task checks |
| sol | `gpt-6.1-sol` | high | implementation and conflicting-source synthesis |
| astra | `gpt-6-astra` | high | explicit escalation for difficult or high-impact decisions |

## Declared adapter support

This table comes from `matrix.py`. It describes integration surfaces; native end-to-end verification is client-specific. Use `harness status --matrix` for reasons and current selection.

| Adapter | Guard | Plan | Memory | Review | Run | Discover | Capture | Improve |
|---|---|---|---|---|---|---|---|---|
| claude-code | available | available | available | available | available | available | available | available |
| codex | limited | available | available | available | available | available | limited | available |
| copilot-vscode | limited | available | available | limited | limited | available | limited | available |
| cursor | limited | available | available | limited | limited | limited | limited | available |
| kimi | available | available | available | available | available | available | available | available |
| gemini | limited | available | available | limited | limited | limited | limited | available |
| agents-md | limited | limited | limited | limited | limited | limited | limited | limited |
| claude-desktop | limited | limited | available | limited | limited | limited | limited | available |
| jupyter-ai | limited | limited | available | limited | limited | limited | limited | available |

The JSON companion retains each limitation's reason. The `agents-md` adapter exports rules only. A native guard hook is installed for Claude Code and Kimi Code; Codex retains its own native sandbox and approvals.

## Memory and knowledge boundaries

The operational board stores task state. Project memory retains source-linked revisions. Facts and lessons have scoped stores. Search indexes are derived views. Profile `kb_paths` selects document sources, and session search handles explicitly supported local history formats. A useful handoff names evidence and the next action.
Domain coverage depends on the supplied sources and their freshness. This package's mechanism and methodology documents are distinct from a deployment's personal or organizational knowledge vault. Cross-device synchronization requires separate configuration and verification.

## Development and GitHub delivery

The [delivery playbook](DEVELOPMENT.md) covers task/issue scope, branches, PR evidence, CI/CD, reviews, releases and stack-specific check selection. It includes small task/PR/release draft examples. Those documented examples supplement the seven shipped file templates. Repository settings and observed checks establish enforcement.

## Current evidence

The release candidate's [qualification report](v3/qualification-20261113.md) records the four-pair memory result, retained failed learning trials and remaining gaps. The [interview pack](../examples/interview/README.md) exercises installed CLI/MCP processes with disposable data and zero model calls. Generated-procedure adoption remains held after token regression.
