## goal: Qualify and install the current development package on Studio while preserving native settings, guards, memory and extra adapter content

Done-condition: full source gate and private installation readback pass. Installed Python package matches source; fresh CLI/MCP answer; native settings, guards, profile, extra Copilot content and memory are untouched. Existing sessions are not claimed reloaded.

## analysis

The owner authorizes installation on this Mac. The ordinary updater re-renders native governance and removes installed-only Copilot content. Refresh only the program package, retaining configuration and data. This is a development installation (declared 0.9.1.dev0), not a v1 release or an EMMA learning qualification.

## research

existing: installer.copy_harness, cmd_update/_reapply, runtime_inventory, full source gate and installed launcher. Source guard.py matches installed bytes; installed discovery.toml is absent. Preserve extra content. No FYP guard maintenance, model calls, history purge or permission changes.

## plan

Qualify source. Stage and hash-check a package copy, retain the previous package for rollback, and switch only the Python package. Add discovery.toml only if absent. Verify full manifests, fresh CLI/MCP and retained local hashes. Report disk-budget failures without pruning or cap inflation. Keep receipts and rollback instructions outside the public repository. EMMA remains a design candidate requiring held-out evaluation, not an activated feature.

- [x] 1. Qualify current source | gate: bash scripts/check.sh
      2026-10-29T07:39:35Z exit 0 in 378s [7d6fef46] — DEMO: PASS / CHECK: PASS / agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.
- [x] 2. Verify installed package and retained local state | needs: 1 | gate: python3.11 "${HARNESS_STUDIO_DEPLOY_VERIFY:?private verification script required}"
      2026-10-29T07:40:49Z exit 0 in 0s [280d0ca0] — "release": false, / "EMMA_activation": false / }

