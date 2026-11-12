# New memory and autonomous-loop references

31 October 2026. Bounded public-source review; no installation, model calls,
benchmark replication or change to native permissions. Addendum to the retained
source audit, not a replacement for its 108-item denominator.

## Acquisition and read depth

| Source | Read this turn | Evidence and limit |
|---|---|---|
| [Smartpigai post](https://x.com/Smartpigai/status/2116168908722028993) | Full public post text through browser | Secondary commentary; embedded media not inspected |
| [AnnatarXBT post](https://x.com/AnnatarXBT/status/2116256966381301780) | Full public post text through browser | Primary projects resolved independently; employment and experiment-count claims not verified |
| [Linked Buzzoni guide](https://x.com/Mr_Buzzoni/status/2115443090068516935) | Full article text through browser | Practical proposal; earnings, pricing, latency and savings claims not qualified |
| [Memory Tax: Dissecting the Net Value of Agent Memory](https://arxiv.org/html/2610.34073v1) | Introduction, main result table, diagnostic sections, design implications, baseline and metric details | Paper reviewed selectively, not replicated |
| [MemoryTax: The Bitter Lesson of Agent Memory](https://arxiv.org/abs/2610.29823) | Abstract | Different paper: one conversation, one run per cell; caption visibility confounds part of the comparison |
| [Librarian Agents](https://arxiv.org/abs/2610.22273) | Abstract | Trained builder using reinforcement learning; not evidence that a prompted nightly curator reproduces its gains |
| [Anthropic graph cookbook](https://platform.claude.com/cookbook/capabilities-knowledge-graph-guide) | Setup, extraction overview, query example, evaluation and scaling sections | API example, not an installed subscription-compatible integration |
| [Karpathy autoresearch](https://github.com/karpathy/autoresearch) and [program.md](https://raw.githubusercontent.com/karpathy/autoresearch/master/program.md) | README mechanism and experiment instructions | Pattern reference; no GPU experiment run |
| [Karpathy llm-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Complete idea file, excluding comment-thread claims | Method proposal, not measured harness efficacy |
| [TypeSafe System One](https://docs.typesafe.ai/api/system-one) | API request/response and authorization schema | Identifies Jev; no account, install or API invocation |

## Findings

The broader Memory Tax paper compares eleven memory systems with a substantial
raw-history retrieval baseline: BM25 plus dense search and reranking, optionally
two rounds. Its diagnosis distinguishes information loss, retrieval difficulty
and reader/writer model changes. Source recovery alongside derived memory is a
useful design lead. This does not establish our local system's performance or
prove structured memory universally inferior. See its main table and sections
4, 6 and A.2 at the linked paper.

The smaller MemoryTax paper is a separate study, not a replication of that
eleven-system comparison. Its abstract explicitly discloses narrow sampling and
unequal photo-caption availability. Keep those limits attached to its headline.

The cookbook demonstrates extraction, entity resolution and graph-backed
answers. Its relation scorer ignores predicate wording; use that as a warning
against treating entity connectivity as relationship correctness. It requires an
Anthropic API key. Reuse methodology without assuming the example runs through
Claude Max authentication.

Autoresearch separates an editable training file from fixed evaluation, uses a
fixed experiment duration and keeps a results ledger. Transfer the experimental
discipline, not its unbounded loop or permission-disabling recommendation.

The llm-wiki idea preserves original sources and maintains a linked derived wiki
with an index and chronological log. It offers a useful human-readable view;
the source itself calls the tooling optional and domain-dependent.

Jev is now concretely identified: TypeSafe documents a remote decision endpoint
with named questions, typed answers, effective model and usage fields. A typed
response is not evidence of calibrated routing quality, local inference, privacy
equivalence or net token savings.

## Architecture decisions — proposed, not deployed

1. Preserve a searchable authorized source path alongside derived notes/graphs.
   Do not require a summary or graph traversal to reach original evidence.
2. Treat wiki pages as inspectable, versioned views with source spans, dates,
   conflict/correction links and recorded read depth. A graph edge needs its
   relationship, direction and source checked, not merely valid endpoints.
3. Prefer exact/current lookup first when sufficient. Trial joint source/derived
   ranking on questions that need it, within a bounded context and latency budget.
   Do not install a vector or graph service from a social post alone.
4. Curate incrementally where repeated use can repay construction. Compare
   ingestion, maintenance, retrieval and answering costs together, with the same
   reader, evidence visibility and tasks. A stronger writer is a candidate to
   test, not a mandatory choice for every update.
5. Use independent frozen checks, bounded experiments, resource ceilings,
   stop/recovery and rollback for improvements. Never let generated knowledge
   or a successful experiment revise its own acceptance rule or approval scope.
6. Jev remains an optional remote-router candidate. Start with existing native
   capabilities and deterministic rules; require measured end-to-end benefit,
   abstention controls and explicit data/service authorization before adoption.
   API inference would leave the machine even if stored memory remains local.

## Qualification still required

Use authorized project questions spanning exact recall, paraphrase, multi-source
relations, temporal corrections, contradictory sources, missing evidence and
scope exclusion. Compare current lexical retrieval, raw evidence retrieval,
derived-only retrieval and their bounded combination. Test model changes and
cold-session pickup. Report answer support, missed/false memories, cumulative
tokens, latency, storage and maintenance separately. A broken/stale index must
leave the original evidence recoverable; an unavailable source must remain
UNKNOWN. No such new paired model campaign was run here.

The eight-page diagram booklet already distinguishes originals from derived
retrieval, optional graph/semantic routes and evaluated promotion. These sources
refine that proposal; they do not justify calling it fully implemented or better
than competing systems. Native guard approval/resumption remains unqualified.
