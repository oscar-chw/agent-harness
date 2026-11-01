<!-- Local identity/path redacted; original evidence SHA256 198545795fdf1163bf24d7eae72ac9c71e7e82a1fc6797e1f536a60650d07766 retained privately. -->
# Node 1 — Make scoped retrieval independent of other cached projects

plan: v1-memory-foundation
gate: `python3 -m pytest -q tests/test_kb_scope.py tests/test_mcp.py`
ctx: src/agent_harness/mcp/kb.py

## Attempt 2026-10-26T08:05:58Z — local developer — 0s — exit 2

```
==================================== ERRORS ====================================
___________________ ERROR collecting tests/test_kb_scope.py ____________________
ImportError while importing test module '<checkout>/tests/test_kb_scope.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/importlib/__init__.py:127: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/test_kb_scope.py:4: in <module>
    from agent_harness.mcp.kb import KB, fts5_available
E   ModuleNotFoundError: No module named 'agent_harness'
=========================== short test summary info ============================
ERROR tests/test_kb_scope.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.24s
```

## Attempt 2026-10-26T08:08:02Z — local developer — 2s — exit 0

```
.......................................                                  [100%]
39 passed in 2.21s
```

## Attempt 2026-10-26T08:10:33Z — local developer — 2s — exit 0

```
.........................................                                [100%]
41 passed in 2.22s
```

## Attempt 2026-10-26T08:25:32Z — local developer — 2s — exit 0

```
.........................................                                [100%]
41 passed in 2.22s
```
