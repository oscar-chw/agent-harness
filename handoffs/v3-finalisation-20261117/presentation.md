# Public v3 readiness documentation handoff

17 November 2026. Documentation worker. Session ID UNKNOWN. Root owns implementation, integration gates and rollout. This packet is NOT_REGISTERED because this assignment permits writes only to the two deliverables below.

## Exact files

- [docs/v3/readiness-20261117.md](../../docs/v3/readiness-20261117.md) contains the public architecture, one complete spaced Mermaid diagram, source map, rationale, capability/evidence/limits table and short read-only demonstration.
- [handoffs/v3-finalisation-20261117/presentation.md](presentation.md) contains this handoff and documentation verification evidence.

## Decisions

- Used a dated readiness snapshot while root and two implementation workers continue. Preserved the installed 3.0.0rc2 plus local research-overlay baseline. The active finalisation goal and main broad qualification remain pending.
- Named implementation files in every diagram box and linked them in the source map. Solid arrows include client-directed workflows. The dashed dreaming-to-candidate integration is aspirational. Automatic packet and research withdrawal integration remain pending root gates.
- Kept the central board advisory and graph gates authoritative for completion. Described task state and the legacy continuation interface without implying that either supplies autonomous client behavior.
- Retained unguided rejection at +481 tokens and full-guide compaction at 5,449 saved tokens, 3.50%, six pairs, 24/24 per arm. Linked public aggregate receipts. Preparation cost and net project savings remain unestablished.
- Labelled root's 30 passed memory-admission result as reported partial evidence. Historical dreaming precision 0.6034 against 0.80 remains held. Candidate-only staging belongs to root. No broad deployment, intelligence, teaching-efficacy or provider-adherence claim was added.
- The demonstration inspects existing state and research. New automatic workflows require root's integration qualification. Source tests, native trials, installation, publishing and rollout were NOT_RUN by this worker.

## Verification

Acceptance command is `python3 -` with the document-integrity script recorded below. It failed with exit 1 before creation because the public document was absent. After creation it returned exit 0 and printed `PASS two documents, local links, diagram structure, public-path hygiene and receipt arithmetic`. In-memory missing-link and private-path mutations each raised the expected assertion. The mutation check returned exit 0. Both documents remained unchanged by those controls.

The exact replay command from the repository root is below. It reads the recorded script and checks both deliverables without creating files.

```sh
python3 - <<'PY'
from pathlib import Path
text = Path('handoffs/v3-finalisation-20261117/presentation.md').read_text()
script = text.split('```python\n')[1].split('```')[0]
exec(compile(script, '<documentation-integrity>', 'exec'))
PY
```

```python
from pathlib import Path
import json, re
root = Path.cwd()
names = ("docs/v3/readiness-20261117.md", "handoffs/v3-finalisation-20261117/presentation.md")
texts = {name: (root / name).read_text() for name in names}
public = texts[names[0]]
assert public.count("\x60\x60\x60mermaid") == 1
diagram = public.split("\x60\x60\x60mermaid\n")[1].split("\x60\x60\x60")[0]
assert diagram.count("subgraph ") >= 5
for term in ("Framework", "Methodology", "Philosophy", "Knowledge", "withdraw", "relearn", "candidate", "aspirational", "30 passed", "pending", "3.0.0rc2"):
    assert term.lower() in public.lower(), term
for name, text in texts.items():
    forbidden = ("/" + "Users/", "/" + "home/", "~" + "/", "sk" + "-proj-", "local" + "host", "127" + ".0.0.1")
    assert not any(value in text for value in forbidden), name
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if "://" not in target and not target.startswith("#"):
            assert (root / name).parent.joinpath(target.split("#")[0]).exists(), target
a = json.loads(Path("eval/results/reasoning-iteration-20261117.json").read_text())
b = json.loads(Path("eval/results/reasoning-compaction-20261117.json").read_text())
assert a["candidate_tokens"] - a["baseline_tokens"] == 481
assert b["baseline_tokens"] - b["candidate_tokens"] == 5449
assert a["correct_per_arm"] == b["correct_per_arm"] == {"baseline": 24, "candidate": 24}
assert round(-b["percent_token_change"], 2) == 3.50
assert "5,449" in public and "481" in public and "3.50%" in public and "24/24" in public
assert "NOT_VISUALLY_VERIFIED" in texts[names[1]]
print("PASS two documents, local links, diagram structure, public-path hygiene and receipt arithmetic")
```

Mermaid is **NOT_VISUALLY_VERIFIED**. No local `mmdc` executable was found. Structural checks establish the document shape and source-link integrity. Renderer syntax, clipping and legibility need a rendered review before presentation use.

## Root continuation

Reconcile the pending rows with the original node gates after implementation merges. Retain this snapshot's date and bounded historical verdicts when updating readiness. The finalisation plan owns completion. No plan marks or peer files were changed by this worker. [Active plan](../../plan/v3-finalisation-20261117.md)
