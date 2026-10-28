# Node 11 — Verify the integrated archive development checkpoint

plan: v1-memory-foundation
gate: `bash scripts/check.sh`
ctx: (none)

## Attempt 2026-10-26T10:47:39Z — local developer — 384s — exit 0

```
== offline wheel build: /opt/homebrew/bin/python3.11
== tests (the harness, the guard corpus, the eval instrument)
....................s................................................... [  5%]
..................s..................................................... [ 10%]
.................................................xx..................... [ 15%]
........................................................................ [ 20%]
........................................................................ [ 25%]
........................................................................ [ 30%]
........................................................................ [ 35%]
........................................................................ [ 41%]
........................................................................ [ 46%]
........................................................................ [ 51%]
........................................................................ [ 56%]
........................................................................ [ 61%]
........................................................................ [ 66%]
........................................................................ [ 71%]
........................................................................ [ 76%]
........................................................................ [ 82%]
........................................................................ [ 87%]
........................................................................ [ 92%]
........................................................................ [ 97%]
...................................                                      [100%]
1399 passed, 2 skipped, 2 xfailed in 377.21s (0:06:17)
== secret scan
SECRET-SCAN

… 475 bytes elided …

n - skill data-job-trial-run (shared .agents/skills)
  copy to $DEMO_HOME/.agents/skills/debug-systematically - skill debug-systematically (shared .agents/skills)
  copy to $DEMO_HOME/.agents/skills/production-code - skill production-code (shared .agents/skills)
  copy to $DEMO_HOME/.agents/skills/standards - skill standards (shared .agents/skills)
  copy to $DEMO_HOME/.agents/skills/verify-before-done - skill verify-before-done (shared .agents/skills)
  copy to $DEMO_HOME/.agents/skills/work-loop - skill work-loop (shared .agents/skills)
  copy to $DEMO_HOME/.agents/skills/write-tests-first - skill write-tests-first (shared .agents/skills)
  symlink $DEMO_HOME/.claude/skills/data-job-trial-run - skill data-job-trial-run (link to .agents/skills)
  symlink $DEMO_HOME/.claude/skills/debug-systematically - skill debug-systematically (link to .agents/skills)
  symlink $DEMO_HOME/.claude/skills/production-code - skill production-code (link to .agents/skills)
  symlink $DEMO_HOME/.claude/skills/standards - skill standards (link to .agents/skills)
  symlink $DEMO_HOME/.claude/skills/verify-before-done - skill verify-before-done (link to .agents/skills)
  symlink $DEMO_HOME/.claude/skills/work-loop - skill work-loop (link to .agents/skills)
  symlink $DEMO_HOME/.claude/skills/write-tests-first - skill write-tests-first (link to .agents/skills)
  write $DEMO_HOME/.claude/commands/explain-this-repo.md - slash command /explain-this-repo
  write $DEMO_HOME/.claude/commands/fix-failing-test.md - slash command /fix-failing-test
  write $DEMO_HOME/.claude/commands/plan.md - slash command /plan
  write $DEMO_HOME/.claude/commands/review.md - slash command /review
  write $DEMO_HOME/.claude/agents/harness-quick.md - subagent harness-quick: haiku, effort low
  write $DEMO_HOME/.claude/agents/harness-standard.md - subagent harness-standard: sonnet, effort medium
  write $DEMO_HOME/.claude/agents/harness-deep.md - subagent harness-deep: opus, effort high
  write $DEMO_HOME/.claude/agents/harness-review.md - subagent harness-review: opus, effort high
  Warning: this replaces your current Claude Code setup (backed up; `harness uninstall` restores it)
Dry run: nothing was written.

$ harness --home $DEMO_HOME install --yes --tools claude-code && harness --home $DEMO_HOME doctor
[ok] python 3.9.6
[ok] SQLite FTS5 available
[ok] claude-code: $DEMO_HOME/.claude/CLAUDE.md
[ok] claude-code: $DEMO_HOME/.claude/settings.json
[ok] claude-code: $DEMO_HOME/.claude.json
[ok] claude-code: $DEMO_HOME/.agents/skills/data-job-trial-run
[ok] claude-code: $DEMO_HOME/.agents/skills/debug-systematically
[ok] claude-code: $DEMO_HOME/.agents/skills/production-code
[ok] claude-code: $DEMO_HOME/.agents/skills/standards
[ok] claude-code: $DEMO_HOME/.agents/skills/verify-before-done
[ok] claude-code: $DEMO_HOME/.agents/skills/work-loop
[ok] claude-code: $DEMO_HOME/.agents/skills/write-tests-first
[ok] claude-code: $DEMO_HOME/.claude/skills/data-job-trial-run
[ok] claude-code: $DEMO_HOME/.claude/skills/debug-systematically
[ok] claude-code: $DEMO_HOME/.claude/skills/production-code
[ok] claude-code: $DEMO_HOME/.claude/skills/standards
[ok] claude-code: $DEMO_HOME/.claude/skills/verify-before-done
[ok] claude-code: $DEMO_HOME/.claude/skills/work-loop
[ok] claude-code: $DEMO_HOME/.claude/skills/write-tests-first
[ok] claude-code: $DEMO_HOME/.claude/commands/explain-this-repo.md
[ok] claude-code: $DEMO_HOME/.claude/commands/fix-failing-test.md
[ok] claude-code: $DEMO_HOME/.claude/commands/plan.md
[ok] claude-code: $DEMO_HOME/.claude/commands/review.md
[ok] claude-code: $DEMO_HOME/.claude/agents/harness-quick.md
[ok] claude-code: $DEMO_HOME/.claude/agents/harness-standard.md
[ok] claude-code: $DEMO_HOME/.claude/agents/harness-deep.md
[ok] claude-code: $DEMO_HOME/.claude/agents/harness-review.md
[ok] MCP server answers tools/list within 5 s (15 tools)
[ok] disk footprint 1.0 MB (cap 20 MB)

$ python3 content/hooks/guard.py --check "rm -rf ~"
exit 2

$ python3 content/hooks/guard.py --check "git status && pytest -q"
exit 0

DEMO: PASS
CHECK: PASS
agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.
```

Public copy: local author/path identifiers redacted; original retained privately.
Original SHA-256: `7591a39ec96d2af70e749ee27fae96f8b1087964372563001b94d6101e28cac7`. Test outcomes are unchanged.
