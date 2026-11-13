# Framework and orchestration

The framework preserves enough shared state for another process to continue work, while executable gates record task outcomes. Each connected client keeps its own model, login and native execution controls.

## Mechanism

1. The client launches a local MCP process in an authorized project directory. The connection captures that directory for its operational scope.
2. The board resolves the Git root and uses a SHA256 of the resolved root path to select a local SQLite database under HARNESS_HOME.
3. Initialization emits a bounded board packet. Later tool responses deliver changed visible rows. Per-reader signatures suppress unchanged work and lease-renewal noise. Omitted rows remain available for later inspection.
4. Writers supply the task version they observed. SQLite transactions commit the task projection, event and retry receipt together. A stale expected version causes a conflict. Reusing the same request ID and exact inputs replays the committed result.
5. The work graph selects dependency-ready nodes, records ownership/leases and runs declared gate commands. A failed gate returns the node to pending with evidence. A blocked permission needs its own recovery path.
6. A checkpoint records findings, linked evidence and the next action at a meaningful boundary. A fresh connection reads the saved state.

The coordination store serializes transactions through BEGIN IMMEDIATE. This is a local multi-process design. A deployment across several hosts needs a separately verified synchronization or service boundary.

## Example

The [interview demo](../../examples/interview/README.md) publishes a free-shipping task. Reader A starts as a new MCP process and receives it. A test gate fails at the threshold. Reader B starts independently and receives the failure and next action. A writer still expecting the earlier version is rejected. After the prepared fix, the same tests pass and Reader B receives the update once.

## Tradeoffs

- SQLite keeps the default deployment small. Serialized transactions can become a bottleneck as contention grows.
- CAS protects board updates. An external database, filesystem or deployed service needs equivalent protection for its own side effects.
- Leases and fencing reject stale ownership operations. A ledger flag alone cannot terminate an active worker.
- Host directory and harness home determine scope. A second checkout or worktree can resolve to a different board. A matching task name alone cannot join those scopes.
- The graph represents task dependencies. Iteration records another attempt or revises the plan when evidence changes its premise. Dependency cycles remain invalid.

## Evidence and limits

The demo proves CLI/MCP process behavior with zero model calls. Separate tests exercise concurrent publications, stale writes, recovery and bounded delivery. Emitted instructions establish delivery. Actual model interpretation and compliance need behavioral evidence.

Mac Studio and the research account passed installed rc2 readback. Loaded clients need a fresh connection to load updated code. MacBook readback remains unverified.

## Implementation

[MCP lifecycle](../../src/agent_harness/mcp/server.py) · [Shared-board delivery](../../src/agent_harness/shared_board.py) · [Transactional state](../../src/agent_harness/operational_state.py) · [Client lifecycle observations](../../src/agent_harness/board_hooks.py) · [Work graph](../../src/agent_harness/workgraph/plan.py) · [Qualification](../v3/qualification-20261113.md)
