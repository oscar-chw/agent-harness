# Memory benchmark: retrieval helps, but the excerpts remain incomplete

The deployed **2.0.0.dev7** retriever was run on all **500 LongMemEval_S-cleaned
records**. This is a retrieval-component result, not an answer-accuracy score or
a completed V2 qualification.

| Outcome | Count |
|---|---:|
| Attempted | 500 |
| Retrieval cases graded | 463 |
| Abstention cases excluded under the upstream retrieval policy | 30 |
| Metadata-budget errors, retained as failures | 7 |

With a limit of five returned sessions, all relevant sessions were found for **331 of 470
non-abstention questions: 70.4%**, counting the seven errors as unsuccessful.
The reference policy—using the last five supplied sessions—covered **27/470:
5.7%**. This comparison does **not** establish superiority over QMD or another
memory system.

Finding the right session was easier than returning the evidence inside it.
On the 463 graded questions, the returned windows contained **42.5% of marked
evidence-turn occurrences on average**. The current reader selects a first
matching window; a session hit must not be presented as a complete answer.

## Where it struggles

All seven execution errors occurred because complete retrieval/omission metadata
could not fit the unchanged **8 KiB** response budget. None was silently dropped.

| Question class | Non-abstention cases | Errors | All-session recall, errors included |
|---|---:|---:|---:|
| Updated facts | 72 | 1 | 80.6% |
| Across multiple sessions | 121 | 0 | 57.0% |
| Earlier assistant information | 56 | 6 | 78.6% |
| Preferences | 30 | 0 | 73.3% |
| Facts from one session | 64 | 0 | 87.5% |
| Dates and ordering | 127 | 0 | 64.6% |

The next experiments should address compact, fully source-bound metadata and
better evidence windows or follow-up reads. Semantic retrieval and reranking,
including QMD as a candidate backend, need a separate matched comparison.
No retrieval or learning change was activated from this benchmark.

## Reproduce the component run

Use the pinned public data file and run from the repository root:

```sh
PYTHONPATH=src python3 -m eval.run_longmemeval_retrieval \
  --dataset "$DATA_ROOT/longmemeval_s_cleaned.json" \
  --sha256 d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442 \
  --revision 98d7416c24c778c2fee6e6f3006e7a073259d48f \
  --expected-count 500 --output ./new-retrieval-results
```

The run used the actual installed dev7 engine. Reproduction from a checkout must
match the module hashes in [the result manifest](longmemeval-20261106.json).
The working-tree scripts are prepared for publication; publication itself remains
held. Raw conversations are not copied into this public note.

The retrieval loop took about **51 seconds** on an ARM64 Mac. That excludes the
download and initial hash check/JSON loading. This component made **zero model
calls**; it establishes no whole-task token savings. Generated session files were
temporary, while their manifests, citations and observed packets were retained.

## Scope and provenance

The corpus includes both user and assistant turns, adapted into shared notes.
Upstream's flat-session index uses user turns only, so this is **not an official
LongMemEval leaderboard result**. The scorer preserves upstream recall-any/all
and its binary DCG discount. Dataset-declared session labels stay with the grader;
IDs containing answer markers are made opaque before indexing. The first20 cases
were used for adapter development; the remaining480 were not tuned after scoring.

The independent audit rebuilt source hashes and metrics for every graded row,
reproduced all seven errors, and replayed six fixed cases. Ten altered-artifact
controls and eight copied-code mutants were rejected. An earlier partial run and
faulty-fixture failures remain in the local evidence, with corrections recorded.

Sources: [pinned dataset card](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/blob/98d7416c24c778c2fee6e6f3006e7a073259d48f/README.md),
[upstream index construction](https://github.com/xiaowu0162/LongMemEval/blob/9e0b455f4ef0e2ab8f2e582289761153549043fc/src/retrieval/run_retrieval.py),
[upstream metric code](https://github.com/xiaowu0162/LongMemEval/blob/9e0b455f4ef0e2ab8f2e582289761153549043fc/src/retrieval/eval_utils.py).

**Full V2: NOT_QUALIFIED. Learning promotion: NOT_GRANTED. Official QA and
QMD head-to-head comparison: NOT_RUN.**
