# Learning lifecycle audit

2026-11-17. Owner is the independent learning auditor. Root owns integration and final gates. Inspected worktree `research-reasoning-20261117`, HEAD `ce5b463558d9dab5427733c3ea3b354b8fdf31f1`, with existing dirty research integration. This packet is the sole repository write. Existing source, plans and peer handoffs were preserved. No native/model calls, installs, credentials, messages or shared-server operations.

## Requirement mapping

| Requirement | Implementation | Gate and evidence | Remaining action |
|---|---|---|---|
| Learn reusable methods/frameworks from evidence | `procedures.py` validates source episodes and distinct task inputs. `procedure_campaign.py` freezes development/held-out inputs, records consumed history, replays evidence and serializes adoption. `method_control.py` gives advisory method decisions. | A and B below pass. `test_v3_learning_cycle.py` covers actual controller logic with a replaced transport, including concurrent adoption, unknown usage, source drift and tampered receipts. | Native generated-method acceptance remains HELD. `docs/v3/qualification-20261113.md` records candidate-charged 172,569 versus baseline 48,969 tokens. This historical experiment was not replayed here. Broad framework benefit remains UNMEASURED. |
| Reuse capability research and preserve upgrade preferences | `research_registry.py` hashes local sources, detects drift, binds preference/record digests and retains bounded history. `content/skills/work-loop/capability-research.md` instructs clients to research missing task families. | A includes 19 registry/retrieval cases. Current source availability and stale-writer checks are exercised. | Research registration and user-confirmation digests establish advisory bookkeeping. Automatic task-family detection, actual human confirmation and measured model adherence remain client responsibilities. Withdrawal gap is blocker 2. |
| Vet acquired skills and suggested plugins | MCP `Server.skill_manage` rejects direct create/update and routes drafts/corrections through procedures. `discover.py` vets pins, installer argv, hidden characters and consent flags, then checks applicable installed commits. `docs/skill-refresh-20261116.json` retains source revisions, licenses, inspected paths and individual decisions. | B covers source-bound drafting, direct-write refusal and skill-refresh packaging. C checks five specific plugin controls with mocked installers. | Evaluate each suggested plugin for task fit, inspected components, permissions, provenance, compatibility and a bounded acceptance check. Record adopt/defer/reject with rationale. Existing vetting is one input to suitability. No plugin installation is implied. Omnigraph remains a reference/pilot candidate. |
| Dream candidate connections and corrections | `memory_dreaming.py` and `memory_dreaming_v1.py` implement trigger, Light/REM/Deep phases, guarded copy writes and receipts. Edges go to a review ledger. Orphan links can be appended to the copy. | A passes both dreaming suites, covering dry-run purity, trigger refusal, phase scope, deterministic output and scoring controls. Historical `docs/v3/h6c-dreaming-v1-verdict-20261110.md` reports orphan precision 0.6034 against required 0.80, recall 0.8537. Edge precision/recall were 0.80/1.0 on 13 labeled candidates. | Overall DISCONFIRMED remains. A general semantic synthesis or skill-generation benefit is UNMEASURED. Candidate-only delivery is blocker 3. Historical corpus metrics were not regenerated here. |
| Withdraw bad advice and prevent relearning it silently | `procedures.correct` atomically rolls back old advice and proposes a linked replacement. `mcp/memory.py` notifies previously recalling sessions. `memory_forget.py` implements tombstone/escrow/certification/relearn. `memory_guard.py` implements admission refusals and quarantine. | A and B pass procedure withdrawal, legacy compatibility, erasure/certification and backflow controls. H5/H6b verdicts document frozen-copy evidence. Probe P1 below FAILS at the ordinary MCP integration seam. | Wire scoped guard configuration through supported entrypoints before claiming persistent runtime protection. Retained source copies, escrow, already-loaded context and literal-free paraphrases remain explicit boundaries. |
| Require measured evaluation before promotion | `procedure_campaign.assess/adopt` replays frozen evidence, full recorded history, per-case quality and complete observed usage. Legacy caller-attested promotion remains refused. | A covers failure to admit missing/malformed/reused usage, changed artifacts, regression and excess cost. `plan/research-reasoning-20261117/05-execute-bounded-native-iteration-and-require-an-.md` retains the two failed attempts. | The parent plan retains exit 1 for instrument drift and exit 1 for the subsequent comparison. Latest recorded baseline/candidate are 149,713/150,194 tokens, all six paired quality differences zero, 299,907 consumed tokens/12 calls, `promotion=NOT_GRANTED`. Root owns native reasoning and any further authority. |

## Top 3 current fixable blockers

1. **Ordinary entrypoints lack configured tombstone enforcement.** `mcp/server.py` constructs `Memory` without a guard in its shared and project-scoped paths. `cli.py` similarly constructs `ProjectMemory` without one. P1 verifies the explicit guard rejects a tombstoned literal while `Server.mem` admits it. This is an opt-in integration gap under finalisation, with the component contract preserved. Smallest next change is a scoped ledger/escrow configuration and common guard construction at these entrypoints. Gate through public MCP and project-memory CLI paths using a temporary corpus. Require refusal after tombstoning, unrelated writes succeeding, corrupt-ledger refusal and relearn admission. Keep missing configuration visible. Existing `test_memory_guard.py` alone cannot establish this wiring.

2. **Capability research has no structured withdrawal state.** `research_registry.FIELDS` has no lifecycle field or withdrawal operation. `check()` returns `REUSE_EXISTING` whenever source hashes match. P2 records explicit withdrawal text in `quality_evaluation` and still receives that status, with `execution_authorized=False`. The probe demonstrates a missing lifecycle capability, rather than a violation of the current advisory schema. Add an explicit withdrawal record/state that retains source history and preferences, overrides reuse, and requires deliberate reevaluation before renewed eligibility. Gate a fresh CLI read after withdrawal, unchanged hashes, stale concurrent writers and explicit replacement. Procedure correction already supplies a narrower pattern to reuse.

3. **Dreaming has no delivered candidate-review boundary for the failed arm.** Historical orphan admission failed its precision gate, yet the research module's copy-apply path still appends scoring-qualified orphan links and labels them promoted. The copy-only contract limits the effect. Finalisation needs a candidate ledger with source hashes and explicit review/admission outcome before integrating synthesized links or procedures into central retrieval. Keep the known-failing arm candidate-only and preserve the split edge result. Gate that a known false orphan remains reviewable but cannot enter normal retrieval, and that a separately approved source-bound candidate can. No threshold relaxation or new semantic-model campaign is needed to deliver this boundary. Broad autonomous dreaming remains ASPIRATIONAL until measured.

## Exact local checks

All checks used this worktree as cwd, Python 3.9, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`, and `-p no:cacheprovider`. These runs preserve source and test bytes. Temporary fixture writes occur outside the repository.

**A** — exit 0, 122 passed in 10.48s.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider tests/test_research_capabilities.py tests/test_v3_learning_cycle.py tests/test_v3_learning_cli.py tests/test_memory_dreaming.py tests/test_memory_dreaming_v1.py tests/test_memory_forget.py tests/test_v1_legacy_promotion.py
```

**B** — exit 0, 87 passed in 36.11s.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider tests/test_v1_learning_loop.py tests/test_memory_guard.py tests/test_skill_refresh.py tests/test_discovery_cycle.py
```

**C** — exit 0, 5 passed in 1.15s. A–C total 214 passing tests across three runs.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider tests/test_harness_best.py::TestReviewFindings::test_the_approval_covers_the_pinned_ref_and_the_exact_argv tests/test_harness_best.py::TestReviewFindings::test_vetting_blocks_hidden_text_consent_skips_and_foreign_programs tests/test_harness_best.py::TestV041::test_a_plugin_pinned_only_by_version_is_not_pinned tests/test_harness_best.py::TestV041::test_an_install_that_is_not_the_approved_commit_is_removed tests/test_harness_best.py::TestV041::test_the_approved_commit_installed_is_recorded
```

### P1 — preserved failing integration probe

Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -` with this temporary-fixture body. Exit 1. Explicit-guard control refused the target and admitted unrelated content. Ordinary `Server.mem` admitted the same target. The last assertion is the proposed finalisation requirement.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from tests.test_memory_guard import _write_corpus, _refs, TARGET, UNIQUE_LITERAL
from agent_harness import memory_forget as F, memory_guard as G
from agent_harness.mcp.memory import Memory
from agent_harness.mcp.server import Server
with TemporaryDirectory(prefix='learning-audit-') as tmp:
    root = Path(tmp)
    corpus, escrow = root / 'corpus', root / 'escrow'
    _write_corpus(corpus)
    F.unlearn(corpus, TARGET, authority='offline-test', reason='audit fixture', escrow_dir=escrow, apply=True)
    guard = G.Guard(ledger_root=corpus, escrow_dir=escrow, reference_texts=_refs(corpus))
    guarded = Memory(home=root / 'guarded', project=root, guard=guard)
    rejected = guarded.mem_add('pin jobs with ' + UNIQUE_LITERAL)
    assert rejected.get('ok') is False
    assert guarded.mem_add('Unrelated audit fixture has green labels.').get('id')
    guarded.close()
    server = Server(home=root / 'public')
    admitted = server.mem.mem_add('pin jobs with ' + UNIQUE_LITERAL)
    server.mem.close()
    print('control explicit Guard refuses tombstoned literal; unrelated write succeeds')
    print('public Server.mem guard is None; same literal admitted=' + str(bool(admitted.get('id'))))
    assert not admitted.get('id'), 'integration gap: ordinary MCP memory has no configured tombstone guard'
```

### P2 — preserved failing withdrawal probe

Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -` with this body. Exit 1. Printed `status=REUSE_EXISTING`, explicit withdrawal metadata and `execution_authorized=false`. The final assertion expresses the missing lifecycle requirement. It does not imply that advisory registration grants procedure activation.

```python
import hashlib, json
from pathlib import Path
from tempfile import TemporaryDirectory
from agent_harness import research_registry as R
with TemporaryDirectory(prefix='learning-audit-') as tmp:
    root = Path(tmp)
    content = root / 'content'
    content.mkdir()
    source = content / 'guide.md'
    source.write_text('# Trial method\nRetained source for a withdrawn research method.\n')
    entry = {'id':'trial-method', 'summary':'Research retained for audit.', 'sources':[{'path':'guide.md','sha256':hashlib.sha256(source.read_bytes()).hexdigest()}], 'related':[], 'reviewed_at':'2026-11-17', 'quality_evaluation':'WITHDRAWN: independent review rejected this advice'}
    home = root / 'home'
    home.mkdir()
    result = R.record(home, entry, content=content)
    print(json.dumps({'quality_evaluation':entry['quality_evaluation'], 'status':result['status'], 'execution_authorized':result['execution_authorized']}))
    assert result['execution_authorized'] is False
    assert result['status'] != 'REUSE_EXISTING', 'lifecycle gap: no structured withdrawal veto on capability reuse'
```

## Handoff limits

Root final gates, live installations, historical artifact replays and native efficacy were NOT_RUN here. `handoffs/research-reasoning-20261117/orchestrator.md` predates the node-05 completed comparison and still says no scored calls yet. The parent plan and node record retain the newer failure. Prefer those dated records during integration. Older `docs/v2/methodology/native-promotion.md` predates the current controller-owned adoption path.

Memory lookup supplied the canonical project/proposal-only qualification context from `MEMORY.md` lines 234–245. All implementation findings above were inspected in the current worktree. No memory store was written.
