# Laptop bundle entry: bounded static review

3 November 2026. Two concrete P2 findings; no tests/models/native calls or source,
package, approval or knowledge changes performed by this reviewer.

P2 home/store consistency: install-laptop-bundle.py:66-75 passes no normalized
store when --home is absent. With literal HARNESS_HOME="~/custom-store", the
packaged runtime/install.py expands/resolves it, but knowledge/add-knowledge.py:
21-22 uses Path(environment) unchanged. Knowledge is then written beneath a
literal ./~/custom-store rather than the runtime's store, and the entry reports
success. Normalize the selected store once and pass identical explicit context
to both phases, respecting --home precedence. Existing tests always use --home
and clear HARNESS_HOME; they miss this environment-only path.

P2 partial failure reporting: subprocess.run at line75 can raise OSError starting
the knowledge child after runtime completed. Only the outer generic "Bundle
refused" handler runs, losing completed-phase/no-rollback information. Catch
launch failures at the phase boundary and retain actual prior completion plus
unknown/not-started child state. Current tests cover nonzero child exits only.

Inspected BUNDLE/layout contains both ordered entry points and their assets;
outer validation precedes either child. This review does not establish all
artifact hashes or malformed-child-manifest behavior through execution. Root's
disposable upgrade/repeat/readback/uninstall results remain root-owned evidence;
actual laptop/Windows behavior and full-suite results are not established here.
