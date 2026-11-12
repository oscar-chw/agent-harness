# DeepSeek superagent: fit without a framework replacement

3 November 2026. **Decision: pattern-only reuse.**
Question: can its authorization/execution separation improve our existing harness
while retaining our graph, stores and permissions?

Pin: `6337fc823ce20251c8de8085948165c81aaa701e`.
**D**=[documented]; **C**=code observed, not executed; **M**=measured execution
(none here); **UNKNOWN**=not established. Recommendations are inferences.

**D/C:** [LICENSE][L]: MIT,2026 DeepSeek Harness Team; retain notices when copying;
no warranty. [README:3–9][R]: research prototype, not official/production-ready;
some article designs are future directions. Dependency-license audit UNKNOWN.

## Philosophy and authority

**D:** [000:5–31][P] prioritizes human attention: narrow authority, useful results,
no chatter, honest failures and proportional work; no efficacy evidence.

**D:** [001:27–43][D] separates Trigger, Mandate, Ticket and replaceable Assignment.
[002:18–44,91–141][A] separates subscribed context from authority, defaults inferred
work to observation and revalidates before resume. Policy changes notify live
work rather than immediately revoke it; execution judgment still matters.

**D:** [003:25–47,78–90][F]: worker sessions/directories run as operator without
command approval; wrappers are not isolation. Merge limits are prompt rules,
not host enforcement. Do not import that authority assumption.

## One static input -> ticket -> execution trace

**C:** Start with the permitted human Trigger used by the upstream fixture:
1. [intake:19–59][I] normalizes time, rejects duplicate IDs, applies listening
   scope, records the trigger, and fans context to subscriptions or queues Eval.
2. [evals:71–118,282–315][E] uses the policy gate to select admitted strength,
   rejects an obsolete policy-version decision, then builds a mandate carrying
   scope, actor, basis and policy version. Acceptance keys the ticket to the Eval.
3. [tickets:37–55][T] prepares/saves the ticket, subscribes threads, optionally
   queues acknowledgement and invokes executor.start.
4. [executor:264–284,424–469][X] queues launch, checks live/current assignment,
   prepares a directory if absent, ensures its worker session and delivers an
   assignment prompt with another current-state check.

**C, hand-derived expected result:** one allowed explicit input creates one
ticket/assignment; duplicate intake creates none; a changed policy cannot accept
the stale assessment. [tests:15–71,115–153,243–260][S] assert ticket/mandate/start,
rollback after prepare failure, policy-version rejection and stale-assignment
delivery refusal. The fixture uses in-memory repositories and mocked executor/
assessor; this is source evidence, not a real worker launch or durable delivery
measurement. No test/build/install/model run performed.

## Fit against what we actually have

**C, local source** (Python paths under src/agent_harness):
- workgraph/plan.py:1211ff,1513ff: claims, original gates and permission holds;
  retain these as completion authority, not a worker's ready report.
- operational_state.py:42–98,385–416: project-keyed transactional state,
  request records and fenced leases; not a fact store or permission boundary.
- workgraph/admission.py:208–245: overlap/capacity reservations. This resource
  admission is distinct from their permission-to-originate admission.
  plan.py:2770ff retains execution-unknown reservations.
- handoff.py:1–55 plus session-memory: bounded file-first packets, no routine
  messaging; preserve our history rather than add another coordination store.
- content/skills/work-loop/recovery.md:59–87: adaptive effect/target/risk judgment;
  lessons grant no authority and native refusals remain binding.

**Recommendation (inference):** reuse context/authority separation, explicit
material authorization basis in existing checkpoints, and late-attempt result
rejection. Reuse our versions/fences/gates; no framework/provider replacement.

**Later gap (inference):** authorized external intake needs identity/scope bound
to our task/attempt and pending-versus-delivered effects. A durable external
reply/launch bridge is not established here. Deduplication is not exactly-once
outside action.

**UNKNOWN/untouched:** runtime/efficacy/isolation, durable effects/outbox, source
adapters, panel/deployment, complete tests/dependency licensing. No saving or
native permission equivalence. Original gate remains NOT_QUALIFIED per root.

[L]: https://github.com/deepseek-ai/dsh-superagent-prototype/blob/6337fc823ce20251c8de8085948165c81aaa701e/LICENSE#L1-L21
[R]: https://github.com/deepseek-ai/dsh-superagent-prototype/blob/6337fc823ce20251c8de8085948165c81aaa701e/README.md#L3-L9
[P]: https://github.com/deepseek-ai/dsh-superagent-prototype/blob/6337fc823ce20251c8de8085948165c81aaa701e/docs/000-philosophy.md#L5-L31
[D]: https://github.com/deepseek-ai/dsh-superagent-prototype/blob/6337fc823ce20251c8de8085948165c81aaa701e/docs/001-domain.md#L27-L43
[A]: https://github.com/deepseek-ai/dsh-superagent-prototype/blob/6337fc823ce20251c8de8085948165c81aaa701e/docs/002-authorization.md#L18-L141
[F]: https://github.com/deepseek-ai/dsh-superagent-prototype/blob/6337fc823ce20251c8de8085948165c81aaa701e/docs/003-execution.md#L25-L90
[I]: https://github.com/deepseek-ai/dsh-superagent-prototype/blob/6337fc823ce20251c8de8085948165c81aaa701e/src/core/intake.ts#L19-L59
[E]: https://github.com/deepseek-ai/dsh-superagent-prototype/blob/6337fc823ce20251c8de8085948165c81aaa701e/src/core/evals.ts#L71-L315
[T]: https://github.com/deepseek-ai/dsh-superagent-prototype/blob/6337fc823ce20251c8de8085948165c81aaa701e/src/core/tickets.ts#L37-L55
[X]: https://github.com/deepseek-ai/dsh-superagent-prototype/blob/6337fc823ce20251c8de8085948165c81aaa701e/src/executor/dsh.ts#L264-L469
[S]: https://github.com/deepseek-ai/dsh-superagent-prototype/blob/6337fc823ce20251c8de8085948165c81aaa701e/tests/core-engine.spec.ts#L15-L260
