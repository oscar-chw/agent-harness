# Current usable candidate

3 November 2026. **Local development candidate, not a qualified stable v2.**
For the two-minute explanation and diagram, read
[Interview quickstart](INTERVIEW-QUICKSTART-20261103.md).

Latest diagnostic increment: [KB runtime repair](kb-runtime-repair-20261103.md).
Its exact wheel is under `output/interview-candidate-20261103/revision2/`.
The checks below describe the retained predecessor; the revision2 manifest names
the post-change checks. An installed disk overlay is not a connected-client reload.

## What passed

| Check | Observed result |
|---|---|
| Full regression, supported offline build backend | 1,944 passed; 2 skipped; 2 expected failures; 4 marker warnings |
| Actual candidate wheel | Exact runtime/content bytes; isolated console script; generated MCP server; persistent memory across fresh processes; clean miss; graph init/list/versions |
| Copilot portable MCP repair | 3 failing cases before; 60 affected tests passed; 4 staged tests passed; one adapter installed with backup and matching source/install hash |
| Native source-reader demonstration | Fresh Codex reader recovered an approval prerequisite omitted by a pending note; original full case remains PARTIAL |
| Privacy | Clean wheel-input tree scan passed; this is not full private-vault publication approval |
| Lint and whitespace | Changed adapter/tests/audit pass Ruff; git diff whitespace check passed |

Full regression command:

```sh
PYTHONDONTWRITEBYTECODE=1 HARNESS_STAGING_PYTHON=/opt/homebrew/bin/python3.11 \
  PYTHONPATH=src python3 -m pytest -q tests eval
```

Evidence: `.harness-work/retrieval/source-reader/full-suite-r2.{log,xml}`;
`output/interview-candidate-20261103/wheel-smoke-r3.json`;
`output/interview-candidate-20261103/source-privacy.json`.

## Corrections retained in the record

The initial raw test command used Apple's old setuptools despite the declared
build requirement. The existing check script already selects a supported
interpreter. Unchanged staging tests passed with that interpreter; no packaging
source fix was needed.

Two skip audits also rejected legitimate, checked host limitations. Their fix
recognises actual FTS5/access predicates rather than merely allowing a reason
string. Unconditional skips still fail. The first permissive draft's four failed
negative controls are retained; the final affected run passed all 27 checks.

The separate wheel-smoke invocation initially put its prefix inside the checkout,
then encountered macOS's `/var` versus `/private/var` alias. The isolation checks
correctly failed. Reusing the external prefix with resolved paths passed the
same isolation conditions and original runtime checks. All failed records remain.

## What is not established

- Stable-v2 acceptance: graph node 4 remains pending/STUCK on its original gate;
  four original cases are partial. No gate or score was relaxed.
- Matched whole-workflow quality and aggregate token nonregression remain UNKNOWN.
  The one native source-reader call used 124,702 input-plus-output tokens;
  cached/reasoning counts are subsets, not extra savings.
- Live authenticated Copilot loading and all-device parity are NOT_RUN.
- The new profile capability note is reachable through a fresh explicitly scoped
  KB, but absent from this live MCP index. Cause and live reload remain unresolved.
- Dot installation message is NOT_SENT: direct app control was refused. No bypass,
  native permission change or substitute endpoint was attempted.
- The bundled knowledge snapshot contains 96 canonical project documents. It is
  not every local KB source, private history, database or a synchronised vault.

## Package and follow-up

Private candidate: `output/interview-candidate-20261103/manifest.json`.
Wheel SHA-256: `b9366bd7911aad88f3635de7cad5cc3bf5addd3a719f6d4265da58d9616266c4`.
The checked installation/sync instructions are in
`handoffs/v2-completion/DOT-INSTALL-HANDOFF-20261103.md`.
No commit, push, whole-install replacement or remote deployment was made in this increment.
