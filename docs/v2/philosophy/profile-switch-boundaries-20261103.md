# Profile switching boundaries

3 November 2026. Static input; migration/recovery NOT_RUN.

Observed: installer.py:702–707 preserves profile data on uninstall, but
copy_harness:802–804 removes a different active profile before copying its
replacement. Archive-old/not-merge is a proposed repair, not current proof.

Archiving preserves user additions and an audit trail. Merging risks mixing machine facts, stale guidance and access scopes. Preserved bytes must not automatically become indexed knowledge,
current advice or permission. Sharing needs scoped selection, provenance and currentness; archives grant
no authority.

UNKNOWN pending qualification:
- Recovery: complete archive identity, interrupted-copy behavior, restoration
  and active-profile rollback; an archive path alone proves none.
- Symlinks: profile copying uses copytree, while _copy_any:496–501 explicitly
  preserves links. Do not assume identical link/target semantics or containment.
- Concurrent installs: serialization and conflict-safe archive publication are
  not established by the inspected switch seam.
- Public migration: no release, existing-install conversion or all-client reload
  is established. storage.py:37–55,102–105 protects referenced backups/stashes;
  profile-archive retention/discovery remain unqualified.

Paths above are under src/agent_harness. No merge, migration or tests performed.
