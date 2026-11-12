# Public and private evaluation scope

Public CI exercises the pure research helpers in `tests/support/v3_research`
and the retained public assertions. `tests/test_v3_public_eval_scope.py` checks
the original function/method AST hashes against `MANIFEST.json`, the
unchanged retained public assertions, and failure when private checks are
explicitly collected with an absent research root.

The manifest records private corpus distribution as `NOT_DISTRIBUTED` and
private-corpus execution in public CI as `NOT_RUN`. The five unabridged original
files retain 93 function/method bodies, including 75 original test functions
and methods. Twelve private-artifact/context checks are explicitly isolated from
public discovery. The other 63 original checks retain their public assertions.

The private files are `h6a_recorded_corpus.py`, `kb_honesty_corpus.py`,
`jev_recorded_corpus.py`, `plugin_recorded_corpus.py` and
`settlement_recorded_context.py`.
Their explicit filenames keep ordinary public pytest discovery scoped to the
distributed checks. Their hashes preserve the assertions through relocation.

## Run the original private checks

Provide an authorized research checkout containing the matching `src`, original
helper modules and frozen artifacts under `.harness-work/v3-h6a-l2-candidacy`,
`.harness-work/v3-h3-hybrid` and `.harness-work/v3-h1-consolidation`.
Historical JEV and plugin qualification also requires the original bound H6a
evaluation/mutation receipts and the pipeline receipt
`.harness-work/eval-pipeline-20261110/runs/run-20261111T005928Z-2deaf2a8.json`.
The plugin method retains its original successful-admission expectation.
The historical settlement method also requires the original signing context.
Its post-signing hygiene tokens `/Users/me`, `agent@` and `redacted-host` are
reconstructed from the verifying process's live HOME, user and hostname.
Readable relocated files alone cannot recreate the original source signatures.
Dynamic signature, corruption and refusal controls remain in public CI.
From the public checkout, run

```sh
HARNESS_RESEARCH_ROOT=/absolute/path/to/authorized-research-checkout \
  PYTHONPATH=src python3 -m pytest -q \
  eval/private_reference/h6a_recorded_corpus.py \
  eval/private_reference/kb_honesty_corpus.py \
  eval/private_reference/jev_recorded_corpus.py \
  eval/private_reference/plugin_recorded_corpus.py \
  eval/private_reference/settlement_recorded_context.py
```

Missing helpers, corpus files or frozen artifacts produce collection errors
or failed assertions and a nonzero exit. Every original check remains required
for its private qualification claim. The public collection-failure probe uses
an absent temporary research root and invokes the H6a and KB files together once.
Two additional subprocess probes invoke the original JEV and plugin methods
individually with copied public prerequisites and absent private bindings.
They check the precise missing historical input/receipt reason and require the
original method to fail. Their expectations and assertion bodies remain intact.
One further subprocess invokes the original historical settlement method with
an absent research root and requires its missing-plan failure. Positive
historical settlement qualification requires the authorized original signing
host, original plan/record bytes and the unchanged original assertions.
Public helper and preservation results establish their stated source scope.
Private-corpus outcome claims require the explicit run with its authorized data.
