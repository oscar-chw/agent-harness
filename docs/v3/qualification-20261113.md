# v3 release qualification

The candidate is **3.0.0rc2**. The four directions share one source-bound memory
and task system. This page records the evidence earned by this candidate.

## What each direction contributes

| Direction | Mechanism and reason | Current evidence |
|---|---|---|
| Framework | Local transactional task board, version checks and per-reader change receipts. Independent sessions can inspect progress without heartbeat chats. | Concurrent duplicate publication, independent continuations, STOP delivery and quiet lease-renewal checks pass. |
| Methodology | Adaptive work graph, independent gates, replayed learning evidence and complete campaign-cost checks. | A read-only campaign assessment exposes the token deficit before adoption. The expensive generated method stays held. |
| Philosophy | Select assumptions, counterexamples, first-principles explanations and teaching questions according to the user's purpose. | Eight source-grounded authored cases cover guidance, direct answers, prerequisites, urgency, transfer and uncertainty. Learner outcomes remain unmeasured. |
| Knowledge vault | Retained source revisions, current scoped claims and disposable search indexes. Source corrections invalidate derived evidence. | Connected-reader tests caught a stale honesty cache after a peer indexed new evidence. Both lexical and FTS paths now refresh it. |

## Measured memory result

Four authored configuration tasks compare retained source-revision history with
the current source-bound memory view. Each arm used the same native model,
effort, current source facts and answer requirements. Order reverses between
tasks. The model receives the selected packet and uses no tools.

| Measure | Retained history | Current memory |
|---|---:|---:|
| Correct task answers | 4/4 | 4/4 |
| Observed input plus output tokens | 111,825 | 99,886 |
| Mean native wall time | 22.26 seconds | 20.87 seconds |

Current memory used **10.68% fewer tokens**. Mean paired saving was
2,984.75 tokens with a 16.98-token standard error across four pairs. Memory
updates used zero model calls. Mean timing was lower in this run. Four pairs
leave reliable speed effects uncertain. These are small authored readback tasks with source-bound corrections.
They leave general coding, research and learner-transfer efficacy unqualified.

The observer checked terminal upstream completions, fresh threads, distinct
responses, bound requests, actual answers, model context and tool abstention.
Cached input is included. The scope covers these eight calls. Whole-project
research and surrounding chat cost remain unknown. Reproduction uses the native
signed-in client and leaves credentials in its normal store. [Native protocol](https://learn.chatgpt.com/docs/app-server)

```sh
python3 eval/v3_memory_pickup.py prepare /path/to/new-study
python3 eval/v3_memory_pickup.py run /path/to/new-study
python3 eval/v3_memory_pickup.py verify /path/to/new-study
```

The run consumes included quota. Each study allows eight calls, no retries and
90 seconds per call, with a 250,000 observed-token stop threshold. The local
instruction environment affects counts. Historical failed attempts remain in
their original records. The aggregate public receipt is in
`eval/results/v3-memory-pickup-20261113.json`.

Two earlier readback qualification runs consumed 423,306 tokens and are retained
as qualification cost. The current result establishes packet-level readback savings.
Net savings for the whole development and evaluation project remain unestablished.

## Philosophy calibration

Eight visible authored cases were evaluated in two four-case batches per arm.
Baseline used 50,726 tokens. Adding the full selected reasoning guide used 52,439,
a 3.38% increase. One guided response used 92 words against the frozen 90-word
limit. The treatment remains unadopted. One earlier malformed-JSON response
consumed 25,219 tokens and remains in the failure ledger.

Initial responses were checked against the case facts and rubric. Multi-turn
learner follow-up, independent learner transfer and teaching efficacy remain
NOT_RUN. The public aggregate is in
`eval/results/v3-philosophy-calibration-20261113.json`.

The current local regression command was
`HARNESS_STAGING_PYTHON=/opt/homebrew/bin/python3.11 PYTHONPATH=src python3 -m pytest -q tests eval --tb=short`.
It returned 3,020 passed, 2 skipped and 2 expected failures. The local path selects
the local wheel-capable interpreter and can be replaced with an equivalent
Python 3.9+ environment carrying setuptools 61+ and wheel.

## Why these decisions

- Retain lexical retrieval and current-source checks. Earlier semantic reranking
  reduced recall on the frozen corpus. A knowledge graph becomes useful only
  where its specific contribution is measured. The original verdicts remain in
  the dated outcome registry.
- Suppress bookkeeping-only updates and coalesce duplicate checkpoints inside
  the write transaction. These changes directly address reproduced repetition
  and concurrent publication failures.
- Evaluate the full learning cost. The separate nine-call generated-procedure
  experiment used 221,538 tokens. Candidate-charged cost was 172,569 against a
  48,969-token baseline. The method stays withheld. Changing tasks or model
  parameters supplies no retrospective credit for that loss.
- Adapt the amount of teaching to the request. The authored cases hold known
  prerequisites constant while changing guided, direct and urgent intent.
  Jane Street's tutor provides a concrete source reference. Local adaptation
  and learner benefit require their own checks. [Socratic Tutor](https://github.com/janestreet/agent_skills/blob/master/socratic-tutor/SKILL.md)

## Workplace evaluation

An evaluation should name its task distribution, independently checked outcomes,
instruction failures, corrections, elapsed time, complete tokens and operational
recovery. A comparison with another harness must match model, tasks, tools,
source access and resource limits. A human comparison also needs recorded human
time, quality and review effort. Those comparisons are **NOT_RUN** here.

Publication of a candidate exposes its reproducible mechanisms and limits.
Stable release and device parity require fresh packaging, CI and installed
readback receipts. Existing loaded clients require reconnection to load runtime
updates. Generated procedures enter use only after the unchanged adoption gate
passes for their exact scope.

## Public test portability

Public CI runs the distributed pure helper and integration checks. Nine checks
requiring the private frozen retrieval corpus are retained unabridged under
`eval/private_reference`, outside ordinary test discovery. AST-hash preservation
checks reject removed or weakened assertions. Explicit private collection fails
when the corpus is absent. The authorized local run exercised all 21 original
functions, including the retained pure checks. Public CI reports private-corpus
execution as NOT_RUN. [Evaluation scope](../../eval/private_reference/README.md)

The rc2 correction prevents a timeout from reporting a probe as observed before
it ran. Protocol fixtures use a separate startup allowance. Deliberate timeout
and rejected-boundary assertions remain enforced.
