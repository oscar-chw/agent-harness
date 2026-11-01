## goal: Define and qualify inspection-first shared handoffs and active evidence-backed memory writing

Done-condition: the shared-session protocol and handoff template ship to supported adapters, two fresh CLI processes can publish/inspect one project checkpoint, unrelated projects remain separate, missing evidence cannot become completion, and existing content/context/privacy checks pass. Live activation is limited to additive local guidance; no messaging, history harvesting, guard changes or inferred learning promotion.

## analysis

Ordinary cross-session coordination must be inspection-first. Active messages are for authorized activation or continuation of work. Sessions maintain small evidence-backed checkpoints during material work. A guide cannot guarantee compliance from every model or recover a crash before a write.

## research

existing: project plan records, content/templates/handoff.md, task checkpoint/status CLI, operational ledger with CAS/evidence freshness, scoped fact memory, state_save/load and session search. Reuse these stores. The optional MCP op_state tool is off by default; the documented shell fallback is harness task, not an invented command. Avoid parallel overwrites by using per-task/per-session handoff files; the graph remains completion authority.

## plan

Add a compact session-memory skill, expand the existing handoff template and point core memory rules to it within the existing context caps. Exercise shipped installation and two-process inspection, including isolation and missing-file controls. Add only a managed pointer to existing native instruction files, preserve their other content and keep backups. No performance claim or automatic promotion follows from structural tests.

Fitness disposition: owner-requested narrow local guidance canary, not an independently qualified performance improvement or all-device release. Unique delta is a shared artifact/inspection contract and explicit write triggers, rather than generic reasoning advice. The loaded guide is under 60 lines; discovery/rendered context caps pass. Positive mechanics and missing/cross-project controls are tested. Paired model trigger/compliance, latency and token benefit remain NOT_EVALUATED. Rollback retains the original native instruction bodies and installer backups; remove only the managed suffix/owned guide through a separately reviewed rollback. Requalify after client/model changes.

- [x] 1. Qualify shared protocol, existing checkpoint mechanics and context budgets | gate: python3 -m pytest -q tests/test_session_memory_protocol.py tests/test_workflow_templates.py tests/test_content.py tests/test_context_budget.py tests/test_operational_state.py
      2026-10-29T08:18:08Z exit 0 in 2s [e0b7d756] — .................s.......................                                [100%] / 40 passed, 1 skipped in 2.74s
- [x] 2. Verify full source gate | needs: 1 | gate: bash scripts/check.sh
      2026-10-29T08:25:23Z exit 0 in 404s [f1de81f1] — DEMO: PASS / CHECK: PASS / agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.
- [x] 3. Verify additive local guidance installation | needs: 2 | gate: python3.11 "${HARNESS_SESSION_MEMORY_VERIFY:?private readback required}"
      2026-10-29T08:25:42Z exit 0 in 0s [9f6ad75a] — PASS: shared skill/template, additive native pointers, original contracts and retained files / Native session reload and model compliance: NOT_EVALUATED; no messages sent

