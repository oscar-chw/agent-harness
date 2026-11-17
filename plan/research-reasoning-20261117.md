## goal: Improve measured reasoning and integrate reusable capability research

User requests continued reasoning/decision improvement with no additional task token cost, research into successful human research and paper writing, automatic research for missing substantive capabilities, reuse of completed research, saved preferences and confirmation during upgrades, all integrated with the central harness knowledge system.

existing: inspected published reasoning guide and held native calibration, work-loop, skill-creator, shared session memory, SourceVault/ProjectMemory, KB source selection, native evaluation controller and current usage receipts. Source changes use this isolated worktree. Original acceptance rules and failed attempts remain available.

Assumption: a capability is a meaningful task family such as scientific paper writing or a database migration. Individual tool calls inherit its research record. Research status, source support, model quality and adoption have distinct evidence.

- [x] 1. Specify capability reuse, preference confirmation and central retrieval acceptance | gate: PYTHONPATH=src python3 -m pytest -q tests/test_research_capabilities.py
      2026-11-17T06:11:10Z exit 0 in 0s [93a827bb] — ................                                                         [100%] / 16 passed in 0.61s
      2026-11-17T06:17:39Z exit 0 in 1s [3260e88a] — ...................                                                      [100%] / 19 passed in 0.60s
- [x] 2. Research and distill human research practice, paper writing and reasoning | gate: python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" content/skills/research-paper
      2026-11-17T06:11:10Z exit 0 in 0s [039cdff0] — Skill is valid!
- [x] 3. Integrate source-bound capability research and preference checks | needs: 1,2 | gate: PYTHONPATH=src python3 -m pytest -q tests/test_research_capabilities.py tests/test_content.py tests/test_context_budget.py tests/test_kb_scope.py
      2026-11-17T06:11:12Z exit 0 in 1s [2989274f] — ...........................s......................                       [100%] / 49 passed, 1 skipped in 1.34s
      2026-11-17T06:17:41Z exit 0 in 1s [fbece68a] — ..............................s......................                    [100%] / 52 passed, 1 skipped in 1.33s
- [x] 4. Freeze and validate a compact reasoning comparison with complete usage | gate: PYTHONPATH=src python3 -m pytest -q tests/test_reasoning_iteration.py
      2026-11-17T06:18:01Z exit 0 in 19s [863714e8] — ................................................                         [100%] / 48 passed in 19.58s
- [x] 5. Execute bounded native iteration and require an earned improvement | needs: 4 | gate: python3 .harness-work/reasoning-eval/check-outcome.py .harness-work/reasoning-eval/compaction-run
      2026-11-17T06:29:31Z exit 1 in 0s [453b2fe8] — {"error": "frozen instrument, input or runtime changed", "promotion": "NOT_GRANTED", "status": "HOLD"}
      2026-11-17T06:35:10Z exit 1 in 0s [e7767bf4] — {"baseline_tokens": 149713, "candidate_tokens": 150194, "ceiling_policy": "Stop before the next call at the observed ceiling. An in-flight call can overshoot.", "consumed_calls": 12, "evidence": "NATIVE_RECEIPT_REPLAY", "holds": ["candidate_cost_increase", "no_strict_improvement"], "known_consumed_tokens": 299907, "orphan_receipts": [], "paired_quality_differences": [0, 0, 0, 0, 0, 0], "paired_tok
      2026-11-17T07:03:07Z exit 0 in 0s [35f2b81a] — {"baseline_tokens": 155643, "candidate_tokens": 150194, "ceiling_policy": "Stop before the next call at the observed ceiling. An in-flight call can overshoot.", "consumed_calls": 12, "evidence": "NATIVE_RECEIPT_REPLAY", "holds": [], "known_consumed_tokens": 305837, "orphan_receipts": [], "paired_quality_differences": [0, 0, 0, 0, 0, 0], "paired_token_differences": [-884, -870, -913, -901, -908, -9
- [x] 6. Verify central vault discovery and apply qualified guidance with backups | needs: 3 | gate: python3 .harness-work/check-central-integration.py
      2026-11-17T06:19:10Z exit 0 in 1s [aca4f2a1] — PASS installed source hashes, baseline backups, five source-bound capabilities and cold-process KB retrieval

## Native resource authority

The earlier1million-token/41-call tranche consumed984939known tokens/38calls. This task resumes work, with a fresh owner-approved ceiling of300000included-quota native tokens and12calls (17November2026). Local preparation and source research may proceed. The trial preserves failed calls, exact inputs, evaluator bindings and aggregate usage. Missing usage prevents acceptance. Resource authority is resolved for this bounded tranche. Failed attempts consume calls and known tokens; unknown usage stops acceptance and further launches until reconciled. No native Claude, paid usage, credential reads, guard weakening or shared-host change.

## Continued comparison authority and scope

Owner approved a separate350000token/12native-call tranche to test compaction of the existing selected long guide. The first unguided comparison remains rejected and is retained at source controller commit8bad4bd and eval/results/reasoning-iteration-20261117.json. The alternate comparison preserves exact grading, complete usage, all corresponding-case quality checks and nonincreasing aggregate tokens. Its claim is compression where the full guide would already be used, not superiority to unguided execution. Gate5 now checks that explicit alternate frozen comparison; all earlier failures remain in its node record.
