## goal: Research current agent methods, add bounded project artifact navigation, qualify and publish a v2 development candidate without claiming stable deployment

Done-condition: local checks pass on the candidate; a new development branch and PR expose the same commit. Stable release, native deployment, learning promotion and token-savings claims remain outside this dev publication.

existing: current storage caps, scoped handoffs, method-control DIRECT route, source-backed retrieval, daily discovery, native adapters; Microsoft and DeepSeek official-source sidecars; Instagram mind-map caption and visible diagram. Reuse those rather than adopting another agent runtime or a paid API.

Analysis: the request is a usable v2 DEVELOPMENT publication, with evidence-based prior-art decisions and less artifact clutter. Versioning does not establish v2 production readiness. Keep original user work and local private evidence. No live guard/config edits, scheduler activation, paid API or blind history cleanup.

Research: Microsoft LLMLingua is older compression research; Agent Framework has newer experimental compaction; DeepSeek has a new superagent prototype and alpha OAR work. Compare their actual capability/authority boundaries. The social mind map inventories components but supplies no quality benchmark. Record dated primary URLs in the public development note.

Plan: add an explicit standard-library workspace CLI, default read-only, one index plus scratch/outputs per material task; idempotent preparation, metadata-only bounded inventory, symlink/nonregular refusal, warnings without deletion. No new automatic tools in every prompt. Freeze tests first. Initial CLI regression: 11 failed / 7 passed because workspace is not registered (exit 2).

Owner authorization: current request explicitly authorizes v2 dev push. Publication targets a new branch/PR; no force-push, stable tag or automatic deployment. Exclude unrelated/private local drafts.

- [x] 1. Implement and qualify bounded task workspace navigation | ctx: src/agent_harness/workspace.py | gate: python3 -m pytest -q tests/test_workspace.py
      2026-11-01T18:58:35Z exit 0 in 2s [d8795bd9] — ....................                                                     [100%] / 20 passed in 2.29s
- [ ] 2. Qualify integrated dev package with existing release checks in its clean publication snapshot | needs: 1 | ctx: docs/v2-development.md | gate: cd .harness-work/v2-development/scratch/candidate && bash scripts/check.sh
- [ ] 3. Publish reviewed development commit without changing stable main | needs: 2 | gate: git diff --quiet HEAD refs/remotes/origin/codex/v2-development-20261102
