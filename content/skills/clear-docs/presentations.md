# Presentations people can read and edit

Use for slide content, templates and presentation quality. Follow the active
client's presentation skill for the authoring tool and output destination.
An available native presentation workflow owns its connection, export and delivery.
Confirm dependencies before using a local helper; upstream environment assumptions
such as preinstalled libraries may differ on this machine.
The pinned Office validator uses Python 3.10+ syntax. Check that interpreter and
its dependencies together; use an isolated environment when the system Python is older.

## Structure for the audience

Establish whether the deck is presented live, read beforehand or edited by others.
Fit the amount of text and evidence to that use. Write an outline that preserves
the requested content, then choose a clear message or subject for each slide.
Use layouts suited to the material, such as a diagram, table, chart or comparison.
Keep extra derivations and precise sources in readable notes or an appendix.
A short deck can go straight to the point.

## Preserve a usable PowerPoint document

For PPTX output, prefer theme-linked colors and fonts, reusable layouts, named
placeholders and meaningful reading order where the selected authoring tool
supports them. Preserve the supplied template's actual layout and branding.
Keep required charts, tables and diagram elements editable. Include descriptive
alternative text for images and use speaker notes for contextual sources.

When editing, inspect both rendered slides and extracted content, including
notes, tables and chart values. Inventory required content before changing it.
Remove an unused template slot together with its associated visual group.
Use a separate output copy and unique render/thumbnail paths per deck.

Local OOXML edits need package relationships, content types and slide order kept
consistent. Use reviewed helpers for structural changes and validate the result.
If using PptxGenJS, verify its actual canvas dimensions, supported chart options,
theme behavior and units against the pinned library version. Build fresh options
objects where the library mutates them. These details are backend-specific.

## Check content, file integrity and appearance

Check requested coverage, numbers, units, sources, notes, editability and reading
order. Run the selected backend's package/schema checks. Reopen or import the
exported artifact when available. Render and inspect every slide at presentation
size for clipping, overlap, illegible labels, absent visuals and template drift.
Read-only text extraction and XML validation establish different evidence.
Report any unavailable render, native opening or editing check explicitly.

## Upstream reference

[Anthropic PPTX skill](https://github.com/anthropics/skills/tree/1780c5e5a552fd4d1c9d6a7b0cab26b0c2bef064/skills/pptx)
documents structured decks, notes/text extraction and Office validation helpers.
Its own LICENSE.txt at this revision is Apache-2.0. Older indexed descriptions
show different terms, so retain the revision and inspect the actual license.
An optional reviewed local copy may be under the harness home's
`skill-packs/anthropic-pptx/<revision>/`; its helpers still need compatible dependencies.
This reference is independently written guidance. Helper smoke tests establish
file operations only. Visual quality and reduced token use need separate evidence.
