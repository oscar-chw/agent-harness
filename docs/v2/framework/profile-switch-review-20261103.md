# Profile switch: bounded static proposal

3 November 2026. P1: copy_harness removes hh/profile before copying a different
source. Failure destroys the active profile; success discards accumulated
knowledge/local rules. Same-directory laptop use bypasses this branch; the kit
is unchanged.

Caller order: cmd_install previews context, calls copy_harness, rebuilds installed
context/plans, applies tool changes, then saves state. cmd_update calls
copy_harness before _reapply builds context, applies and saves. Publication
precedes later fallible context/config operations.

Minimal data-safe replacement:
1. Copy the requested profile to a unique sibling stage under hh BEFORE touching
   active data, including when the source is nested inside hh/profile. Load and
   validate it first. Copy failure leaves the old tree intact; clean only this
   invocation's unpublished stage.
2. Rename the entire old profile to unique backup/<timestamp>/modified/profile,
   matching modified-file retention. Preserve knowledge, hidden files and edits;
   never filter or overwrite the retained tree.
3. Rename the candidate into hh/profile. On publication failure restore the old
   tree. Never delete the only retained copy if recovery fails; report its path.
4. Retain/report that backup after success. Do not merge old rules into the new
   profile. Old knowledge stays recoverable; continued indexing is separate.

Later apply/save failure is not whole-install rollback. Preserve both profiles;
never claim tool configs rolled back. Root should cover copy/publish failure,
successful retention, nested source and same-source no-op.
No tests/runtime/source changes performed by this reviewer.
