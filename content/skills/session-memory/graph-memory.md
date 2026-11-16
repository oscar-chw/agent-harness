# Assessing shared graph memory

Use for a requested memory architecture or retrieval redesign. Ordinary task
pickup uses the current shared board and source-linked records directly.

## The useful distinction

The operational board records current task status, next actions and evidence.
A domain graph represents relationships between entities, sources and decisions.
Keep original documents and provenance available. A useful graph relationship
does not itself establish that the represented claim is true or current.

[Omnigraph](https://github.com/ModernRelay/omnigraph/tree/4f7c2076dc7da3e647849bfadf7636f83d36156e)
is a candidate reference for typed node/edge schemas, per-agent branches, reviewed
merges, historical reads and combined keyword/vector/graph retrieval. Its README
describes local disk and object storage with Lance data, plus server and MCP paths.
Those are upstream implementation claims; our current harness has no Omnigraph
backend or qualified migration. Existing version checks on board updates and
graph-branch merging solve different concurrency problems.

## Define a pilot before changing the backend

Freeze representative questions and expected source evidence, including a
multi-hop relationship question, a simple lookup and a case with no valid answer.
Include corrections, withdrawn claims, deletion, time-sensitive facts, project
isolation and conflicting concurrent edits. Measure the existing path and the
candidate on the same inputs. Inspect retrieved evidence and omissions as well
as the final answer. Unchanged-result delivery and full retrieval answer quality
need separate checks.

Charge ingestion, embedding, query, reranking, context construction and maintenance
to total cost. Record cold/warm latency, storage and complete usage where available.
Test restart, schema changes, branch conflicts and backup/restore in isolated data.
An additional service must earn its operational cost through the measured task.

## Adoption decision

Prefer the smallest path that meets the measured retrieval and concurrency need.
A local typed relationship index may suffice. A versioned graph engine may help
when many writers need reviewable domain changes and graph queries. Decide from
evidence and current authority. Keep the candidate isolated until the applicable
quality, cost, access, correction and recovery checks pass. A saved skill or graph
is not evidence of learned model weights or guaranteed future recall.

The linked [video](https://www.youtube.com/watch?v=FeAysJe6FGA) supplied the example.
Its public description and chapter list were inspected on 2026-11-16. Captions
were unavailable. The linked pinned repository supports this bounded review.
