# Central pickup and memory acceptance review

2026-11-17. Read-only implementation audit in research-reasoning-20261117. Only this handoff authored. Root owns gates and the native compaction trial. Existing mechanisms checked include SharedBoard, OperationalState, lifecycle hooks, source-bound ProjectMemory, research registry, KB and H6b admission controls.

## Latest install reconciled

Node 6 records `python3 .harness-work/check-central-integration.py` exit 0, covering installed hashes/backups, five capability checks and fresh-process KB retrieval. The orchestrator records already-connected MCP research-section readback. The local overlay retains the 3.0.0rc2 label. Earlier statements that research integration is source-only are superseded for this Mac's bounded overlay. No all-device or release qualification follows. Research discovery, late publication and profile-alias repair already have tests in `tests/test_research_capabilities.py`. Rebuilding those mechanics would duplicate existing work.

Independent current readback found installed/source bytes identical for `mcp/server.py`, `shared_board.py`, `operational_state.py` and `mcp/memory.py`. The gaps below therefore concern installed code paths too. Runtime deployment of the research registry supplies no native quality or learning-efficacy result.

## Top three fixable blockers

### 1. Automatic checkpoints lack a resolvable task packet

- Requirement -> automatic structured outcomes support cold pickup without the user composing a handoff. `docs/v1/architecture.md`, sections “Useful outcomes without user-authored handoffs” and “Cross-session progress without conversation relays”.
- Implementation -> `shared_board.py:48–65` publishes a preview, text digest and generic next instruction under a connection-generated identity. It carries neither goal nor checkpoint path. `mcp/server.py:225–237` passes summary text only. Automatic rows become `idle_unprepared`. Explicit `harness task checkpoint` already handles actionable packets.
- Existing gate -> `PYTHONPATH=src python3 -m pytest -q tests/test_board_automatic.py::test_existing_checkpoint_entrypoints_publish_for_a_cold_session tests/test_operational_idle_recovery.py::test_unprepared_legacy_task_is_not_described_as_actionable tests/test_session_memory_protocol.py`.
- Evidence / next action -> temporary probe reproduced an automatic row without `goal` or `checkpoint`. Current automatic test checks preview delivery only. Bind the existing persisted packet location and stable task identity at publication, then add a cold-reader assertion that resolves the packet and recovers its next permitted action. Preserve legacy diagnostic rows and existing explicit-checkpoint validation.

### 2. Workspace-launched MCP cannot pick up a separately scoped project board

- Requirement -> an authorized cold reader discovers the target project's current task and evidence through the shared interface.
- Implementation -> `mcp/server.py:212` freezes launch cwd, board calls use that root, and `operational_state.dispatch` refuses a `project` field. `board_publish` silently declines publication when a successful saved state's project differs from launch scope. Scope isolation is intentional and covered. The missing seam is trusted adapter-to-project binding for a chat whose working project differs from the MCP launch directory.
- Existing gate -> `PYTHONPATH=src python3 -m pytest -q tests/test_operational_state.py::test_cli_and_mcp_use_the_same_host_project_without_model_supplied_scope tests/test_board_automatic.py::test_automatic_publication_uses_canonical_saved_project tests/test_board_hooks.py::test_payload_cwd_controls_scope_even_when_launcher_and_environment_disagree`.
- Evidence / next action -> temporary server launched in A missed an actionable task in B and rejected the project override, while direct B-root access recovered `idle_ready`. Existing tests establish same-root interoperability and exclusion. Root should qualify adapter launch/root binding with a workspace-A/project-B cold case. Keep arbitrary model-selected cross-project board access excluded. This gap applies when launcher and task roots differ. Correctly rooted clients already have pickup mechanics.

### 3. Tombstone backflow guard remains disconnected from normal memory admission

- Requirement -> previously unlearned content stays refused on ordinary memory/lesson admission within the supported lexical boundary.
- Implementation -> `Memory` and `ProjectMemory` accept an optional Guard. `mcp/server.py:267,303` constructs Memory without one. H6b verdict explicitly leaves production wiring out of scope. The new research overlay does not change those constructors or configure a ledger/escrow mapping.
- Existing gate -> `PYTHONPATH=src python3 -m pytest -q tests/test_memory_guard.py::test_mem_add_refused_with_receipt tests/test_memory_guard.py::test_lesson_add_refused tests/test_memory_guard.py::test_sync_quarantines_dropped_file tests/test_memory_guard.py::test_project_memory_append_blocked_and_clean tests/test_memory_guard.py::test_corrupt_ledger_refuses_everything tests/test_memory_guard.py::test_no_ledger_guard_inactive`.
- Evidence / next action -> temporary tombstoned corpus plus explicit ledger-aware Memory refused the exact text. Normal Server admission accepted it and its Memory guard was None. Establish the authoritative per-store ledger/escrow selection and wire the normal constructors, then test ordinary MCP admission, explicit-project admission, unrelated-content control, corrupt ledger and post-relearn admission. Explicit-injection unit success currently establishes the guard component's behavior.

## Probe results and bounds

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -` ran an inline model-free temporary-directory probe, exit 0. It reproduced all three gaps with the stated controls and printed four installed/source byte matches. Temporary data was removed by TemporaryDirectory. First attempt exited 1 after finding gap 1 because the probe compared macOS temporary-directory aliases without resolving them. Resolving the temporary root corrected that probe assumption before the successful rerun. No acceptance gate was edited or executed.

All gate commands above are exact root follow-up commands, NOT_RUN by this reviewer. Native compaction, observed model continuation, broad memory efficacy and all-device uptake remain unverified here. The earlier four-pair native memory receipt establishes 4/4 answers per arm and 10.68% packet-level token reduction on authored tasks. Its tool-free selected-packet protocol does not exercise automatic board discovery or these admission seams. No additional graph backend is needed to address these three mechanics.
