# Pstack composition decision — 28 October 2026

Need: a usable coding/research loop and source-bound skill improvement without
another task authority, unbounded fan-out or unmeasured default context.

| Source and exact read | Evidence | Disposition |
| --- | --- | --- |
| [Cursor architect](https://github.com/cursor/plugins/blob/c742dd61706fbacc1b95f1a20b7b988cf096ce6c/pstack/skills/architect/SKILL.md), full selected skill | Documented design sketch, integration grounding and redesign loop; no local superiority experiment | Complement the task/interface template. Its mandatory multiple-candidate/model defaults are not adopted. |
| [Cursor interrogate](https://github.com/cursor/plugins/blob/c742dd61706fbacc1b95f1a20b7b988cf096ce6c/pstack/skills/interrogate/SKILL.md), full selected skill | Findings must have executable reproduction and be rerun by the owner | Complement existing independent gates and review. No review persona or vote replaces a check. |
| [Community port README](https://github.com/michael-denyer/pstack-claude/blob/e397ed54d211a8040ffb46490322708d3536b1fe/plugins/pstack/README.md), selected file | Describes client translations, startup routing, local scripts and data sent through the user's model client | Defer installing the whole port. Startup routing overlaps our owner, and runtime/client parity was not audited. |

This is pattern-level composition, not a package merge. No upstream executable
or skill body is copied, installed or run. The pinned port README identifies MIT
and upstream notices, but licence-file/code/dependency review remains required
before any later code reuse. We did not audit every Pstack skill or its runtime.

The concrete local change is small: the shipped plan prompt uses the existing
graph; templates explain artifacts on demand; the improve CLI prepares exact
episode bindings and exposes lifecycle inspection. Existing draft, correction,
withdrawal, memory and completion logic remain authoritative. Acceptance checks
exercise actual public commands, stale-source refusals, retained memory and
non-activation. No claim of model-quality or token savings follows from them.

Research remains retained even where implementation is deferred. Future Pstack
adoption needs one identified missing capability, a pinned licensed slice and a
paired comparison against the current workflow with full overhead counted.
