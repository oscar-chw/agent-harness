---
name: clear-docs
description: Readable docs, wikis and slides.
---

# Clear documents and useful visuals

Help the reader understand, decide or act. Do not turn a simple answer into a report.
Infer the audience and next action from the task; ask only if the difference matters.

## Put the useful part first

- Start with the answer, recommendation or purpose, then the next action.
- Use plain words; explain necessary terms beside their first use. Keep precise meaning.
- Use descriptive headings and short paragraphs, not tables filled with long prose.
- Give a short overview with links to depth. Preserve required methods, evidence and limits
  in the body or an appendix; do not delete substance just to shorten the page.
- A runbook starts with when to use it, steps and expected results; link diagnosis/rollback.
- A slide carries one main message. Put detail in notes/handouts, not microscopic text.
- Reuse the project's format and artifact location. No extra report for a tiny request.

## Choose the aid by the question

| Reader needs to see | Useful starting choice | Prefer text when |
|---|---|---|
| Exact values or side-by-side options | Small table with clear headers/units | Only one fact matters |
| Trend, rank, distribution or relationship | A chart matching that relationship | Data is missing or no pattern can be supported |
| Components, boundaries or dependencies | Labeled architecture diagram | A short list already explains the relation |
| Decisions, retries, state or actor interactions | Flow/state/sequence diagram | A few straight steps need no branches |
| Where a control or visual defect is | Current annotated screenshot | Text is more searchable, stable or legible |
| Change over time is itself the lesson | Step-through animation or interaction | A static diagram/series explains it as well |

Choose an aid when it removes real reconstruction/lookup work. No decoration quota.
Start with an overview; split dense detail into linked views instead of shrinking labels.
Keep explanation near the relevant marks. Use a takeaway plus exceptions, not a duplicate
paragraph for every box. See [references.md](references.md) for evidence and limits.

## Make it trustworthy and usable

- Use actual data; label examples and proposals. Keep unknowns visible. Never draw invented
  measurements, claim a proposed architecture is deployed, or imply causation from correlation.
- Name units, time/source and meaningful uncertainty. Explain intervals; avoid false rankings.
- Label relationships directly; do not rely on color or hover alone. Supply a useful text
  equivalent, and exact data where needed. Animated explanations need controls/static fallback.
- Use available native diagram/chart/document tools; do not add a stack just for decoration.
  Prefer editable/vector diagrams and real plotting tools for data over generated image text.
- Inspect the rendered artifact at its intended size: labels, clipping, contrast, source links,
  narrow layout and the reader's next action. Unrendered means NOT_VISUALLY_VERIFIED.

## Learn from use, not from a prettier-looking output

Read [cases.md](cases.md) for ambiguous/negative examples, not a mandatory task checklist.
Use existing scoped lesson/memory tools for concrete reader corrections: audience, task,
failed choice, fix and evidence. If unavailable, retain that in the project handoff.
Keep project preferences scoped; do not promote one person's taste into a universal rule.
Cases and structural validation do not establish measured readability or token improvement.
