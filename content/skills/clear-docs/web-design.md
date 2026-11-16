# Reusable web design decisions

Use when a task needs a visual identity carried across screens or sessions.
A copy edit or small component repair can follow the existing design directly.
This reference complements the client's UI authoring and browser tools.

## Capture intent and implementation together

Inspect the project's existing design system, styles and representative screens.
Describe the audience, main task, density and product character in a short overview.
Record the relevant semantic color roles, typography, spacing, shape, component
states and responsive behavior with their actual values and reasons. A screenshot
supports visual comparison; source styles establish exact tokens. Label inferred
choices and missing evidence. Preserve an existing DESIGN.md format.

For a reusable new system, Google's DESIGN.md format combines YAML tokens with
prose rationale. Tokens give exact values; prose explains their use. Follow its
current schema if claiming compatibility. An example for a dense operational UI
could pair calm neutral surfaces with a high-contrast primary action, visible
failure states and tabular numbers. Derive the choices from the task and brand.

## Make motion earn its place

Use motion to explain a transition, acknowledge an action or communicate meaningful
progress. Choose its duration and frequency for the task. Repeated decorative
motion requires a concrete purpose and a usable static alternative. Honor reduced
motion and provide appropriate controls for automatic moving content. A deliberate
animated focal point may suit a marketing page. A long-lived control panel needs
attention reserved for actionable changes. Preserve accessible focus and keyboard use.

Google's taste-design skill prescribes infinite Pulse/Typewriter/Float/Shimmer
states on active components and staggered list entry. Those are that skill's style
choices. Select animation, fonts, symmetry and palette for this project.

## Verify the result

If the project uses Google's format, run the pinned compatible design linter and
inspect every finding. Export success alone does not establish lint success.
Version 0.4.0 has the portable `designmd` executable alias, including Windows.
Resolve dependencies in the project's existing package manager and lockfile.
An isolated trial can use `npx --package @google/design.md@0.4.0 designmd lint DESIGN.md`.
Check the installed version before applying version-specific commands.

Render representative narrow and desktop screens. Check actual contrast, focus,
text fit, loading/empty/error states, reduced-motion behavior and task completion.
Token/schema validation cannot establish visual quality, accessibility conformance
or an improvement in agent performance. Record which checks actually ran.

## Sources

- [Google DESIGN.md](https://github.com/google-labs-code/design.md/tree/1ed38aa9dd4451b9039f9aeb9ed1d2579edafddf), Apache-2.0.
- [Google design-md skill](https://github.com/google-labs-code/stitch-skills/blob/0337446dadde6f8c94210444e2aa9d546126480f/plugins/stitch-utilities/skills/design-md/SKILL.md), Apache-2.0.
- [Google taste-design motion section](https://github.com/google-labs-code/stitch-skills/blob/0337446dadde6f8c94210444e2aa9d546126480f/plugins/stitch-utilities/skills/taste-design/SKILL.md), Apache-2.0.
- [W3C interaction animation](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html) and [automatic motion](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html) explain distinct criteria.

This is independently written task guidance informed by these sources. Source
review and tool smoke checks establish bounded capability, with efficacy unmeasured.
