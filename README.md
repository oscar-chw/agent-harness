# Agent Harness

Shared task state, source-backed memory and executable completion checks for AI coding clients.

**Current runtime release — v3.0.0rc2.** The candidate is installed and checked on Mac Studio and the research connection account. MacBook readback and broader learning efficacy remain open. [Release](https://github.com/oscar-chw/agent-harness/releases/tag/v3.0.0rc2)

[![CI](https://github.com/oscar-chw/agent-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/oscar-chw/agent-harness/actions/workflows/ci.yml)
[![Lint](https://github.com/oscar-chw/agent-harness/actions/workflows/lint.yml/badge.svg)](https://github.com/oscar-chw/agent-harness/actions/workflows/lint.yml)

[Walkthroughs](docs/walkthrough/README.md) · [Run the interview demo](examples/interview/README.md) · [All capabilities](docs/CAPABILITIES.md) · [Architecture](examples/interview/architecture.svg) · [Evidence](docs/v3/qualification-20261113.md) · [Install](#install)

## What happens when a session starts

A configured client starts its own local MCP process. The server selects the canonical project, supplies a bounded task-board packet, and exposes scoped memory and document tools. Later tool-response boundaries deliver changed board rows. Independent sessions use the same local records. Small questions can stay direct, while material work can use the graph, checkpoints and executable gates.

```mermaid
flowchart TB
    clients[Native clients and selected models]
    gateway[Per-client MCP process and supported lifecycle hooks]
    board[(Project task board)]
    memory[(Source-backed memory and retrieval)]
    workGraph[Work graph and executable gates]
    controls[Command guard and existing execution authority]
    work[Tools, tests and artifacts]
    evaluation[Evaluation and scoped adoption]
    clients --> gateway
    gateway <-->|Read and checkpoint| board
    gateway <-->|Retrieve and record| memory
    gateway -->|Plan tool when enabled| graph
    workGraph --> controls
    controls --> work
    work -->|Failed gate returns pending| graph
    work -->|Observed outcome and measured cost| evaluation
    evaluation -.->|Qualified candidate only| memory
```

[Open the full architecture](examples/interview/architecture.svg) · [Printable PDF](examples/interview/architecture.pdf) · [Mermaid source](examples/interview/architecture.mmd)

The board coordinates progress. The work graph owns dependency scheduling and gate settlement. Memory retains evidence and revisions. Models keep their native account, tool and approval boundaries. The shared store is local to an authorized home and canonical project. Cross-device synchronization needs separate configuration and verification.

## Four connected directions

| Direction | What it contributes | Where to inspect |
|---|---|---|
| Framework | Transactional task board, version conflicts, leases, recovery and work-graph execution | [Framework walkthrough](docs/walkthrough/framework.md) |
| Methodology | Intent framing, bounded research, implementation, testing, review and evidence-based iteration | [Methodology walkthrough](docs/walkthrough/methodology.md) |
| Philosophy | Assumptions, counterexamples, first principles and teaching adapted to the request | [Thinking and philosophy walkthrough](docs/walkthrough/philosophy.md) |
| Knowledge | Scoped source retrieval, retained corrections, facts, lessons and project handoffs | [Memory hierarchy walkthrough](docs/walkthrough/memory.md) |

These are task-dependent capabilities. A whole lifecycle is useful where dependencies, risk or recovery justify it.

## What ships

- **9 skills** for work loops, production code, debugging, tests, standards, verification, session memory, data-job trials and clear documentation.
- **17 MCP tool definitions**, covering knowledge, facts, lessons, saved state, task coordination, session inspection, method candidates and the work graph. `run_checks` is opt-in.
- **7 templates, 4 reusable prompts and 4 task presets**, with explicit input/output and permission contracts.
- **4 routing tiers**, constrained by configured model/effort support. Advisory automatic progression ships disabled until configured and qualified.
- **8 application adapters and a rules-only adapter**, with different native capabilities. Claude Code and Kimi Code receive command guard hooks. Codex uses its native sandbox and approval system.
- **Discovery, review, learning and maintenance commands** for explicit operation. Optional extensions and host-provided tools retain their own installation and access boundaries.

The [complete catalogue](docs/CAPABILITIES.md) lists every shipped skill, MCP tool, CLI command, template, prompt, preset and adapter limitation. Its [JSON inventory](docs/CAPABILITIES.json) is generated from source. Profile-selected skills and host plugins can extend this inventory.

## A runnable demonstration

The interview pack exercises the installed runtime using a disposable project and home. It runs real CLI and MCP processes with zero model calls.

```sh
python3 examples/interview/demo.py --output demo-run
```

It demonstrates cold-session pickup, a genuine failing test gate, an independent reader recovering the failure, rejection of an old-version update, and a fix passing the unchanged tests. A running reader receives the changed board once. The next unchanged boundary adds zero board bytes.

Open `examples/interview/guide.html` for the offline architecture, five-minute presenter sequence, recorded CLI replay and source-backed technical Q&A. The optional native-model follow-up has a separate client-specific setup and remains unrun.

## What has been measured

| Evidence | Observed result | Scope |
|---|---|---|
| Current memory against retained source history | 111,825 → 99,886 observed input/output tokens, **10.68% fewer** | 4 authored pairs, matched model/effort/facts, 4/4 correct in each arm; packet-level result |
| Generated-procedure trial | Candidate-charged 172,569 tokens against baseline 48,969 | Adoption remains held; failed trials and preparation costs retained |
| Full reasoning-guide treatment | +3.38% tokens and one response-length failure | Treatment remains unadopted; learner transfer unmeasured |
| rc2 release regression | 3,021 passed, 2 skipped, 2 expected failures | Release-bound run; newer documentation/demo checks are reported by CI |
| Installed readback | Mac Studio and research account passed cold MCP, board and stale-write checks | MacBook readback remains unverified |

Cached input is included in the memory comparison. Four authored pairs leave general coding productivity, reliable speed gains and net whole-project savings unqualified. [Full protocol and limits](docs/v3/qualification-20261113.md)

Historical guard, recall and component evaluations remain in [results](docs/results.md) and [design decisions](docs/design-decisions.md). Their original dates, small samples and qualification limits still apply.

## Install

Python 3.9+ is required. The package's default runtime uses the standard library.

```sh
git clone https://github.com/oscar-chw/agent-harness.git
cd agent-harness
python3 bin/harness install --dry-run
python3 bin/harness install
python3 bin/harness status --matrix
```

Inspect the dry run first. Installation replaces selected instruction files and merges supported client settings, with backups recorded for uninstall. Profile overrides and existing deployment policies require review. [Installation and rollback details](docs/usage.md)

An interview demo requires an existing harness installation. Its default runtime is `HARNESS_HOME`, or `~/.agent-harness`. The demo creates separate disposable state inside the chosen output directory and refuses an existing output directory.

## Trust and activation boundaries

- Board packets are advisory context. A passing graph gate establishes its declared outcome. Models can still misinterpret instructions, and gates can still be incomplete.
- Command screening, native approvals and operating-system isolation are separate controls. Supported hooks and configured sandboxing determine the actual execution boundary.
- Source hashes and receipts bind identity and revision. Semantic correctness needs independent outcome checks.
- Generated methods stay candidates until their exact scope passes the adoption rules. Self-improvement here changes retained context and procedures through evaluation; model-weight training remains outside the implemented learning path.
- Knowledge coverage depends on accessible, selected sources and freshness. Personal and organizational vault content stays deployment-specific.

## Documentation and source

[Capability catalogue](docs/CAPABILITIES.md) · [How it works](docs/how-it-works.md) · [Usage](docs/usage.md) · [GitHub and delivery practices](docs/DEVELOPMENT.md) · [All diagrams](docs/DIAGRAMS.md) · [Interview questions](examples/interview/technical-notes.md) · [Documentation index](docs/README.md)

```text
src/agent_harness/    adapters, MCP, board, memory, routing, review and graph
content/             rules, skills, templates, prompts and policy catalogues
examples/interview/  runnable isolated demo and offline presentation guide
eval/                evaluation instruments and scoped result records
tests/               behavior, integration, property and evaluation checks
profiles/            deployment-specific configuration examples
```

## Credits and licence

The project references Hermes-style memory and skill mechanisms, the Agent Skills format and the Model Context Protocol. The work graph originated in agentic-os. Research references and adoption verdicts remain in the dated design documents. MIT licence. [LICENSE](LICENSE)

Implemented with AI coding agents under Oscar's requirements and iterative review.
