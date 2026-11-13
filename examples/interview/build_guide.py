"""Build the offline interview guide and a source-aligned architecture SVG."""
from html import escape
import hashlib
import json
from pathlib import Path
import re

from check_pack import require, validate_receipt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PUBLIC = "https://github.com/oscar-chw/agent-harness/blob/cdf2bb28beb1e1de470daad5d9a801b78cf82e7d/"


def box(x, y, width, height, title, lines, fill="#ffffff", stroke="#c9d3cf"):
    parts = [f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="12" '
             f'fill="{fill}" stroke="{stroke}"/>',
             f'<text x="{x+22}" y="{y+34}" class="boxTitle">{escape(title)}</text>']
    for i, line in enumerate(lines):
        parts.append(f'<text x="{x+22}" y="{y+63+i*24}" class="boxBody">{escape(line)}</text>')
    return "".join(parts)


def arrow(path, label="", x=0, y=0, dashed=False, both=False):
    dash = 'stroke-dasharray="7 6"' if dashed else ""
    start = 'marker-start="url(#arrow)"' if both else ""
    result = (f'<path d="{path}" fill="none" stroke="#38615c" stroke-width="2" '
              f'{dash} {start} marker-end="url(#arrow)"/>')
    if label:
        result += f'<text x="{x}" y="{y}" class="edgeLabel">{escape(label)}</text>'
    return result


def architecture():
    items = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="1040" viewBox="0 0 1440 1040" role="img" aria-labelledby="title desc">
<title id="title">Agent Harness 3.0.0rc2 architecture</title>
<desc id="desc">Native clients use separate MCP processes. Project-scoped task coordination and source-backed memory are shared locally. The work graph runs guarded gates. Evaluation controls candidate adoption. Model behavior and cross-device synchronization require separate verification.</desc>
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto-start-reverse"><path d="M0,0 L0,6 L7,3 z" fill="#38615c"/></marker></defs>
<style>text{font-family:Arial,sans-serif;fill:#193b36}.boxTitle{font-size:22px;font-weight:700}.boxBody{font-size:18px;fill:#3e5b55}.edgeLabel{font-size:16px;fill:#315a53;paint-order:stroke;stroke:#f4f7f3;stroke-width:5px;stroke-linejoin:round}.section{font-size:18px;font-weight:700;letter-spacing:1px}.small{font-size:17px;fill:#52665f}</style>
<rect width="1440" height="1040" fill="#f4f7f3"/>
<text x="50" y="48" font-size="31" font-weight="700">Work survives the conversation</text>
<text x="50" y="79" class="small">As-built mechanisms / 3.0.0rc2 / 13 November 2026 / local request-driven processes</text>
''']
    items += [box(60, 112, 405, 105, "Client A", ["Native app + selected model", "Own login, tools and approvals"]),
              box(505, 112, 405, 105, "Client B", ["Independent session or model", "Own login, tools and approvals"]),
              box(970, 112, 410, 105, "CLI entrypoints", ["harness task publishes board checkpoints", "plan operates the work graph"])]
    items += ['<rect x="35" y="254" width="1370" height="606" rx="18" fill="#eaf0e9" stroke="#b7c9bd"/>',
              '<text x="60" y="284" class="section">LOCAL HARNESS / SAME HOME + CANONICAL PROJECT</text>']
    items += [box(60, 310, 850, 112, "Per-client MCP server", ["One process per connection; initialization and tool-response context", "Supported lifecycle hooks provide another client-specific entrypoint"]),
              box(970, 310, 410, 112, "Work graph", ["Dependencies, claims and gate evidence", "Exit 0 settles; failure returns pending"]),
              box(60, 496, 405, 145, "Shared task board", ["SQLite tasks, versions and event cursors", "CAS rejects stale writes; retries use IDs", "Advisory summaries point to checkpoints"]),
              box(505, 496, 405, 145, "Source-backed memory", ["Retained revisions and scoped claims", "Lexical / FTS retrieval and source checks", "Corrections invalidate derived evidence"]),
              box(970, 496, 410, 145, "Execution controls", ["Command guard screens gate commands", "Native approvals and OS rights still apply", "Sandbox protection depends on setup"]),
              box(60, 713, 850, 108, "Evaluation and scoped adoption", ["Frozen cases + independent outcomes + measured preparation/trial cost", "Generated procedures remain held after token regression"], fill="#fff4df", stroke="#d4b478"),
              box(970, 713, 410, 108, "Tools, tests and artifacts", ["Real subprocess results become evidence", "A passing gate has its declared scope"])]
    items += [arrow("M262 217 V310"), arrow("M707 217 V310"), arrow("M1175 217 V310"),
              arrow("M910 364 H970", "plan tool", 920, 347),
              arrow("M262 422 V496", "read / checkpoint", 275, 465, both=True),
              arrow("M707 422 V496", "retrieve / record", 720, 465, both=True),
              arrow("M1175 422 V496", "screen command", 1188, 465),
              arrow("M1175 641 V713", "allowed execution", 1190, 681),
              arrow("M970 766 H910", "outcomes", 915, 748),
              arrow("M707 713 V641", "admitted scope only", 720, 685, True),
              arrow("M1380 765 H1393 V364 H1380", dashed=True)]
    items += ['<text x="60" y="896" class="section">FOUR DESIGN DIRECTIONS</text>']
    items += ['<text x="1418" y="690" transform="rotate(-90 1418 690)" font-size="14" fill="#52665f">failed gate returns pending</text>']
    for x, title, body in [(60, "Framework", "Coordination and recovery"),
                           (405, "Methodology", "Gates, review and evaluation"),
                           (750, "Philosophy", "Assumptions and counterexamples"),
                           (1095, "Knowledge", "Sources and corrections")]:
        items.append(f'<text x="{x}" y="929" font-size="21" font-weight="700">{title}</text>')
        items.append(f'<text x="{x}" y="957" font-size="17" fill="#52665f">{body}</text>')
    items += ['<text x="60" y="1007" class="small">Solid arrows show request/data paths. Dashed arrows show conditional feedback. Cross-device synchronization remains unqualified.</text>', '</svg>']
    return "".join(items)


def inline(text):
    text = escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    def link(match):
        target = match[2]
        if target.startswith("../../"):
            target = PUBLIC + target[6:]
        return f'<a href="{target}">{match[1]}</a>'
    return re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", link, text)


def questions():
    source = (HERE / "technical-notes.md").read_text()
    rendered = []
    for section in source.split("### ")[1:]:
        title, body = section.split("\n", 1)
        body = body.split("\n## ", 1)[0].strip()
        paragraphs = "".join("<p>" + inline(p.replace("\n", " ")) + "</p>"
                             for p in body.split("\n\n") if p.strip())
        rendered.append("<details><summary>" + escape(title) + "</summary>" + paragraphs + "</details>")
    return "\n".join(rendered)


def capabilities():
    data = json.loads((HERE / "capability-catalog.json").read_text())
    parts = ['<h1>What ships, and when it is used.</h1><p class="lede">A source-generated inventory of the shared package. Client features, profile overrides and host plugins retain their own activation boundaries.</p>']
    for title, key in (("Skills", "skills"), ("MCP tools", "mcp_tools")):
        parts.append(f'<details><summary>{len(data[key])} {title.lower()}</summary><table><thead><tr><th>Name</th><th>Purpose</th></tr></thead><tbody>')
        for row in data[key]:
            exposure = ' <span class="pill">opt-in</span>' if row.get("exposure") == "opt-in" else ""
            parts.append('<tr><td><code>' + escape(row["name"]) + '</code>' + exposure + '</td><td>'
                         + escape(row["description"]) + '</td></tr>')
        parts.append('</tbody></table></details>')
    for title, key in (("Templates", "templates"), ("Reusable prompts", "prompts"),
                       ("Public CLI commands", "cli"), ("Routing tiers", "routing_tiers"),
                       ("Internal lifecycle hooks", "internal_hooks")):
        parts.append(f'<details><summary>{len(data[key])} {title.lower()}</summary><p>'
                     + ' · '.join('<code>' + escape(name) + '</code>' for name in data[key])
                     + '</p></details>')
    parts.append('<details><summary>4 task presets</summary>')
    for name, row in data["presets"].items():
        parts.append('<h3>' + escape(name) + '</h3><p>' + escape(row["output_contract"]) + '</p>')
    parts.append('</details><details><summary>9 adapters and their limitations</summary>')
    for name, values in data["adapters"].items():
        limits = [key + ' — ' + value.removeprefix('no: ') for key, value in values.items() if value != "yes"]
        body = '. '.join(limits) if limits else 'Declared package integration surfaces are available. Native behavior requires separate verification.'
        parts.append('<h3>' + escape(name) + '</h3><p>' + escape(body) + '</p>')
    parts.append('</details><details><summary>' + str(len(data['optional_editor_extensions'])) + ' optional editor extensions</summary>')
    for row in data['optional_editor_extensions']:
        parts.append('<h3>' + escape(row['id']) + '</h3><p>' + escape(row['why']) + '</p>')
    parts.append('</details><div class="callout caution"><strong>Activation and evidence</strong><p>run_checks, check_guard, memory_snapshot and skill_nudge ship disabled. Automatic routing progression is a configured candidate. Generated-procedure adoption remains held. External browser, email, GitHub and media tools depend on the host or explicit integrations.</p></div><p><a href="capability-catalog.md">Full catalogue</a> · <a href="capability-catalog.json">Machine-readable inventory</a></p>')
    return "".join(parts)


def main():
    proof = json.loads((HERE / "recorded-demo-proof.json").read_text())
    validate_receipt(proof)
    require(proof.get("demo_sha256") == hashlib.sha256((HERE / "demo.py").read_bytes()).hexdigest(),
            "rehearsal belongs to different demo code")
    require(proof.get("commands_sha256") == hashlib.sha256((HERE / "recorded-commands.json").read_bytes()).hexdigest(),
            "command log belongs to a different rehearsal")
    events = json.loads((HERE / "recorded-commands.json").read_text())
    expected = [("status", 0), ("task", 0), ("gate", 1), ("task", 0), ("task", 0),
                ("task", 2), ("task", 0), ("gate", 0), ("task", 0)]
    require(len(events) == len(expected), "recorded command sequence changed")
    for event, (action, code) in zip(events, expected):
        require(event.get("argv", [])[3:4] == [action] and event.get("exit") == code,
                "recorded command sequence or outcome changed")
    require("FAILED (failures=2)" in events[2]["stderr"]
            and "task version changed" in events[5]["stderr"]
            and "\nOK\n" in events[7]["stderr"], "recorded failure, conflict or pass evidence missing")
    svg = architecture()
    (HERE / "architecture.svg").write_text(svg)
    labels = {1: "Publish the task", 2: "The broken implementation fails", 3: "Record the failure",
              5: "Reject an outdated writer", 7: "The same gate passes after the fix",
              8: "Publish the verified next action"}
    replay = [{"title": labels[i], "command": " ".join(row["argv"]),
               "exit": row["exit"], "output": row["stdout"] + row["stderr"]}
              for i, row in enumerate(events) if i in labels]
    template = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Harness · Interview guide</title>
<style>
:root{--ink:#183b35;--muted:#52645f;--paper:#f5f6ef;--line:#cbd5ca;--accent:#17685d;--amber:#82520c}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.6 "Geist","Arial",sans-serif}
header,main{max-width:1280px;margin:auto;padding:24px 32px}header{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);gap:18px}
header strong{font-size:18px}header span{color:var(--muted);font-size:14px}nav{display:flex;gap:5px;flex-wrap:wrap}button{font:inherit;cursor:pointer;border:1px solid var(--line);color:var(--ink);background:transparent;border-radius:5px;padding:9px 15px}button[aria-selected=true]{background:var(--ink);color:white;border-color:var(--ink)}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #c47828;outline-offset:3px}
h1{font-size:38px;line-height:1.15;letter-spacing:-1px;margin:22px 0 16px;max-width:940px}h2{font-size:26px;line-height:1.3;margin:26px 0 14px}h3{font-size:20px}p{max-width:920px;margin:12px 0}a{color:#17685d;text-underline-offset:3px}.lede{color:var(--muted);font-size:19px;max-width:940px}.diagram{margin:24px 0;background:#f4f7f3;border:1px solid var(--line);border-radius:8px}.diagram svg{display:block;width:100%;height:auto}.figure-links{display:flex;gap:22px;font-size:15px}.two{display:grid;grid-template-columns:1fr 1fr;gap:32px;margin:24px 0}.callout{border-left:4px solid var(--accent);padding:8px 20px;background:#e9eee5}.caution{border-left-color:#b67a2e;background:#fbf1dd}code,pre{font-family:"IBM Plex Mono",Menlo,monospace;font-size:14px}code{background:#e6ebe1;padding:2px 5px;border-radius:3px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#193b35;color:#f4f7f3;padding:22px;border-radius:6px;line-height:1.8}pre code{background:transparent;color:inherit;padding:0}table{border-collapse:collapse;width:100%;margin:24px 0;text-align:left}th,td{padding:14px 12px;border-bottom:1px solid var(--line);vertical-align:top}th{font-size:14px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}td:first-child{font-weight:600}.metric{font-size:40px;font-weight:650;letter-spacing:-1px}.label{font-size:15px;color:var(--muted)}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:24px 0;margin:26px 0}.metrics p{margin:0}.tab[hidden]{display:none}details{border-bottom:1px solid var(--line);padding:16px 0}summary{cursor:pointer;font-size:19px;font-weight:600;padding-right:20px}details p{font-size:16px}ol{padding-left:24px}li{margin:12px 0}.small{font-size:14px;color:var(--muted)}footer{border-top:1px solid var(--line);margin-top:32px;padding:20px 0;color:var(--muted);font-size:14px}.raw{max-height:380px;overflow:auto}.steps td:nth-child(1){width:110px}.pill{font-size:13px;border:1px solid var(--line);padding:3px 9px;border-radius:20px}
@media(max-width:750px){header{align-items:flex-start;flex-direction:column}header,main{padding:18px}h1{font-size:30px}.two,.metrics{grid-template-columns:1fr}.diagram{overflow:auto}.diagram svg{min-width:900px}th,td{padding:10px 6px;font-size:15px}}
@media print{header nav,button,.no-print{display:none}.tab[hidden]{display:block}.tab{page-break-before:always}.tab:first-of-type{page-break-before:auto}header,main{padding:0}h1{font-size:28px}.diagram{break-inside:avoid}details{break-inside:avoid}body{font-size:12px}summary{font-size:14px}details p{font-size:12px}}
</style></head><body>
<header><div><strong>Agent Harness</strong><br><span>Interview companion · 3.0.0rc2 · 13 November 2026</span></div><nav aria-label="Presentation sections" role="tablist">
<button role="tab" aria-selected="true" aria-controls="overview" id="tab-overview" data-tab="overview">Architecture</button><button role="tab" aria-selected="false" aria-controls="demo" id="tab-demo" data-tab="demo">Run the demo</button><button role="tab" aria-selected="false" aria-controls="capabilities" id="tab-capabilities" data-tab="capabilities">Capabilities</button><button role="tab" aria-selected="false" aria-controls="evidence" id="tab-evidence" data-tab="evidence">Evidence</button><button role="tab" aria-selected="false" aria-controls="questions" id="tab-questions" data-tab="questions">Technical Q&amp;A</button></nav></header>
<main>
<section class="tab" id="overview" role="tabpanel" aria-labelledby="tab-overview"><h1>Work survives the conversation.</h1><p class="lede">A local control layer gives independent AI sessions shared task state, source-backed context and executable completion checks.</p><div class="diagram">{{SVG}}</div>
<div class="figure-links"><a href="architecture.svg">Open full-size diagram</a><a href="architecture.pdf">Printable architecture</a><a href="architecture.mmd">Mermaid source</a></div>
<div class="two"><div><h2>Explain one request</h2><p>A client connects. Its MCP process selects the current project board and relevant sources. Work proceeds through the graph where dependencies justify it. Guarded commands produce gate evidence. The next session reads the saved state.</p></div><div><h2>Explain the boundary</h2><p>The board coordinates. The graph settles completion. Memory supplies evidence. The model still reasons inside its native client. Each host has a local store; verified cross-device synchronization remains open.</p></div></div>
<div class="callout"><strong>Your opening</strong><p>“I developed a local-first harness for AI-assisted work. It preserves project state across sessions and checks completion with executable gates. My focus is recovery, traceable memory and measured efficiency. I can show the actual failure-and-recovery path, then explain what the evaluation established.”</p></div></section>

<section class="tab" id="demo" role="tabpanel" aria-labelledby="tab-demo" hidden><h1>Five minutes. One boundary bug.</h1><p class="lede">The free-shipping threshold is 50. A tiny implementation charges 5 at every subtotal. Three fixed tests cover 49, 50 and 80.</p><pre><code>python3 demo.py --output demo-run</code></pre><p>Run from this pack's folder. Python 3.9+, Git and an existing harness installation are required. A different installation can be selected with <code>--runtime /path/to/agent-harness</code>. Existing output folders are refused.</p>
<table class="steps"><thead><tr><th>Time</th><th>Show</th><th>Say</th></tr></thead><tbody>
<tr><td>0:00–0:45</td><td>Architecture and acceptance rule</td><td>“Free shipping starts at 50. The test command defines success.”</td></tr>
<tr><td>0:45–1:30</td><td>Run the demo. Open reader-a.txt.</td><td>“This fresh MCP process received the saved task during initialization.”</td></tr>
<tr><td>1:30–2:30</td><td>commands.json and reader-b.txt</td><td>“The first gate failed. A different process recovered the failure and the next action. An old-version writer was rejected.”</td></tr>
<tr><td>2:30–3:30</td><td>project/feature.py, test_feature.py and plan/shipping.md</td><td>“The prepared fix passed the original tests. Their hash stayed the same.”</td></tr>
<tr><td>3:30–4:15</td><td>reader-b-update.txt and demo-proof.json</td><td>“The connected reader received the changed state once. Its next unchanged boundary added zero board bytes.”</td></tr>
<tr><td>4:15–5:00</td><td>Evidence tab</td><td>“Model quality is a separate evaluation. Here is the bounded native comparison and a learning experiment that remained held.”</td></tr>
</tbody></table>
<div class="callout caution"><strong>What this live run establishes</strong><p>Real installed CLI, gate and MCP-process behavior. The fix is scripted and the run uses zero model calls. A real model's interpretation and compliance require their own native evaluation.</p></div>
<details><summary>Optional native-model follow-up · setup remains NOT_RUN</summary><p>Create a fresh temporary MCP connection with working directory <code>demo-run/project</code>, <code>HARNESS_HOME</code> set to <code>demo-run/home/harness</code>, and <code>PYTHONPATH</code> pointing to the existing runtime's lib directory. Resolve absolute paths and keep the normal connection intact. Then ask the model to inspect the board and linked gate evidence. Record the answer separately. This uses included account quota and requires client-specific configuration.</p></details>
<h2>Replay the observed CLI output</h2><p class="small">Saved rehearsal using the installed runtime. These controls replay recorded evidence. Run the Python command for a fresh demonstration.</p><h3 id="replay-title"></h3><p id="replay-exit"></p><pre class="raw" id="replay-output"></pre><div><button id="previous">Previous step</button> <button id="next">Next step</button></div>
<details><summary>Inspect the recorded receipt</summary><pre class="raw" id="receipt"></pre></details></section>

<section class="tab" id="capabilities" role="tabpanel" aria-labelledby="tab-capabilities" hidden>{{CAPABILITIES}}</section>
<section class="tab" id="evidence" role="tabpanel" aria-labelledby="tab-evidence" hidden><h1>Separate mechanics from outcomes.</h1><p class="lede">Deterministic controls test coordination and failure handling. Native paired trials measure the model-facing effect.</p>
<div class="metrics"><div><div class="metric">10.68%</div><p class="label">fewer observed tokens<br>4 paired authored memory tasks</p></div><div><div class="metric">4/4</div><p class="label">correct answers in each arm<br>same model, effort, facts and requirements</p></div><div><div class="metric">3,021</div><p class="label">passed in the release regression run<br>2 skipped · 2 expected failures</p></div></div>
<table><thead><tr><th>Comparison</th><th>Retained history</th><th>Current memory</th></tr></thead><tbody><tr><td>Observed input + output tokens</td><td>111,825</td><td>99,886</td></tr><tr><td>Correct answers</td><td>4/4</td><td>4/4</td></tr><tr><td>Memory-update model calls</td><td colspan="2">0</td></tr></tbody></table>
<p>Cached input is included. The saving applies to the measured packets. Four authored pairs leave general coding benefit, durable speed gains and net whole-project savings unqualified.</p>
<div class="two"><div class="callout"><strong>Operational evidence</strong><p>Candidate and merged-main Linux Python 3.9/3.12 tests and lint passed. Mac Studio and the research account passed installed readback. The live demo binds the installed gate engine's hash.</p></div><div class="callout caution"><strong>A learning candidate was held</strong><p>Generated procedures cost 172,569 candidate-charged tokens against a 48,969-token baseline. Adoption remained held. Full reasoning-guide treatment also remained unadopted after +3.38% tokens and a response-limit failure.</p></div></div>
<p><strong>Open qualification</strong> — MacBook installation, universal client/model compliance, cross-device memory synchronization, learner transfer and comparisons with human teams or other harnesses.</p>
<p><a href="https://github.com/oscar-chw/agent-harness/blob/main/docs/v3/qualification-20261113.md">Published study and limitations</a> · <a href="https://github.com/oscar-chw/agent-harness/releases/tag/v3.0.0rc2">Versioned release</a></p></section>

<section class="tab" id="questions" role="tabpanel" aria-labelledby="tab-questions" hidden><h1>Explain the mechanism. Name the limit.</h1><p class="lede">Start with the purpose, trace one concrete input, then explain the tradeoff. Expand a question for implementation references.</p>
<div class="callout"><strong>Version conflict example</strong><p>Two writers read task version 3. Writer A commits version 4 inside the SQLite transaction. Writer B still expects 3, so its update is rejected. It must read the new state before deciding what to do.</p></div>
{{QUESTIONS}}
<h2>Three things to rehearse without AI</h2><ol><li>Point to every arrow in the architecture and explain what crosses it.</li><li>Change the shipping threshold to 60 and name which tests should fail before editing them.</li><li>Explain why a passing test, a delivered STOP message and a current source hash each establish different facts.</li></ol></section>
<footer>Prepared from the v3.0.0rc2 implementation and dated qualification evidence. The diagram shows current mechanisms and conditional paths. Technical citations are pinned to the published candidate.</footer>
</main><script>
const proof={{PROOF}};
const replay={{REPLAY}};let replayIndex=0;
document.getElementById('receipt').textContent=JSON.stringify(proof,null,2);
function showReplay(){const row=replay[replayIndex];document.getElementById('replay-title').textContent=(replayIndex+1)+' / '+replay.length+' · '+row.title;document.getElementById('replay-exit').textContent='Observed exit code '+row.exit;document.getElementById('replay-output').textContent='$ '+row.command+'\n\n'+row.output;document.getElementById('previous').disabled=replayIndex===0;document.getElementById('next').disabled=replayIndex===replay.length-1}
document.getElementById('previous').addEventListener('click',()=>{replayIndex--;showReplay()});document.getElementById('next').addEventListener('click',()=>{replayIndex++;showReplay()});showReplay();
function selectTab(id){document.querySelectorAll('.tab').forEach(s=>s.hidden=s.id!==id);document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===id)));history.replaceState(null,'','#'+id);window.scrollTo(0,0)}
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>selectTab(b.dataset.tab)));
const first=location.hash.slice(1);if(['overview','demo','capabilities','evidence','questions'].includes(first))selectTab(first);
document.querySelector('nav').addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight'].includes(e.key))return;const b=[...document.querySelectorAll('[data-tab]')];const i=b.indexOf(document.activeElement);if(i<0)return;e.preventDefault();const n=(i+(e.key==='ArrowRight'?1:-1)+b.length)%b.length;selectTab(b[n].dataset.tab);b[n].focus()});
</script></body></html>'''
    inline_svg = svg.replace('height="1040" viewBox="0 0 1440 1040"',
                             'height="945" viewBox="0 95 1440 945"')
    document = template.replace("{{SVG}}", inline_svg).replace("{{QUESTIONS}}", questions())
    document = document.replace("{{CAPABILITIES}}", capabilities())
    document = document.replace("{{PROOF}}", json.dumps(proof).replace("<", "\\u003c"))
    document = document.replace("{{REPLAY}}", json.dumps(replay).replace("<", "\\u003c"))
    (HERE / "guide.html").write_text(document)
    print("Built architecture.svg and offline guide.html")


if __name__ == "__main__":
    main()
