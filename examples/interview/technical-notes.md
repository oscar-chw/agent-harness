# Technical interview notes

Prepared from inspected source on 2026-11-13. Links use repository-relative paths and line anchors inspected in the current checkout. Historical measurements and installation statements below come from the dated qualification report and release handoff. The runnable demonstration checks installed mechanics separately from model behavior.

## 60-second first-person pitch

I developed a local harness for AI-assisted work across sessions. A transactional task board shares checkpoints and rejects stale updates. A work graph records executable completion checks. MCP supplies bounded context, and source-backed memory retains corrections. In four paired authored tasks, current memory used10.68%fewer observed tokens with4/4correct answers in both arms. I also evaluated generated procedures and withheld them after their token cost regressed. The release is a verified candidate on two targets. Broader task benefits and universal model compliance still need measurement.


## Core questions and answers

### 1. Why have both a shared board and a work graph?

The board lets sessions recover a project's current checkpoint, blocker and next action. The graph schedules dependency-ready nodes and records gate outcomes under a file lock. Keeping these responsibilities separate makes progress discoverable while preserving a concrete completion decision. Board activity labels and evidence hashes remain advisory, and a graph's completion claim is limited by the quality of its gate. [Board contract](../../src/agent_harness/operational_state.py#L1), [graph claims](../../src/agent_harness/workgraph/plan.py#L1233), [gate settlement](../../src/agent_harness/workgraph/plan.py#L1629)

### 2. Why use SQLite for coordination?

SQLite gives local CLI and MCP processes a transactional coordination store. `BEGIN IMMEDIATE` covers schema creation and each operation, with task projection, event and replay receipt committed together. This keeps deployment simple at the cost of serializing access, including snapshot transactions through the same helper. The implementation has a 30-second connection timeout, database page cap and 10,000-event ceiling, and its scope is local project coordination. [Database lifecycle](../../src/agent_harness/operational_state.py#L42), [transaction contents and cap](../../src/agent_harness/operational_state.py#L297)

### 3. How does compare-and-swap prevent lost updates?

A caller supplies the task version it observed as `expected`. Inside the transaction, `_mutate` compares that value with the stored version before applying a transition and incrementing the version. If two writers read version 3, the first can publish version 4 and the second receives a conflict, requiring a refreshed decision. This introduces explicit retry handling, and the version check covers the board row while memory receipts undergo separate currentness checks. [Version comparison](../../src/agent_harness/operational_state.py#L297), [snapshot consistency](../../src/agent_harness/operational_state.py#L209)

### 4. What happens if a response is lost after commit?

Request IDs let the caller safely repeat a committed board operation. `_mutate` hashes task, expected version, action and arguments, then stores the result in the same transaction as the mutation. An identical retry returns that result before checking the now-advanced task version, while reusing the ID with changed inputs raises a conflict. Replay storage consumes space, and this guarantee covers recorded board transitions with external side effects requiring their own retry discipline. [Replay and atomic recording](../../src/agent_harness/operational_state.py#L297)

### 5. Why combine lease expiry, a token and a fencing counter?

These fields prevent an obsolete claimant from renewing or releasing current ownership. Each successful claim increments `fence`, returns a random token and stores its digest in the task row, while `_owned` checks status, expiry, fence and token. This adds ownership checks beyond a timeout at the cost of carrying lease metadata on requests. Enforcement covers these board transitions, and an external worker or storage sink needs its own ownership enforcement to reject stale side effects. [Claim and ownership checks](../../src/agent_harness/operational_state.py#L429), [renew and release](../../src/agent_harness/operational_state.py#L459)

### 6. How do updates reach a fresh MCP client?

The server captures its launch directory to keep the connection's operational project scope stable. Initialization appends board context to instructions, and subsequent successful or rejected tool calls can append changed board context to their responses. This reuses existing request boundaries and avoids a background messaging loop, with update latency depending on those boundaries. Delivery establishes that text was emitted, while model attention, correct interpretation and compliance require separate behavioral evidence. [Connection scope](../../src/agent_harness/mcp/server.py#L195), [initialization and tool responses](../../src/agent_harness/mcp/server.py#L420), [qualification boundary](deployment-status.md)

### 7. How do you prevent repetitive board context?

Each connection hashes visible row content while excluding version, fence, expiry and update cursor. Only rows admitted to the bounded brief are marked delivered, and identical initial checkpoint publications can coalesce inside the write transaction. This reduces renewal noise and duplicate checkpoints while preserving pending rows that exceeded the packet budget. Connection-local delivery state resets on reconnection, and truncation plus omission counts leave the full checkpoint necessary for detailed decisions. [Reader delivery state](../../src/agent_harness/shared_board.py#L21), [publication](../../src/agent_harness/shared_board.py#L48), [transactional coalescing](../../src/agent_harness/operational_state.py#L314), [bounded brief](../../src/agent_harness/operational_state.py#L233)

### 8. How does a memory correction avoid silently rewriting history?

Corrections append immutable revision records linked to the prior receipt and journal hash. `append` compares the expected receipt, preserves ownership and access fields, and refuses changes to a withdrawn identity. This retains an auditable history at the cost of journal growth and repeated validation, with superseded reads requiring explicit historical access. A receipt binds retained bytes, while a proposed verified paraphrase becomes pending unless every cited span directly matches the assertion. [Journal validation](../../src/agent_harness/project_memory.py#L96), [correction and confidence rules](../../src/agent_harness/project_memory.py#L148), [historical reads](../../src/agent_harness/project_memory.py#L227)

### 9. How do lexical search and FTS5 interact?

Shared-note retrieval reads only explicitly allowed document IDs under a pinned manifest. Its FTS5 path builds an in-memory candidate index over normalized tokens, then both backends use the same BM25 scorer. Rebuilding avoids a persistent derived index for this bounded pilot, with extra per-query construction cost and limits of 100 notes and 4 MiB of text. FTS errors raise explicitly, lexical scores express overlap, and line-window omissions expose the excerpt's limited context. [FTS candidate selection](../../src/agent_harness/vault_retrieval.py#L10), [scope and limits](../../src/agent_harness/vault_retrieval.py#L26), [ranking and citations](../../src/agent_harness/vault_retrieval.py#L75)

### 10. What exactly does the 10.68% result establish?

Four authored pairs compared retained source-revision history with a current source-bound memory packet using matched models, effort, facts and answer requirements. Both arms answered 4/4 correctly, with observed input-plus-output tokens falling from 111,825 to 99,886, a 10.68% packet-level reduction. Cached input counts are included, and memory updates used zero model calls. Four pairs provide a narrow readback result, while reliable speed effects, general coding benefits and net whole-project savings remain unqualified. [Paired design and results](../../docs/v3/qualification-20261113.md#L15), [accounting scope](../../docs/v3/qualification-20261113.md#L34), [earlier qualification cost](../../docs/v3/qualification-20261113.md#L52)

### 11. Why was the generated self-improvement method rejected?

The adoption decision accounts for the full cost of generating and evaluating a procedure. The nine-call experiment consumed 221,538 tokens, with candidate-charged cost of 172,569 against a 48,969-token baseline, so procedural learning remains held. MCP permits source-bound drafting and correction while rejecting direct skill creation or updating, accepting slower adoption to retain explicit evaluation. The mechanism changes retained procedures and context with no weight training, and general self-learning efficacy remains unearned. [Cost and decision](../../docs/v3/qualification-20261113.md#L84), [MCP write restrictions](../../src/agent_harness/mcp/server.py#L309), [remaining qualification](deployment-status.md)

### 12. How does the command guard relate to OS permissions?

The graph checks gate commands itself because subprocess execution creates a path beyond an agent's ordinary tool hook. A guard refusal records `NOT_RUN` and a persistent permission hold, while execution uses the configured sandbox prefix when available. This adds command screening but depends on enabled guard configuration, and the source includes an explicit off switch. Native approvals and OS permissions retain their own enforcement, while MCP's `--no-shell` suppresses the command-executing tools exposed to a client. [Guard evaluation](../../src/agent_harness/workgraph/plan.py#L1517), [execution and refusal](../../src/agent_harness/workgraph/plan.py#L1597), [persistent hold](../../src/agent_harness/workgraph/plan.py#L1676), [shell capability suppression](../../src/agent_harness/mcp/server.py#L502)

### 13. How is routing bounded by actual capabilities?

Routing selects an admissible next attempt from explicit task facts, configured tiers and independent gate receipts. `next_decision` binds context, policy and model inventory, then checks artifact hashes, usage budgets, tier ceilings and the exact supported model-effort pair. This favors an explicit hold when inputs are stale or unsupported, with less automatic fallback flexibility. The progression decision currently accepts Codex state and returns advice, while dispatch and successful model behavior require separate evidence. [Task-derived minimum](../../src/agent_harness/routing.py#L163), [decision scope and bindings](../../src/agent_harness/routing.py#L178), [gate evidence and capability checks](../../src/agent_harness/routing.py#L273)

### 14. How do recovery paths preserve the original failure?

Recovery makes a continuation possible while retaining the reason work stopped. Board resume rechecks checkpoint, evidence and memory currentness, and graph recovery requires the exact held gate hash, a resolution reason and current guard acceptance. The graph writes a durable recovery record and returns the node to pending with `NOT_RUN`, adding another step before gate execution. An active leased worker requires separate stopping, and native or worker denials require their own resolution path. [Board stop and resume](../../src/agent_harness/operational_state.py#L398), [exact-bound graph recovery](../../src/agent_harness/workgraph/plan.py#L1293)

### 15. What is earned at deployment time?

Deployment receipts establish which package and entry points an installed process actually uses. The dated release handoff records rc2 publication, package bindings, and cold installed MCP, board and stale-write checks on Mac Studio and the research connection account. Per-device readback and reconnecting loaded clients add operational work because installed files and loaded code can diverge. These are historical recorded results, stable v3 remains unearned, and MacBook installation remains unverified. [Recorded publication and installation](deployment-status.md), [loaded-code identity](../../src/agent_harness/mcp/server.py#L195), [release requirements](../../docs/v3/qualification-20261113.md#L101), [MacBook and stable-release limits](deployment-status.md)

## Three hard follow-ups

### A. The old worker wakes after its lease expires and writes an artifact. What stops it?

The board rejects stale lease renewals and releases through token, expiry and fence checks. Artifact writes need equivalent enforcement at their destination. The graph also rechecks ownership and lease before settlement, and versioned gates revalidate captured inputs before publishing a receipt. I would identify the side-effect boundary and require a fence-aware write protocol there before claiming end-to-end stale-worker exclusion. [Board enforcement](../../src/agent_harness/operational_state.py#L453), [graph settlement checks](../../src/agent_harness/workgraph/plan.py#L1629)

### B. Could four authored pairs be cherry-picked or cheaper only because development cost was excluded?

The report limits the claim to packet-level readback, retains 423,306 tokens from two earlier qualification runs, and leaves net project savings unestablished. I would defend the observed paired result and its matched conditions, then require a prespecified broader task distribution and complete development, evaluation and correction accounting for an economic claim. Those broader comparisons remain `NOT_RUN`. [Design](../../docs/v3/qualification-20261113.md#L17), [retained earlier costs](../../docs/v3/qualification-20261113.md#L52), [workplace comparison requirements](../../docs/v3/qualification-20261113.md#L93)

### C. A receipt is valid and a STOP message was delivered. Can the agent still act incorrectly?

Yes. Receipt validation establishes retained identity and current source binding, with semantic verification restricted to direct citation matches. A delivered STOP remains advisory context, and the board refuses to treat a flag as stopping an active lease. I would require independent behavior checks and execution-boundary enforcement before making a stronger compliance claim. [Confidence handling](../../src/agent_harness/project_memory.py#L165), [active-lease STOP restriction](../../src/agent_harness/operational_state.py#L398), [compliance limit](deployment-status.md)
