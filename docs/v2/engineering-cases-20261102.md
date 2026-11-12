# Engineering judgment from production cases

Research sidecar for full-stack, interview and dev-ops work. These cases are prompts for reasoning from constraints, not templates to copy. Company descriptions below are attributed as documented; conclusions labeled **Inference** are transfer lessons, not findings measured in this harness. Nothing here establishes that reading these cases improves a model. That would need a matched evaluation.

## Evidence and acquisition

Reviewed 2 November 2026. Five primary engineering sources were read at the relevant decision and limitation sections. Read depth below distinguishes full-page access from focused section reading; unrelated page material was not treated as evidence. GitLab's modular-monolith handbook page was attempted but timed out, so it is not counted or used. No upstream code was fetched or run; a separate open-source application interface was not needed to answer this case set.

| Primary source | Date and read depth |
|---|---|
| [Shopify, “Under Deconstruction: The State of Shopify’s Monolith”](https://shopify.engineering/shopify-monolith) | 16 Sep 2020. Full article opened; focused reading of initial goals, dependency-density discussion, alternative decomposition strategies and reported current state. |
| [Shopify, “A Packwerk Retrospective”](https://shopify.engineering/a-packwerk-retrospective) | 7 Feb 2024. Full article opened; focused reading of package/dependency model, privacy checks, failed isolation result, costs and revised direction. |
| [Amazon Builders’ Library, “Making retries safe with idempotent APIs”](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) | Article page has no publication date displayed in the fetched content; AWS announced it in Jan 2021 ([announcement](https://aws.amazon.com/about-aws/whats-new/2021/01/new-abl-article-making-retries-safe-with-idempotent-APIs/)). Read the workflow, duplicate-intent, atomicity, semantic-response, late-request and parameter-mismatch sections. |
| [Google SRE Book, “Handling Overload”](https://sre.google/sre-book/handling-overload/) | Copyright 2017. Read the overload signals, local-vs-global overload, retry budgets, retry-layer rule and limitations sections. |
| [Stripe, “Designing robust and predictable APIs with idempotency”](https://stripe.com/blog/idempotency) | 22 Feb 2017. Full article opened; focused reading of ambiguous network outcomes, idempotency-key behavior, exponential backoff and jitter. |

## Cases

### 1. Shopify: make a large monolith easier to change without assuming the ideal boundary is already real

**Context and constraints — documented.** Shopify described a Rails monolith with more than 2.8 million Ruby lines and 500,000 commits, worked on by hundreds of developers. The stated goals were smaller mental models, narrower test runs and safer changes behind contracts. The organizational constraint mattered: a central architecture group lacked the context and reach to refactor every domain alone.

**Decision — documented.** Shopify chose to first group the main monolith by commerce subdomains and assign stewardship. That made ownership and a visible partition useful before strong boundaries were complete. For other applications, it also tried the reverse sequence: first carve out small units with strong boundaries, leaving an unstructured remainder. The first path favored ownership and an understandable map; the second favored clean examples and working isolation. Shopify explicitly said to choose based on which intermediate state is more useful. It also described extracting storefront rendering for separate high-throughput, read-only scaling and card vaulting for sensitive-data isolation, while warning that services add distributed-system complexity.

**Strong alternative.** Start with a small, isolated component and move responsibilities into it incrementally. This is preferable when clean boundaries and an executable example matter more than immediately assigning every legacy file to a domain.

**Failure, limit and reversal — documented.** The domain-first approach left most components without strong boundaries because legacy dependencies made the work large. A dense graph, with each component depending on over half the others and many cycles, defeated independent reasoning. The carve-out-first approach left a large “ball of mud” beside its clean components. Neither order avoids an unfinished state. Shopify also reported unresolved cross-component query/reindex coupling. It would revisit the choice if ownership remains unclear (favor a visible domain map), or if the map has little enforcement value while new work can be cleanly isolated (favor carve-outs). Service extraction becomes more compelling when an independently scalable workload or data-isolation boundary outweighs network, deployment and operational costs.

**Inference for a new task.** Before drawing a module boundary, identify which change becomes safer or easier, who owns the code, what data/query flows cross it, and what intermediate state provides value. A folder rename or dependency rule is not proof of a useful module. Prefer the smallest boundary that matches observed change and ownership patterns; revise the boundary when actual dependencies contradict it.

### 2. Shopify: a static boundary check can pass while the component is still unusable

**Context and constraints — documented.** Packwerk lets teams declare packages and a non-circular dependency graph, then checks Ruby constant references against those declarations. It can record existing violations as debt and prevent new ones. Shopify also used privacy checks to designate public and private constants.

**Decision — documented.** Shopify initially treated domain-shaped packages and privacy boundaries as a route toward independent components. In practice, teams found that finishing a package’s violation list did not mean its code could run in isolation. They broadened the definition of progress toward executable results. Later, they described using a domain component as an organizational grouping around one or more functionally defined packages: the former supports human ownership and a domain mental model; the latter can be a real dependency/runtime unit.

**Strong alternative.** Enforce only a smaller, actionable dependency rule, while validating a claimed component with its real execution or test seam. Adjust package layout when a reported violation reveals that the proposed graph does not match how code works.

**Failure, limit and reversal — documented.** A package could reach the static-analysis “finish line” and remain broken and unusable alone. Privacy checks are attractive but add technical debt and have blind spots; Shopify said it had considered removing Packwerk, while retaining value in preventing new dependencies at a base layer. A violation may signal a poor code dependency, or a graph that models the system badly. If the check produces costly cleanup without executable isolation or useful containment, narrow or redesign the check. Keep it when it prevents meaningful new coupling at acceptable cost.

**Inference for a new task.** Ask what property the gate observes and what outcome it cannot observe. Pair a structural rule with the smallest real execution test of the claimed boundary; do not report “modular” based only on directories, dependency diagrams or green static checks.

### 3. Amazon: retries are an API contract about intent, not just a client loop

**Context and constraints — documented.** An EC2 launch workflow coordinates placement, volumes, networking and a VM. A timeout can leave the caller uncertain whether a resource was created. Retrying can create duplicates; reconstructing intent afterward is costly and can still be ambiguous if another actor created a similar resource.

**Decision — documented.** For operations requiring at-most-once behavior, Amazon favors a caller-provided request identifier. The service associates that identifier with the initial parameters and makes the operation atomic with recording the identifier. Repeating the same intent can return a semantically equivalent result; reusing the identifier with changed parameters returns a validation error. The service retains request knowledge for a bounded lifetime chosen for the resource and late-request risk. AWS SDK/CLI behavior can generate and reuse a token for operations that expose the idempotent contract.

**Strong alternative.** For a naturally idempotent operation, use a resource address and desired state (for example, replace a named record) so repetition has no additional side effect. This is simpler when the domain operation truly has that semantic. Another option is reconciliation after ambiguous outcomes, accepting more client logic and residual ambiguity.

**Failure, limit and reversal — documented.** Deriving duplicate identity from equal parameters can confuse two distinct user intentions, such as two launches with identical configuration. Recording the token separately from the resource can fail in either direction unless made atomic. A late retry after another actor deletes the resource raises a lifecycle-policy choice; Amazon retains the original request meaning for EC2 for a defined interval, but says retention needs vary by service. Building this contract costs service complexity and is not right for every operation. Choose the simpler contract when duplicate effects are harmless or an explicit at-most-once promise is not worth the storage, atomicity and retention work. Revisit if clients cannot recover safely from an ambiguous timeout or duplicate effects become consequential.

**Inference for a new task.** First classify the operation: desired-state/idempotent, repeatable-but-not-identical, or side-effecting with ambiguous completion. For the last class, decide token scope, parameter binding, atomic persistence, replay response and retention before adding automatic retries. Never infer that an HTTP verb, retry count or client-side deduplication alone makes a write safe.

### 4. Google SRE: retry locally only when there may be spare capacity, and cap amplification

**Context and constraints — documented.** Google describes a large RPC fleet where some individual backend tasks can be overloaded while other tasks still have capacity; alternatively, overload may affect a large share of the datacenter. Its implementation has task-local utilization signals, request criticality, client retry history and overload-specific error responses. These are fleet-scale mechanisms, not a recipe for a single web service.

**Decision — documented.** A task rejects work based on utilization and criticality. If only a small subset of tasks is overloaded, retrying an overload response can act as load balancing. If a large subset is overloaded, retries should stop and the error should reach the caller. Google bounds attempts (three in the described implementation), also applies a per-client retry budget, and propagates “overloaded; don’t retry” upward. In a dependency stack, only the layer immediately above the rejecting service retries, avoiding multiplicative retries at every layer.

**Strong alternative.** Bubble the error immediately, or provide a degraded response, when a retry is unlikely to find capacity, the action is not safe to replay, or the extra work is more harmful than the transient error. For a smaller service, a simple bounded retry budget and explicit overload response may be easier to reason about than fleet-wide adaptive throttling.

**Failure, limit and reversal — documented.** Even three attempts can approach 3x traffic in a worst case; rejected work consumes resources too. Local retries help only when spare capacity is plausible and the operation can be replayed safely. Google’s approach relies on extensive local signals, request metadata and many participating backends; latency geography and sparse clients can weaken it. If retry metrics rise across the fleet, capacity is globally scarce, or rejection is expensive, reduce or stop retries. If overload is localized and alternate capacity exists, a bounded retry may recover useful work.

**Inference for a new task.** Distinguish a transient failure, a single unhealthy instance and system-wide overload. Name who owns the one retry, the maximum attempts/budget, the total deadline, and what signal ends retries. If those facts are unknown, do not copy Google’s three-attempt setting as a default.

### 5. Stripe: the client can know a write succeeded even when it never receives the response

**Context and constraints — documented.** Stripe frames a request across two servers as a distributed system. A connection may fail before work starts, midway through work, or after the operation succeeds but before its response reaches the caller. From the client’s perspective, the last two outcomes can be ambiguous.

**Decision — documented.** Stripe accepts an `Idempotency-Key` for mutating POST operations. The client retries an uncertain operation with the same key; the server associates it with the operation and can return the prior successful result rather than applying the side effect again. The article also recommends exponential backoff and random jitter to reduce load and synchronized retry bursts.

**Strong alternative.** If an operation is naturally idempotent under its resource semantics, use that simpler behavior. If the server cannot durably bind key and effect, do not present retry-with-key as an exactly-once guarantee; use reconciliation or surface an unresolved result for explicit recovery.

**Failure, limit and reversal — documented and bounded.** Retry storms can worsen an incident; jitter spreads calls but does not create capacity. The article is a 2017 design explanation, not a current Stripe API specification. Its sample describes a successful cached result and says interrupted work must be recovered or rolled back according to implementation. It does not specify every current endpoint’s key retention, mismatch behavior or transaction boundary. Verify the actual API contract before depending on those details. If retries are driving overload, stop or shed work; if the current endpoint does not promise idempotency, do not assume the pattern applies.

**Inference for a new task.** Trace the three network outcomes explicitly and decide what the caller sees after each. Use the same operation key across retries, but make key lifetime and payload mismatch part of the API contract. Backoff controls timing; idempotency controls duplicate effects. Neither substitutes for the other.

## Transfer prompts for a new task

Use these as short design-review or interview prompts. Answer from the supplied workload, domain and operational constraints; state assumptions when they are missing.

1. **Boundary choice:** A growing application has one high-change checkout flow, shared product/customer models and a small team. What concrete change pain justifies a new module? Who owns it, which calls/data cross the boundary, and what executable check would prove useful isolation? What evidence would make you keep it in the existing module?
2. **Architecture counterfactual:** Two teams need independent release cadence, but both read and update the same transactional rows. Would you split into services now, establish an in-process boundary first, or keep one module? Compare transaction consistency, deployment coupling, team ownership and operational burden. What expected scale or data-isolation change would reverse the choice?
3. **Ambiguous write:** A user submits “create payment,” the server commits, then the connection drops. What must persist so the retry does not charge twice? What if the retry changes the amount but reuses its key? What if the first request is still in flight?
4. **Retry counterfactual:** An API returns overload because one host is hot; half the pool appears healthy. Which layer retries, how is work bounded, and how does it avoid returning to the same host? Now suppose 80% of hosts reject and retry traffic is 25% of total. What changes?
5. **Dev-ops degradation:** A queue is growing, the worker pool is saturated and retries are increasing. Which work is valuable enough to preserve, what can be rejected/degraded, where does the deadline propagate, and what measurement would show recovery rather than just shifted backlog?
6. **Gate challenge:** A dependency check passes, but the component cannot start without the whole application. Which claimed property did the check actually establish? Add the smallest execution-level evidence needed, and name what still remains unproven.

For each answer, compare one plausible alternative, name the cost of the preferred choice, and give one observable condition that would reverse it. A recommendation without that reversal condition is likely a copied pattern rather than a context-aware decision.
