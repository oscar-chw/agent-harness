# Node 6 — CONTROLS + verdict: both-directions controls in check_rea_v0.py (unlawful/absent license fails; inference-as-observed fails; unbound source fails; hash mismatch fails; empty unknowns fails; intact passes) and docs/v3/rea-support-v0-verdict-20261111.md with the v1 delta

plan: v3-rea-support
gate: `/usr/bin/python3 .harness-work/v3-rea-support/check_rea_v0.py`
ctx: (none)

## Attempt 2026-11-11T00:53:46Z — agent@redacted-host — 0s — exit 0

```
REA v0 controls — 8 checks, 0 bad
  OK    real record: valid + bindings verified (rea-lever-20261105, 6 claims, decision pattern-only)
  OK    C1 license absent: refused (invalid license spdx)
  OK    C2 source unpinned: refused (unpinned source version (a commit/tag digest is required; 'latest' is not analyzable))
  OK    C3 inference as observed: refused (observed claim c6 cites no bound evidence (inference presented as observed))
  OK    C4 bound evidence mutated: refused (binding docs/v2/references/lever-20261105.md hash mismatch for /private/var/folders/3z/qg67zkkn0m5325qx65hvgh580000gn/T/tmps_mwucpb/docs/v2/references/lever-20261105.md (bound evidence changed))
  OK    C5 unknowns emptied: refused (invalid unknowns list)
  OK    C6 pin/binding inconsistent: refused (upstream-pin digest must equal the version pin)
  OK    intact record still passes after all mutations
VERDICT: PASS (record valid; all 6 refusal controls refused for the named reason; intact passes)
```
