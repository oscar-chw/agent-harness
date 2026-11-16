# Design, presentation and graph-memory skill refresh

Reviewed 16 November 2026. Exact source revisions and inspected paths are in
[the provenance record](skill-refresh-20261116.json).

## Adopted guidance

- **Web design systems.** `clear-docs` now discovers webpage and visual-identity
  work. Its [web-design reference](../content/skills/clear-docs/web-design.md)
  combines design intent, semantic tokens, interaction states and rendered checks,
  informed by Google's DESIGN.md and Stitch skills.
- **Presentations.** Its [presentation reference](../content/skills/clear-docs/presentations.md)
  covers audience, reusable themes/layouts, editable evidence, notes, reading order,
  template preservation and separate file/visual checks. The active client's
  presentation workflow determines its authoring tool and delivery destination.
- **Graph-memory assessment.** `session-memory` links a bounded
  [graph reference](../content/skills/session-memory/graph-memory.md). It explains
  operational state, domain relationships, source provenance, correction and
  concurrent edits, with acceptance criteria for a possible isolated graph trial.

These are references inside two existing skills. Their bodies load on demand.
The clear-docs discovery description grows by 20 UTF-8 bytes. Existing per-part and total
context-budget checks pass. Actual task token savings remain unmeasured.

## Motion selection

Google's pinned taste-design skill, section “Encode Motion Philosophy”, prescribes
infinite Pulse/Typewriter/Float/Shimmer states on active components and staggered
list reveals. Those are project-specific style opinions. Our guidance chooses
motion for the task, preserves reduced-motion behavior and checks the applicable
automatic-motion controls. A marketing focal point and an operational dashboard
have different attention needs. This is a design decision with source rationale,
without a measured head-to-head quality result.

## The linked video

[Omnigraph](https://www.youtube.com/watch?v=FeAysJe6FGA) was identified through
YouTube's public title and description, including the chapter list. Captions were
unavailable. The pinned upstream repository describes typed schemas, per-agent
branches, reviewed merges, historical reads and combined keyword/vector/graph
retrieval. These are useful candidate mechanisms. Existing storage and access
controls remain the current implementation. Omnigraph has not been installed,
integrated or benchmarked by this refresh.

## Checks and limits

The focused delivery checks plus content, context-budget, catalogue, installer,
walkthrough and handoff checks returned 64 PASS and 1 SKIP under Python 3.9. The skip is the existing
Python 3.11+ tomllib profile check. Two skill frontmatter validators and lint pass.
Eight isolated real-helper checks pass, with zero model calls. They cover Google's
0.4.0 design lint/export, rejected broken token references, and the pinned Anthropic
helper's extraction of slide text, tables, chart values and notes, plus valid and
corrupt package validation. A generated PowerPoint fixture supplies known values.
Slide rendering, native PowerPoint opening and model efficacy were not measured.

The Office validator requires Python 3.10+ syntax. An initial Python 3.9 attempt failed
before validation. The same check passed in an isolated Python 3.11 environment.
The fixture check also now accepts the linter's lowercase CSS hex serialization,
preserving the expected color value. An initial check froze the old discovery
description and would prevent a web-design trigger. It was corrected to preserve
skill names and the existing size limits. Original context-budget gates and
invalid-input controls remain in place.

On the available Mac, ten bounded guidance files were baseline-checked, backed up,
installed and read back in a fresh process. Shared skill links resolve to the same
files. The complete pinned Anthropic PPTX skill is a 1.5 MB optional local source
pack, with its license retained. Native presentation plugins, runtime version,
model settings, memories, guards and permissions were outside this change.
Other devices require their own update and readback. Existing loaded contexts
may retain earlier skill text until the next skill load or conversation.
