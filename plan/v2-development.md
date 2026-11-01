## goal: Research current agent methods, add bounded project artifact navigation, qualify and publish a v2 development candidate without claiming stable deployment

Done-condition: local checks pass on the candidate; a new development branch and PR expose the same commit. Stable release, native deployment, learning promotion and token-savings claims remain outside this dev publication.

existing: current storage caps, scoped handoffs, method-control DIRECT route, source-backed retrieval, daily discovery, native adapters; Microsoft and DeepSeek official-source sidecars; Instagram mind-map caption and visible diagram. Reuse those rather than adopting another agent runtime or a paid API.

Analysis: the request is a usable v2 DEVELOPMENT publication, with evidence-based prior-art decisions and less artifact clutter. Versioning does not establish v2 production readiness. Keep original user work and local private evidence. No live guard/config edits, scheduler activation, paid API or blind history cleanup.

Research: Microsoft LLMLingua is older compression research; Agent Framework has newer experimental compaction; DeepSeek has a new superagent prototype and alpha OAR work. Compare their actual capability/authority boundaries. The social mind map inventories components but supplies no quality benchmark. Record dated primary URLs in the public development note.

Plan: add an explicit standard-library workspace CLI, default read-only, one index plus scratch/outputs per material task; idempotent preparation, metadata-only bounded inventory, symlink/nonregular refusal, warnings without deletion. No new automatic tools in every prompt. Freeze tests first. Initial CLI regression: 11 failed / 7 passed because workspace is not registered (exit 2).

Owner authorization: current request explicitly authorizes v2 dev push. Publication targets a new branch/PR; no force-push, stable tag or automatic deployment. Exclude unrelated/private local drafts.

- [x] 1. Implement and qualify bounded task workspace navigation | ctx: src/agent_harness/workspace.py | gate: python3 -m pytest -q tests/test_workspace.py
      2026-11-01T18:58:35Z exit 0 in 2s [d8795bd9] — ....................                                                     [100%] / 20 passed in 2.29s
      2026-11-01T19:04:24Z exit 0 in 3s [73c484e9] — .......................                                                  [100%] / 23 passed in 2.86s
- [ ] 2. Qualify integrated dev package with existing release checks in its clean publication snapshot | needs: 1,4 | ctx: docs/v2-development.md | gate: cd .harness-work/v2-development/scratch/candidate && bash scripts/check.sh
      2026-11-01T19:09:04Z exit 0 in 439s [060a1adb] — DEMO: PASS / CHECK: PASS / agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.
      2026-11-01T19:17:27Z The permission-profile and workspace privacy fixes postdate 490a5ec; retain its gate as historical evidence and requalify the final candidate.
- [ ] 3. Publish reviewed development commit without changing stable main | needs: 2 | gate: git diff --quiet HEAD refs/remotes/origin/codex/v2-development-20261102
- [x] 4. Offer and retain a native permission posture without stacking owned blockers in autonomy mode | ctx: src/agent_harness/permission_profiles.py | gate: PYTHONPATH=src python3 -m pytest -q tests/test_permission_profiles.py tests/test_installer.py tests/test_routing_adapters.py tests/test_context_budget.py
      2026-11-01T19:17:32Z exit 0 in 5s [9b0e80d2] — ............................................                             [100%] / 44 passed in 4.96s
      2026-11-01T19:18:01Z exit 0 in 5s [f10840aa] — .............................................                            [100%] / 45 passed in 5.09s

Policy requirement: explicit review or native workspace autonomy is a deliberate installer choice, reused on update. No live settings are touched in this work. Other owners' restrictions remain. Unattended --yes alone cannot grant broader access. Preserve must retain current native values, including a manual edit after an earlier owned profile.

Check correction: the old per-tool consent fixture supplied only y/n; the new first-install permission question consumed y as an invalid posture. Its fixture now supplies preserve, then the same y/n. Codex refusal remains asserted. This aligns the check with the new requirement without removing negative coverage.

Negative evidence: the new preserve-after-autonomy case first failed with missing defaultMode; invalid saved posture first failed on a traceback. After repair the focused integration set passed 67 tests. Workspace index overwrite mutation was rejected while the unmodified implementation preserved the owner's edit.
