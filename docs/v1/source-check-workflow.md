# Optional source-grounded editing workflow

Use with the client's existing browser/search tools. This is a manual task workflow,
not a detector-evasion skill, an automated truth oracle, or a measured quality gain.
A source must be accessible **and** support the adjacent claim; these are separate checks.

1. List externally checkable claims in the draft, including numbers, dates, names,
   quotations and causal assertions. Preserve the author's meaning and uncertainty.
2. Open each cited primary source. Record URL, title, publisher/date when available,
   retrieval date and the relevant section/page. Search snippets alone do not verify it.
3. Compare the exact claim with the source's scope, population, date and qualifications.
   Label `SUPPORTED`, `CONTRADICTED`, `NOT_SUPPORTED`, or `UNVERIFIABLE`.
4. A 404, login wall, robots restriction or network error is `UNVERIFIABLE`; it does
   not prove that the work never existed. Seek an accessible primary copy or leave
   the claim explicitly unverified. Never invent authors, titles, DOIs or quotations.
5. Correct or remove unsupported assertions, preserve necessary uncertainty, and only
   then edit prose for clarity and the user's voice. Recheck citations after edits.
6. Return a compact claim ledger and the revised draft. Flag remaining source gaps.
   Do not infer correctness from a citation's existence, fluent wording or a model vote.

Suggested ledger: claim | source/locator | access result | support status | action.

## Live smoke check, 26 October 2026

Primary source opened successfully:
[Linux Foundation AAIF announcement, 22 October 2026](https://www.linuxfoundation.org/press/agentic-ai-foundation-announces-four-new-projects-agent-skills-open-responses-openenv-and-opensandbox).

| Probe | Access | Claim result | Action |
|---|---|---|---|
| The announcement identifies Alibaba as the OpenSandbox contributor. | Readable publisher page; summary and New Projects section | SUPPORTED | Retain with citation. |
| Alibaba contributed OpenEnv. | Same genuine page | CONTRADICTED: it attributes OpenEnv to Hugging Face. | Correct the attribution. |
| The announcement proves coding performance improved 30%. | Same genuine page | NOT_SUPPORTED: no such measured result is reported. | Remove the number or find independent evidence. |
| A study at the synthetic path below proves all context loss is eliminated. | Browser tool could not open it; direct public HTTP request returned 404 | UNVERIFIABLE citation; claim not established | Do not cite or retain as fact. |

The last probe deliberately uses an invented test URL, not a real citation:
`https://www.linuxfoundation.org/press/harness-memory-eliminates-all-context-loss-2026-study`.
The browser's access error alone was not called a 404; a separate HTTP read supplied
that status. These bounded checks demonstrate evidence handling, not universal
source coverage, automated semantic accuracy, or absence of hallucination.
