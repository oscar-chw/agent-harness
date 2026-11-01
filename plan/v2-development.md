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
- [x] 2. Qualify integrated dev package with existing release checks in its clean publication snapshot | needs: 1,4 | ctx: docs/v2-development.md | gate: cd .harness-work/v2-development/scratch/candidate && bash scripts/check.sh
      2026-11-01T19:09:04Z exit 0 in 439s [060a1adb] — DEMO: PASS / CHECK: PASS / agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.
      2026-11-01T19:17:27Z The permission-profile and workspace privacy fixes postdate 490a5ec; retain its gate as historical evidence and requalify the final candidate.
      2026-11-01T19:25:15Z exit 1 in 419s [61d0af9b] — FAILED tests/test_permission_profiles.py::test_invalid_saved_posture_is_reported_without_partial_install / FAILED tests/test_permission_profiles.py::test_explicit_native_posture_and_uninstall_restore_original_settings / 4 failed, 1510 passed, 2 skipped, 2 xfailed in 418.79s (0:06:58)
      2026-11-01T19:34:15Z exit 0 in 425s [9db8f7d1] — DEMO: PASS / CHECK: PASS / agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.
- [x] 3. Publish reviewed development commit without changing stable main | needs: 2 | gate: git diff --quiet HEAD refs/remotes/origin/codex/v2-development-20261102
      2026-11-01T19:35:07Z exit 0 in 0s [da39a3ee] — (no output)
- [x] 4. Offer and retain a native permission posture without stacking owned blockers in autonomy mode | ctx: src/agent_harness/permission_profiles.py | gate: PYTHONPATH=src python3 -m pytest -q tests/test_permission_profiles.py tests/test_installer.py tests/test_routing_adapters.py tests/test_context_budget.py
      2026-11-01T19:17:32Z exit 0 in 5s [9b0e80d2] — ............................................                             [100%] / 44 passed in 4.96s
      2026-11-01T19:18:01Z exit 0 in 5s [f10840aa] — .............................................                            [100%] / 45 passed in 5.09s
      2026-11-01T19:26:48Z exit 0 in 7s [02c6f8a7] — ..............................................                           [100%] / 46 passed in 7.29s

- [ ] 5. Retain Python 3.9 compatibility coverage on an available runner and verify published CI | needs: 3 | ctx: .github/workflows/ci.yml | gate: gh pr checks 4 --repo oscar-chw/agent-harness --watch --interval 10

Policy requirement: explicit review or native workspace autonomy is a deliberate installer choice, reused on update. No live settings are touched in this work. Other owners' restrictions remain. Unattended --yes alone cannot grant broader access. Preserve must retain current native values, including a manual edit after an earlier owned profile.

Check correction: the old per-tool consent fixture supplied only y/n; the new first-install permission question consumed y as an invalid posture. Its fixture now supplies preserve, then the same y/n. Codex refusal remains asserted. This aligns the check with the new requirement without removing negative coverage.

Negative evidence: the new preserve-after-autonomy case first failed with missing defaultMode; invalid saved posture first failed on a traceback. After repair the focused integration set passed 67 tests. Workspace index overwrite mutation was rejected while the unmodified implementation preserved the owner's edit.

Integrated check correction: the first final-candidate run retained 4 failed, 1510 passed, 2 skipped, 2 xfailed. New installer fixtures inherited another suite's temporary HARNESS_HOME, so their assertions read a different store. Pin both HOME and HARNESS_HOME to the fixture. No production behavior or assertion is relaxed. Add a caller-store sentinel control and rerun the original full gate.

Final qualification: clean single-branch snapshot 1184c6dc33b8627cd10b074559c8cfbccd8a192f passed bash scripts/check.sh (1515 passed, 2 skipped, 2 xfailed; secret scan PASS; disposable demo PASS; gate exit 0 in 425 seconds). Ruff and diff checks passed. A separate disposable install followed by the actual update command retained both generated native autonomy configurations and passive capture. These are package/configuration checks, not native client eligibility or deployment evidence. Later publication-receipt commits change this plan only.

CI repair: PR 4's first Python 3.9 job failed in setup-python, before any tests: the hosted ubuntu-latest image became 26.04 and has no 3.9 binary. The official actions/python-versions manifest lists 3.9.25 x64 for Ubuntu 22.04/24.04, and 3.12.16 for 22.04/24.04/26.04. Keep both original Python versions: pin only 3.9 to 24.04; retain 3.12 on latest. No test, scan or demo step is skipped or weakened. This later CI-only change supersedes the receipt-only description above; package source/tests still match 1184c6d. Primary evidence: https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json and the failed job at https://github.com/oscar-chw/agent-harness/actions/runs/41342513295.
