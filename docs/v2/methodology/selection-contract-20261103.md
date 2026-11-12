# Skill, tool and resource selection: development extension

3 November 2026. Assignment: the methodology section of
[`round2-20261103.md`](../../../handoffs/v2-completion/round2-20261103.md).
This extends the prior [case/evaluation contract](README.md); its artifacts and
receipts remain unchanged. Main owns runtime integration and all final
verification. No parent gate, runtime, installed recipe or native policy changes
are part of this extension.

## Decision contract

Choose resources for the next useful output under the current evidence,
authority, dependencies and budget. Decide separately whether the task needs a
skill, a tool, coordination, or a different model/effort. Available slots and
model names do not establish a benefit. A task label or the appearance of a
skill/tool keyword is insufficient evidence that using it helps.

| Question | Observable decision criterion | Failure to reject |
|---|---|---|
| Is a skill useful? | Its procedure addresses a real task uncertainty, matches the current owning source/version and has relevant exclusions. Inspect the needed section; preserve the original outcome check. | Load an irrelevant recipe because its name matches, apply stale advice, or call recall proof of successful adoption. |
| Is a tool necessary? | A required fact/result cannot be supplied reliably from authorized current inputs; the tool can obtain/check it within scope. Prefer an already available bounded equivalent when it produces the same required outcome. | Call tools for known arithmetic, invent a successful call to a missing MCP, or substitute local synthetic rows for required live data. |
| Does research resolve a gap? | Inspect authorized local evidence first; acquire only consequential missing/current facts. Source support and currency matter, not the number of URLs or tool calls. | Guess a missing technical fact, or ask the user to diagnose evidence that the agent can inspect. |
| Is parallel work useful? | Necessary independent outputs, exclusive write scopes, available capacity, deadlines, privacy and a parent integration check justify bounded workers. | Fill slots on a tiny task, duplicate work, race on one file, leak context, oversubscribe resources or accept one child as the parent. |
| Is another resource tier warranted? | Use explicit task impact/uncertainty, independently bound failed checks and actual supported pairs within the declared ceiling/budget. Check the failure cause before a costly retry. | Treat the tier order as a measured capability/speed ranking, escalate on worker self-report, or bypass an unavailable pair. |

An observed failure must connect original intent, actual result and acceptance
gap to competing causes and a discriminating check. For example, an absent
executable and a malformed input require different repairs. A larger model or
more helpers does not resolve that distinction by itself. A current adequate
passing receipt suppresses needless diagnosis of the older failure; changed
artifacts or source inputs invalidate the relevant prior receipt.

## Frozen cases and counterexamples

[`selection-cases-20261103.json`](selection-cases-20261103.json) is visible,
synthetic **development** material: eight scenarios, each with a control and
changed-evidence variant. Expectations were recorded before implementing the
new checker. They are not real user episodes, held-out tasks or native outcomes.

| Scenario | Control outcome | Changed constraint and outcome |
|---|---|---|
| Direct no-tool question | `6 × 7` gives 42 directly, with no tool/helper | Required answer now depends on local row semantics: inspect/check the data. |
| Local SQL | Sum `(100, 50)` once per order: 150; a line-item join's 250 fails | Request counts line items instead: all three rows count; deduplication is now wrong. |
| Uncertain research | Inspect scoped local evidence, then current official facts for absent unstable limits; disclose unavailable evidence | A complete supplied excerpt comparison needs no new live-service research. |
| Independent branches | Bound separate owners and outputs, preserve parent integration | Shared generated writes and one available slot require serialization, retaining valid work. |
| Failed gate | Diagnose intent/result/gap and use a discriminating probe before causal repair; keep the original check | A corrected artifact has current acceptance: report it rather than repeat old diagnosis. |
| Stale recipe | Revalidate against incompatible current v2 owning requirements; do not apply v1 advice | Current source, recipe and fixture agree: a small implementation is reasonable, still requiring the outcome check. |
| Missing tool | Authorized complete local fixture plus SQLite can replace an unavailable SQL MCP for that same bounded task | Required production rows have no authorized accessible source: hold that result and report the evidence/tool gap. |
| Harmful unnecessary delegation | Translate a supplied phrase directly despite idle slots; share no helper context | Several necessary independent inventories with ownership/budget may justify bounded delegation. |

Equivalent simpler actions that meet these outcome contracts are acceptable.
No prose length, phase recital, diagnosis phrase, plan existence, role-play or
tool-call count earns domain-quality credit. The checker does not search model
answers for these words. Actual skill fitness, proper tool use, source support,
ownership and useful worker counts require independent outcome evidence.

## Supported projections and limits

The executable [`replay_selection_cases.py`](replay_selection_cases.py) reuses
the original fixture/replay and reads the current source modules. It checks:

- `method_control.decide`: method enums, diagnosis checks and advisory invariants
  for the explicitly supplied state. The helper does not infer semantic gaps
  from task text. Research or missing-tool tasks can still project to `DIRECT`.
- `routing.next_decision`: explicit task-profile tier selection, fail-to-next-tier
  advice, stop on current pass, stale context and missing model-pair holds. Route
  tests use invented model names and a disposable home/cache. Enabled progression
  is a **fixture**, never an account/native configuration change or a model call.
  Disabled cases use the actual public template with no override. `DISPATCH` in
  the receipt is a returned advisory enum, not an executed worker.
- SQLite's visible in-memory fixture: revenue 150 versus invalid join fanout 250,
  and item count 3. This checks bounded SQL arithmetic, not a native agent's tool
  selection, a production query or MCP behavior.

[`routing.py`](../../../src/agent_harness/routing.py) chooses task minimums from
typed caller facts, not demonstrated model capability. The
[public template](../../../content/routing.toml) disables progression.
[`method_control.py`](../../../src/agent_harness/method_control.py) returns
advice and hash bindings; it does not authenticate a grader. The separate
workgraph `route_for` in `workgraph/plan.py` uses declared minimum and recorded
gate evidence; its worker dispatch path is not exercised here. These contracts
must not be conflated into automatic resource/skill/MCP orchestration.

Each variant's unsupported checks emit explicit `NOT_RUN` with a reason. Recipe
semantic freshness is not proved by the separate stale-route-context test;
missing MCP handling is not proved by the separate missing-model-pair test.
No assertion equates either pair. Domain/native acceptance remains `NOT_RUN`
even if every supported local projection passes.

## Commands for main's verification

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 docs/v2/methodology/replay_selection_cases.py --controls
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 docs/v2/methodology/replay_selection_cases.py --require-outcomes
PYTHONDONTWRITEBYTECODE=1 python3 -m ruff check docs/v2/methodology/replay_selection_cases.py
```

The first command exits 0 only for nonempty valid supported projections; it
emits `SUPPORTED_PROJECTIONS_PASS`, 16 per-variant records and explicit unsupported
checks. Its three controls must reject a false PLAN for direct work, a false
quick-tier expectation for a high-uncertainty profile, and 250 as order revenue.
The second must exit **2**, retaining `overall_domain_acceptance: NOT_RUN`.
That is an expected non-qualification result, never an end-to-end PASS or a
reason to loosen an original gate. Missing/malformed packs, wrong projected
expectations or source drift during replay fail rather than count as success.

Authority is **INFORMS**, with the integration owner as reader. Subject is the
named visible pack and current method/routing/SQL projections; exact pack and
source hashes are emitted. These checks settle neither semantic skill fitness,
MCP availability/permission, useful worker count, native adoption, model quality,
held-out transfer nor whole-campaign token benefit. Broader acceptance still
uses [the unchanged-baseline/held-out/total-token contract](evaluation.md).

## Existing checks inspected, not re-run by this worker

`existing:` prior methodology cases/replay; current work-loop/task-brief guidance;
production-code/standards/session-memory skills; `bin/harness`; method/routing,
launch and workgraph route sources; MCP skill listing/readback source; tests below.
No new skill, plugin, framework, runtime selector or global instruction was added.

| Supported boundary | Existing source check available to main |
|---|---|
| Task-derived tier minimum, unknown task and underqualified/ceiling hold | `tests/test_route_progression.py::test_task_selector_starts_at_a_tier_supported_by_the_task_evidence`, `::test_task_selector_refuses_unknown_or_underqualified_task` |
| Task/profile binding, failed gate, current pass | `tests/test_route_progression.py::test_task_profile_is_bound_to_route_history_and_gate_result` |
| Public progression disabled; missing/unsupported pairs do not silently fall back | `tests/test_route_progression.py::test_public_template_does_not_activate_strict_progression`, `::test_unavailable_or_unsupported_pair_never_falls_back` |
| Budget, unknown outcomes and provenance holds | `tests/test_route_progression.py::test_stale_unknown_and_exhausted_budget_hold_before_dispatch`, `::test_route_version_and_gate_provenance_are_required` |
| Refused/non-run gates do not become escalation success | `tests/test_workgraph_routing.py::test_guard_refusal_or_not_run_never_escalates_as_gate_failure`, `::test_a_non_run_route_never_spawns_a_worker` |
| Method directness, failure-specific diagnosis, stale request/artifact rejection | Existing `tests/test_method_control.py` checks named in the prior case pack |
| Semantic skill/MCP fit, capacity/privacy-safe beneficial delegation, source currency and causal adequacy | **Unsupported by this replay: NOT_RUN.** Main needs outcome-specific checks/native evidence; the cases are an explicit contract, not proof. |

No model campaign, source-wide test suite, original parent gate, install,
deployment or promotion was run by this worker for round two. Any small local
checker-development observations in the handoff remain subordinate to main's
independent verification of the exact integrated revision.
