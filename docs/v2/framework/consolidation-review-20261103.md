# Frozen development candidate: static integration review

3 November 2026. Baseline 60735e2; current src/content and build configuration
inspected, emphasizing installer/CLI, Copilot, KB metadata and shared retrieval.
No concrete must-fix integration/default-authority defect found in those seams.
Bounded source review, not exhaustive validation or stable-v2 acceptance.
No tests/models/build/install/config changes performed here.

Installer retains profile on uninstall; profile switching stages a candidate,
retains the old tree under backup/.../modified/profile and restores it if publish
fails. Old knowledge is not merged into the active scope. This is not rollback
of later config writes. Copilot MCP follows selected COPILOT_HOME; write-root
checks still constrain destinations. Adapter output does not prove loading.
Privilege mode changes instructions, not native permissions; saved choices take
precedence during rules rendering.

KB adds availability and selected loaded-method identity, not whole-package
identity, primary truth or guaranteed discovery. Live-profile rediscovery keeps
explicit/env-pinned roots separate; unavailable cache text is withheld.
Shared retrieval retains scoped pins, unchanged excerpt defaults and whole-hit
budget admission, including source_window counts. Counts are not completeness.
Source coverage stays an explicit read-only declaration projection; recovery
source packets and shared admission stay opt-in.

Packaging: include untracked source modules and work-loop Markdown in the frozen
inventory; tracked HEAD alone misses them. Setuptools covers package Python files
and skills/*/*, but wheel inspection must establish inclusion. Version remains
2.0.0.dev3; record snapshot identity and wheel digest separately. Root owns full
gates, wheel/install proof and authority review. Laptop ZIP/live settings remain
separate and unchanged; this note grants no rollout/default activation.
