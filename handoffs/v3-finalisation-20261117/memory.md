# Automatic State checkpoint pickup

2026-11-17. Isolated branch codex/v3-memory-fixes-20261117, base 8bad4bdc16d35a5cffbcf8e8f7d13776f1b8a381. Scope is blocker 1. Root owns root binding, tombstone wiring, independent verification and native compaction qualification.

## Implementation

Successful project-local `state_save` publication validates the actual saved State path and current bounded bytes. A packet with exactly one nonempty `## Goal` and `## Next` section, each within the existing board field limit, supplies the actual goal and next action. The complete redacted State packet is retained as an immutable project-local `.harness/checkpoints/<sha256>.md` snapshot through the existing atomic publisher. Its board row binds the packet through existing checkpoint and evidence-digest validation. Identity derives from the canonical saved State location and survives reconnection. Identical writes create no board churn. A newer structured State updates the same identity and preserves old snapshot bytes. A newer unstructured State replaces actionable metadata with the legacy diagnostic preview.

Session notes retain their existing previews. Incomplete, duplicate-section and oversized task fields remain diagnostic. No completion claim is inferred from the `Done` section. Existing project scope checks and lease/admission behavior remain in force. Foreign State paths, redirected storage, changed source bytes and missing/tampered packet controls refuse actionable pickup.

Owned source changes are `src/agent_harness/shared_board.py`, the checkpoint-publication call in `src/agent_harness/mcp/server.py`, and `tests/test_board_automatic.py`. Local plan and gate evidence are `plan/v3-memory-checkpoint-20261117.md` and its node record. No changes in the research-reasoning worktree, runtime configuration, installations or guard policy. No native/model calls or publication.

## Checks

- RED first, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_board_automatic.py::test_saved_state_packet_is_resolvable_by_a_cold_reader_after_reconnection` exited 1 on missing checkpoint_status. The final test verifies a resolvable packet, stable identity, changed current next action, retained old bytes and open status.
- RED tampered-packet control exited 1 when the first implementation omitted an evidence binding. Existing OperationalState evidence-digest validation now refuses changed bytes. RED unstructured-replacement control also exited 1 before diagnostic updates were attached to the same stable State identity. No existing assertion was relaxed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_board_automatic.py` exited 0, 46 passed, including a separate-process reader and foreign/invalid/redirected/missing controls.
- `plan gate --owner agent@redacted-host/s77484 v3-memory-checkpoint-20261117 1` exited 0, 132 passed in 5.74s. The graph records the exact eight-file affected pytest command and complete output. An initial gate invocation without explicit owner stopped at the lease check before running tests. This owner is the lease created by this implementation session.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_operational_state.py tests/test_operational_process_flow.py tests/test_handoff_navigation.py tests/test_interview_demo.py tests/test_memory_transport.py tests/test_kb_runtime_metadata.py` exited 0, 66 passed in 18.18s.
- `/usr/bin/python3 -m ruff check --config ruff.toml src/agent_harness/shared_board.py src/agent_harness/mcp/server.py tests/test_board_automatic.py` exited 0, all checks passed. Bare ruff and Homebrew-module attempts were unavailable. The repo-declared system interpreter supplied the existing linter without installation.
- Temporary copied-source mutations omitted the task fields and the evidence binding separately. Each relevant pytest command exited 1 with AssertionError. Worktree source remained intact. `git diff --check` exited 0.

## Remaining boundaries

Only structured State packets earn actionable automatic pickup. Session notes and arbitrary prose retain diagnostic previews. Snapshot publication and CAS board updates reuse the existing State writer and board mechanisms. No universal model adherence, native compaction outcome, efficacy, installed behavior or all-device result is claimed from these local checks. Root independently verifies and integrates this isolated commit.
