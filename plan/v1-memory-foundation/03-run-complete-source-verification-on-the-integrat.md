<!-- Local identity/path redacted; original evidence SHA256 2c67423348069d5973d43ded8e9dd33bd71ba314f305211ce31fecd2450ea43e retained privately. -->
<!-- Local identity/path redacted; original evidence SHA256 a5746399853eba3ca836e7de2c2adc0d0255ac7b8e4c3646a208cada749098eb retained privately. -->
# Node 3 — Run complete source verification on the integrated checkpoint

plan: v1-memory-foundation
gate: `bash scripts/check.sh`
ctx: (none)

## Attempt 2026-10-26T08:31:51Z — local developer — 379s — exit 1

```
== offline wheel build: /opt/homebrew/bin/python3.11
== tests (the harness, the guard corpus, the eval instrument)
....................s................................................s.. [  5%]
........................................................................ [ 10%]
............................xx.......................................... [ 15%]
........................................................................ [ 21%]
........................................................................ [ 26%]
........................................................................ [ 31%]
........................................................................ [ 36%]
........................................................................ [ 42%]
........................................................................ [ 47%]
........................................................................ [ 52%]
........................................F.........F..................... [ 58%]
........................................................................ [ 63%]
........................................................................ [ 68%]
........................................................................ [ 73%]
........................................................................ [ 79%]
........................................................................ [ 84%]
........................................................................ [ 89%]
........................................................................ [ 95%]
....................................................................     [100%]
=================================== FAILURES ===================================
____________ TestV041.test_every_skip_in_the_suite_is_environmental ____________

self = <tests.test_harness_best.TestV041 testMethod=test_every_skip_in_the_suite_is_environmental>

    def test_every_skip_in_the_suite_is_environmental(self):
        allowed = ("tomllib", "HARNESS_LIVE", "root reads", "no git history", "no release tag")
        bad = []
        for f in (ROOT / "tests").glob("test_*.py"):
            lines = f.read_text().splitlines()
            for n, line in enumerate(lines, 1):
                if re.search(r"skipTest\(|pytest\.skip\(|SkipTest\(|skipIf\(|skipUnless\(", line) \
                        and "allowed = (" not in line and "re.search(" not in line:
                    ctx = " ".join(lines[n - 1:n + 1])
                    if not any(a in ctx for a in allowed):
                        bad.append("%s:%d" % (f.name, n))
>       self.assertEqual(bad, [])
E       AssertionError: Lists differ: ['test_kb_scope.py:10'] != []
E       
E       First list contains 1 additional elements.
E       First extra element 0:
E       'test_kb_scope.py:10'
E       
E       - ['test_kb_scope.py:10']
E       + []

tests/test_harness_best.py:1020: AssertionError
___________ TestV041b.test_every_skip_names_an_environmental_reason ____________

self = <tests.test_harness_best.TestV041b testMethod=test_every_skip_names_an_environmental_reason>

    def test_every_skip_names_an_environmental_reason(self):
        """Every skip shape (skipTest, skip decorators, pytest.skip/importorskip/mark.skip, SkipTest, and an
        `except ImportError` that returns or passes) must name an allowed, environmental reason in its code,
        comments stripped (a comment saying "tomllib" must not excuse a skip)."""
        import io as _io
        import tokenize
        allowed = ("tomllib", "HARNESS_LIVE", "root reads", "no git history", "no release tag")
        shape = re.compile(r"skipTest\(|\.skip\(|skipIf\(|skipUnless\(|importorskip\(|mark\.skip|SkipTest\(")
        bad = []
        for f in (ROOT / "tests").glob("test_*.py"):
            src = f.read_text()
            lines = src.splitlines()
            code = src.splitlines()                  # also strings blanked: a skip quoted as test data is data
            for tok in tokenize.generate_tokens(_io.StringIO(src).readline):
                (r1, c1), (r2, c2) = tok.start, tok.end
                if tok.type == tokenize.COMMENT:
                    lines[r1 - 1] = lines[r1 - 1][:c1]
                    code[r1 - 1] = code[r1 - 1][:c1]
                elif tok.type == tokenize.STRING and r1 == r2:
                    code[r1 - 1] = code[r1 - 1][:c1] + '""' + code[r1 - 1][c2:]
            for n, line in enumerate(code, 1):
                if f.name == "test_harness_best.py" and ("shape = re.compile" in lines[n - 1]
                                                         or "allowed = (" in lines[n - 1]):
                    continue
                if shape.search(line) and not any(a in " ".join(lines[n - 1:n + 2]) for a in allowed):
                    bad.append("%s:%d" % (f.name, n))
                if re.match(r"\s*except\s*\(?[^:]*\b(ImportError|ModuleNotFoundError)\b[^:]*\)?\s*(as\s+\w+)?\s*:",
                            line) and n < len(lines) and re.match(r"\s*(return|pass)\b", lines[n]):
                    bad.append("%s:%d except ImportError: %s" % (f.name, n, lines[n].strip()))
>       self.assertEqual(bad, [])
E       AssertionError: Lists differ: ['test_kb_scope.py:10'] != []
E       
E       First list contains 1 additional elements.
E       First extra element 0:
E       'test_kb_scope.py:10'
E       
E       - ['test_kb_scope.py:10']
E       + []

tests/test_harness_best.py:1133: AssertionError
=========================== short test summary info ============================
FAILED tests/test_harness_best.py::TestV041::test_every_skip_in_the_suite_is_environmental
FAILED tests/test_harness_best.py::TestV041b::test_every_skip_names_an_environmental_reason
2 failed, 1358 passed, 2 skipped, 2 xfailed in 378.84s (0:06:18)
```

## Attempt 2026-10-26T08:40:43Z — local developer — 387s — exit 0

```
== offline wheel build: /opt/homebrew/bin/python3.11
== tests (the harness, the guard corpus, the eval instrument)
....................s................................................s.. [  5%]
........................................................................ [ 10%]
............................xx.......................................... [ 15%]
........................................................................ [ 21%]
........................................................................ [ 26%]
........................................................................ [ 31%]
........................................................................ [ 36%]
........................................................................ [ 42%]
........................................................................ [ 47%]
........................................................................ [ 52%]
........................................................................ [ 58%]
........................................................................ [ 63%]
........................................................................ [ 68%]
........................................................................ [ 73%]
........................................................................ [ 79%]
........................................................................ [ 84%]
........................................................................ [ 89%]
........................................................................ [ 95%]
....................................................................     [100%]
1360 passed, 2 skipped, 2 xfailed in 380.72s (0:06:20)
== secret scan
SECRET-SCAN: PASS
== demo (scripts/demo.sh: a throwaway home, never yours)
$ harness --home

… 395 bytes elided …

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
