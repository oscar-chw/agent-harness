# Where work, facts, and knowledge belong

The harness has one local entry point (`HARNESS_HOME`, normally `~/.agent-harness`),
not one giant memory file. A client must use the right store for the claim it is
making. A search result is context, not permission or proof of completion.

| What to retain | Canonical source | Read/write interface |
| --- | --- | --- |
| User preference or short durable fact | `memory/user/<id>.json` | `mem_add` with `scope=user`; `mem_search` |
| Fact limited to the current project | `memory/project/<id>.json`, bound to the resolved project root | `mem_add` with `scope=project`; `mem_search` from that project |
| A verified mistake and its repair | `lessons/<id>.json` | `lesson_add`; `lesson_search` |
| Unfinished chat work | `state/<project-key>/STATE.md` (4 KB, ten older versions retained) | `state_save`; `state_load` |
| Multi-step deliverable and its completion evidence | `plan/<slug>.md` in the project repository | `plan context`, `plan claim`, `plan gate`; only a passing gate completes a node |
| Documentation and native Claude memory | Original documents, including configured `kb_paths` and the current project's docs | `kb_toc`, `kb_get`, then `kb_search`; `index.sqlite` is a derived search index |
| Source-bound project assertions (v1 candidate, opt-in) | `.harness/sources/` and `.harness/records/` inside that project | `ProjectMemory` receipts, revisions and explicit source scopes |
| Task leases and event cursors (v1 candidate, opt-in) | `operational/<full-project-digest>.sqlite` | `harness task` / `harness op`; `op_state` only when enabled |

The first six rows describe the current installed-style interfaces. The final
two are candidate facilities: their presence in the package does not mean a
client advertises them or that they have passed native-client qualification.
Project records do not become user-wide memories. A correction must retain its
prior evidence and withdraw stale advice; a proposed replacement is not
automatically promoted to a skill. Do not copy unrelated private transcripts
into a project to make search appear complete.

Claude Code, Codex and supported editors can point at the same local MCP server
and read the same local files **on one machine**. New sessions read the installed
rules and tool definitions. An already-open session may retain an older tool
schema until it reconnects; installing files does not rewrite that session's
context. Cross-device synchronization and full native-history migration are
separate operations requiring their own scope and verification.

The index is rebuildable; the JSON facts, project source receipts, state files,
and git-tracked plans are not disposable cache. `harness doctor` reports storage
health separately from successful MCP registration. If it reports an oversized
index, identify live sources, cached out-of-scope entries, session-search data,
and free pages before considering a bounded rebuild. Never delete source
history or raise the cap just to make the check green.
