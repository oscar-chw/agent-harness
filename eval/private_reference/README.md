# Public and private evaluation scope

Public CI exercises the pure research helpers in `tests/support/v3_research`
and the retained public assertions. `tests/test_v3_public_eval_scope.py` checks
the original private test-function AST hashes against `MANIFEST.json`, the
unchanged retained public assertions, and failure when private checks are
explicitly collected with an absent research root.

The manifest records private corpus distribution as `NOT_DISTRIBUTED` and
private-corpus execution in public CI as `NOT_RUN`. The original 21 test
functions remain in `h6a_recorded_corpus.py` and `kb_honesty_corpus.py`.
Their explicit filenames keep ordinary public pytest discovery scoped to the
distributed checks. Their hashes preserve the assertions through relocation.

## Run the original private checks

Provide an authorized research checkout containing the matching `src`, original
helper modules and frozen artifacts under `.harness-work/v3-h6a-l2-candidacy`,
`.harness-work/v3-h3-hybrid` and `.harness-work/v3-h1-consolidation`.
From the public checkout, run

```sh
HARNESS_RESEARCH_ROOT=/absolute/path/to/authorized-research-checkout \
  PYTHONPATH=src python3 -m pytest -q \
  eval/private_reference/h6a_recorded_corpus.py \
  eval/private_reference/kb_honesty_corpus.py
```

Missing helpers, corpus files or frozen artifacts produce collection errors
or failed assertions and a nonzero exit. Every original check remains required
for its private qualification claim. The public collection-failure probe uses
an absent temporary research root and invokes both private files once.
Public helper and preservation results establish their stated source scope.
Private-corpus outcome claims require the explicit run with its authorized data.
