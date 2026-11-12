# Full-stack delivery and interview practice

Use this branch for building, debugging or explaining a web application, API,
database-backed feature, AI application or its deployment. A definition, rewrite
or tiny isolated edit needs no lifecycle ceremony. Reuse the existing work graph
only where dependencies, ownership or recovery justify it.

## One understandable working slice

1. Clarify only consequential unknowns: user outcome, supplied stack/environment,
   data/permission boundaries and a check that distinguishes success from failure.
   Inspect the project before asking what is already on disk.
2. Trace one concrete request: input/UI → handler/API → validation and permission
   check → business rule → database/state change → response/UI. Explain each
   component's purpose before unfamiliar terminology. Label a proposed route as
   proposed; a backend test is not proof of a browser flow.
3. Reuse the existing stack and smallest vertical slice. Name the files that own
   the rule and its test. Avoid new frameworks, services or parallel workers unless
   the task needs them. Use primary docs for a consequential version uncertainty.
4. Implement small reviewable changes. Test the normal request plus relevant
   invalid input, unauthorized access, missing data, duplicate/retry and partial
   failure. Debug from observed evidence and return to analysis or the plan when
   its premise is wrong; do not repeat unchanged attempts.
5. Verify the actual outcome at its boundary: function/database/API/browser as
   applicable. For deployment also check configuration, migrations, monitoring,
   data preservation and rollback within authorized scope. Tests do not grant
   permission to deploy or weaken a native control.
6. Report what changed, the command/results and material limits. Leave one concise
   evidence-linked checkpoint for unfinished or cross-session work. No collection
   of untracked speculative artifacts or manufactured completion percentages.

## Explain enough to own the code

In interview/learning work, show one concrete input and result before code.
For each meaningful change explain purpose, inputs/outputs, where state changes,
an unfamiliar construct, and the simplest alternative/tradeoff. Keep generated
code small enough for the user to read, modify and defend. Ask them to predict or
explain one small change without AI when rehearsing; do not invent their expertise.

The employer's actual tool/data rules apply. User-reported AI permission is
specific to that exercise; it is not authority to upload unrelated private data.
Use hints before a whole solution when the user wants practice. Ordinary dev-ops
needs concise rationale, not a teaching monologue at every edit.

## Retrieve only relevant knowledge

`kb_get("SWE.md")` lists the common SWE/full-stack chapters; `SWE-SOURCES.md`
gives source-backed learning routes; `ENGINEERING-FOUNDATIONS.md` covers algorithms,
operating systems, review, accessibility and CI. `AI-ENGINEERING.md` covers model contracts,
RAG, tools, orchestration, memory, evaluation and AI operations when relevant.
Fetch selected sections rather than all pages. If an old MCP connection cannot
discover a newly installed page, say so; use the canonical local vault file or a
fresh supported MCP connection, without restarting other sessions automatically.
Missing/stale evidence remains UNKNOWN. Knowledge retrieval is not a guarantee
that an agent learned or that a generated recommendation is correct.
