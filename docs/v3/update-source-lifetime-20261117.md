# Update source lifetime

A real disposable v3.0.0 → v3.0.1 upgrade passed its doctor check, then its next
ordinary update failed. The old updater had deleted the temporary source directory
recorded in installation metadata. The original failed receipt is retained.

## Recovery

When an implicit saved source disappears, `harness update` reuses its installed
package and content. It records that surviving location for the next update.
An explicit `--source` keeps its requested meaning and fails if missing. Existing
checkout sources continue supplying updates. Installed-layout copies select the
package alongside their content, including when invoked from another checkout.

The repair uses existing installed bytes and keeps the storage limits. Ordinary
update reapplies the retained release. `self-update` still discovers and qualifies
newer releases independently.

## Checks

- The new regression failed on the missing source before the repair.
- A second failing regression caught copying the caller checkout package over an
  installed-layout source. Two controlled reversions reproduce both failures.
- Four behavioral tests cover repeated recovery, explicit invalid sources,
  incomplete retained payloads and package selection across checkouts.
- A disposable older updater exercises the candidate archive, followed by an
  ordinary update and byte checks of memory, research preferences, vault and state.
  Its candidate transport is frozen locally. Public release readback is separate.

The complete integrated source passed 3,227 tests, with one skip and two expected
failures. Ruff and the generated capability catalogue passed.

This qualification covers update mechanics. Learning efficacy, aggregate token
savings and remote-device installation retain their own acceptance evidence.
