# Offline correction staging — source-to-installed receipt

25 October 2026. **Scope: synthetic local consumer fixture only.** This is not
native model learning, an installed Claude/Codex registration, production
deployment or independent promotion.

| Boundary | Command or observation | Result |
| --- | --- | --- |
| Source | Clean candidate commit `72dd62f50593fd07bde833e028d6665a821366de`; `git archive HEAD` into a task-owned temporary source directory | `procedures.py` SHA-256 `d552522c64e70d604e29ade2d9aa5bd007a73cf82077ef08055570f05a172efa` |
| Wheel | Existing Python 3.11 and setuptools 83.0.0; `pip wheel --no-index --no-deps --no-build-isolation` from that archive | `agent_harness-0.9.0.dev0-py3-none-any.whl`, SHA-256 `d77e9dcb7311df5d3561ec5214c9f8f99e51779ce17d0aca9cb3ebf5dcd09ba3`; exit 0 |
| Install | Task-owned virtual environment; `pip install --no-index --no-deps` from the local wheel | Exit 0; metadata version `0.9.0.dev0` |
| Load | Virtual-environment Python imported `agent_harness.procedures` from its own `site-packages`; installed file compared with archived source | Installed SHA-256 exactly `d552522c64e70d604e29ade2d9aa5bd007a73cf82077ef08055570f05a172efa`; CLI `harness --help` exited 0 |
| Stdio MCP | Fresh environment with only task-owned `HOME`/`HARNESS_HOME`; JSON-RPC `initialize`, `tools/list`, then `tools/call skill_manage` `action=correct` | Process exit 0, server name `harness`, action present in tool schema, correction response `isError=false` |
| Synthetic before/after | A **test-only** active row and event were inserted directly into the temporary SQLite store; the installed CLI prompt hook recalled it before correction. MCP correction linked one old/new pair, retained old evidence, changed old to `rolled_back`, left new `proposed` | Four concurrent fresh CLI processes emitted no old or replacement method. The previously served session received a withdrawal notice without the old steps. New MCP `view` showed the link and both statuses; `list` omitted the proposed replacement. No learned `SKILL.md` was created |
| Retry conflict | Installed CLI `harness improve --correct-procedure OLD_ID --draft-procedure FILE --project PATH` after the MCP correction | Identical retry exit 0, same proposal; changed candidate retry exit 1 with conflict; new status stayed `proposed` |

The direct SQLite active-row setup exercises **consumer withdrawal** only. It
does not prove an actual method passed a native grader, that a client loaded this
wheel as its registered MCP server, or that a model used the correction. No live
adapter install, hook registration, credential read, model call or network
dependency install was made. Installed v0.9 was left untouched.

The task-owned temporary source, wheel, virtual environment, project and
`HOME`/`HARNESS_HOME` were removed after checking the private receipt's source
commit, version and fresh-read result. The cleanup command exited 0 and a
follow-up existence check passed. No live registration was attempted, so
there was no live registration to restore. The command's
existing `harness improve` top-level help still describes applying proposals
as if an eval gain were sufficient; promotion remains on HOLD and that help
copy needs a separate correction.
