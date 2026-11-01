# Node 2 — Verify installed package and retained local state

plan: studio-package-refresh
gate: `python3.11 "${HARNESS_STUDIO_DEPLOY_VERIFY:?private verification script required}"`
ctx: (none)

## Attempt 2026-10-29T07:40:49Z — oscarmoon@oscarmoondeMac-Studio — 0s — exit 0

```
{
  "package": "MATCHED_ALL_FILES",
  "files": 66,
  "preservation": "UNCHANGED_FILE_METADATA",
  "fresh_cli": "PASS",
  "fresh_mcp": {
    "tool_count": 15
  },
  "native_existing_sessions": "NOT_OBSERVABLE",
  "version": "0.9.1.dev0",
  "release": false,
  "EMMA_activation": false
}
```
