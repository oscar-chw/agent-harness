"""Render the architecture proposal as a vector PDF. No network, models or config writes."""
from pathlib import Path
import math

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas

HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parent / "harness-system-diagrams.pdf"
W, H = landscape(A4)
INK = HexColor("#183347")
MUTED = HexColor("#526575")
LINE = HexColor("#8095A5")
PALETTE = {
    "T": ("#F0F5FB", "#326CAA"),
    "E": ("#EEF5F3", "#28746A"),
    "S": ("#E6F3EB", "#28754F"),
    "H": ("#FBF0E8", "#9B542A"),
}


def node(key, x, y, width, height, title, body="", status="T"):
    return dict(key=key, x=x, y=y, w=width, h=height, title=title, body=body, status=status)


def edge(a, b, label="", via=None, start="bottom", finish="top", label_pos=None):
    return dict(a=a, b=b, label=label, via=via or [], start=start, finish=finish, label_pos=label_pos)


def anchor(n, side):
    return {
        "top": (n["x"] + n["w"] / 2, n["y"]),
        "bottom": (n["x"] + n["w"] / 2, n["y"] + n["h"]),
        "left": (n["x"], n["y"] + n["h"] / 2),
        "right": (n["x"] + n["w"], n["y"] + n["h"] / 2),
    }[side]


def text(c, x, y, value, size=11, color=INK, bold=False):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.drawString(x, H-y-size, value)


def draw_node(c, n):
    fill, stroke = PALETTE[n["status"]]
    c.setFillColor(HexColor(fill)); c.setStrokeColor(HexColor(stroke)); c.setLineWidth(1)
    c.roundRect(n["x"], H-n["y"]-n["h"], n["w"], n["h"], 7, fill=1, stroke=1)
    titles = simpleSplit(n["title"], "Helvetica-Bold", 12, n["w"]-30)
    body = simpleSplit(n["body"], "Helvetica", 11, n["w"]-24)
    need = 12 + 15*len(titles) + (6 if body else 0) + 14*len(body) + 8
    if need > n["h"]:
        raise ValueError(f"Text does not fit node {n['key']}: {need} > {n['h']}")
    y = n["y"]+10
    for line in titles:
        text(c, n["x"]+12, y, line, 12, bold=True); y += 15
    y += 6 if body else 0
    for line in body:
        text(c, n["x"]+12, y, line); y += 14
    text(c, n["x"]+n["w"]-16, n["y"]+5, n["status"], 8, HexColor(stroke), True)


def draw_edge(c, e, nodes):
    pts = [anchor(nodes[e["a"]], e["start"]), *e["via"], anchor(nodes[e["b"]], e["finish"])]
    c.setStrokeColor(LINE); c.setFillColor(LINE); c.setLineWidth(1.05)
    path = c.beginPath(); path.moveTo(pts[0][0], H-pts[0][1])
    for x, y in pts[1:]: path.lineTo(x, H-y)
    c.drawPath(path)
    x, y = pts[-1]; px, py = pts[-2]
    angle = math.atan2(y-py, x-px)
    arrow = c.beginPath(); arrow.moveTo(x, H-y)
    for sign in (-1, 1):
        ax = x-7*math.cos(angle)+sign*3*math.sin(angle)
        ay = y-7*math.sin(angle)-sign*3*math.cos(angle)
        arrow.lineTo(ax, H-ay)
    arrow.close(); c.drawPath(arrow, fill=1, stroke=0)
    if e["label"]:
        first, last = pts[len(pts)//2-1:len(pts)//2+1]
        tx = (first[0]+last[0])/2+5; ty = (first[1]+last[1])/2-14
        if e["label_pos"]:
            tx, ty = e["label_pos"]
        width = c.stringWidth(e["label"], "Helvetica", 9)+6
        c.setFillColor(HexColor("#FFFFFF")); c.rect(tx-2, H-ty-12, width, 13, fill=1, stroke=0)
        text(c, tx, ty, e["label"], 9, MUTED)


PAGES = []


def page(title, subtitle, nodes, edges, note):
    PAGES.append(dict(title=title, subtitle=subtitle, nodes=nodes, edges=edges, note=note))


page("System hierarchy", "One shared local foundation; native clients keep their own capabilities and permissions.", [
    node("owner", 305, 72, 230, 57, "You: intended outcome", "Only meaningful decisions"),
    *[node(k, 36+i*198, 158, 178, 57, label, "Native adapter") for i, (k, label) in enumerate([
        ("claude", "Claude"), ("codex", "Codex"), ("copilot", "Copilot"), ("other", "Other clients")])],
    node("core", 208, 251, 426, 64, "Local control system", "Task contracts, policy, routing and coordination"),
    node("state", 36, 354, 242, 68, "Task and outcome state", "Ownership, revisions, receipts", "E"),
    node("memory", 300, 354, 242, 68, "Knowledge and memory", "Originals, scoped facts, indexes", "E"),
    node("execution", 564, 354, 242, 68, "Execution adapters", "Bounded workers and recovery"),
    node("quality", 36, 459, 242, 68, "Quality and review", "Task checks and integration", "E"),
    node("learning", 300, 459, 242, 68, "Learning and updates", "Evaluate, release, rollback"),
    node("ops", 564, 459, 242, 68, "Operations", "Diagnostics, quota, retention"),
], [
    *[edge("owner", k, via=[(420, 140), (125+i*198, 140)]) for i,k in enumerate(["claude","codex","copilot","other"])],
    *[edge(k,"core",via=[(125+i*198,234),(421,234)]) for i,k in enumerate(["claude","codex","copilot","other"])],
    *[edge("core", k, via=[(421,335),(x,335)]) for k,x in [("state",157),("memory",421),("execution",685)]],
    edge("state","quality"), edge("memory","learning"), edge("execution","ops"),
], "Connections show the target integration. E marks existing foundations, not fleet-wide qualification.")

page("Adaptive task workflow", "Choose an adequate path. A task does not have to visit every stage.", [
    node("goal", 292, 76, 258, 57, "Outcome and constraints", "Use current project context"),
    node("route", 292, 169, 258, 58, "Choose the execution path", "Risk, uncertainty, dependencies"),
    node("direct", 36, 273, 178, 72, "Direct answer", "Use supplied evidence"),
    node("bounded", 234, 273, 178, 72, "Bounded task", "Inspect, act, relevant check"),
    node("research", 432, 273, 178, 72, "Exploration", "Bounded research or probe"),
    node("rigorous", 630, 273, 178, 72, "Rigorous task", "Plan, isolate, recovery"),
    node("verify", 250, 393, 342, 62, "Verify the relevant outcome", "Evidence appropriate to the claim", "E"),
    node("deliver", 290, 494, 262, 40, "Deliver; save material outcomes"),
], [edge("goal","route"),
    *[edge("route",k,via=[(421,248),(125+i*198,248)]) for i,k in enumerate(["direct","bounded","research","rigorous"])],
    *[edge(k,"verify",via=[(125+i*198,369),(421,369)]) for i,k in enumerate(["direct","bounded","research","rigorous"])],
    edge("verify","deliver","pass"),
    edge("verify","route","failure: revisit",via=[(22,424),(22,198)],start="left",finish="left",label_pos=(40,373)),
], "A text answer need not run code tests. Required checks and authority boundaries remain in every path.")

page("Decision policy", "Complexity and rigor are independent. Short work can still have serious consequences.", [
    node("risk",36,100,220,68,"Consequences and authority","Reversibility; allowed actions"),
    node("uncertain",36,230,220,68,"Uncertainty","What missing fact can matter?"),
    node("coord",36,360,220,68,"Coordination needs","Dependencies and continuation"),
    node("select",310,218,218,95,"Task admission","Select the smallest adequate method"),
    node("thought",584,80,220,68,"Reasoning depth","How hard is the inference?"),
    node("evidence",584,191,220,68,"Evidence breadth","What needs verification?"),
    node("process",584,302,220,68,"Workflow machinery","Plan, checkpoint, workers?"),
    node("proof",584,413,220,68,"Verification strength","How strong must proof be?"),
], [
    edge("risk","select",via=[(280,134),(280,265)],start="right",finish="left"),
    edge("uncertain","select",start="right",finish="left"),
    edge("coord","select",via=[(280,394),(280,265)],start="right",finish="left"),
    *[edge("select",k,via=[(555,265),(555,y)],start="right",finish="left") for k,y in [("thought",114),("evidence",225),("process",336),("proof",447)]],
], "No mandatory routing-model call. Escalate on risk or evidence; stop when the required outcome is established.")

page("Guard decision and false positives", "Target policy: intentional actions have a real approval path; external restrictions remain explicit.", [
    node("action",288,74,266,58,"Proposed action","Arguments, targets, context"),
    node("classify",288,170,266,60,"Classify the actual effect","Policy layer and existing authority"),
    node("allow",36,280,178,72,"Authorized / low risk","Proceed within scope"),
    node("ask",234,280,178,72,"Approval required","Use a supported consumer"),
    node("ambiguous",432,280,178,72,"Uncertain scope","Resolve the specific gap"),
    node("deny",630,280,178,72,"Hard restriction","Explain blocking layer","H"),
    node("run",36,443,178,70,"Execute and verify","Recheck action scope"),
    node("pending",234,443,178,70,"Durable request","Resume after valid grant"),
    node("repair",450,443,340,70,"Suspected misfire: maintenance","Reproduce, repair, preserve negative controls","H"),
], [edge("action","classify"),
    *[edge("classify",k,via=[(421,254),(125+i*198,254)]) for i,k in enumerate(["allow","ask","ambiguous","deny"])],
    edge("allow","run"),edge("ask","pending"),
], "CURRENT source guard is binary allow/block. Literal-print false positives are repaired; approval integration is not qualified.")

page("Approval while you are away", "Acknowledged consent, native permission, resumed work and completion are different events.", [
    node("request",36,88,234,76,"1. Action proposal","Effect, scope, revisions, recovery"),
    node("owner",310,88,220,76,"2. Owner approval","Receive through a trusted channel"),
    node("grant",572,88,234,76,"3. Durable grant","Bind scope and validity"),
    node("native",572,242,234,76,"4. Native permission","Supported interface accepts grant"),
    node("worker",310,242,220,76,"5. Resume existing task","Lease and precondition checks"),
    node("result",36,242,234,76,"6. Persist outcome","Artifacts, check result, revision"),
    node("notice",36,418,234,76,"7. Result to owner","No duplicate approval question"),
    node("blocked",572,418,234,76,"Blocked after consent","State actual cause; no bypass","H"),
], [edge("request","owner",start="right",finish="left"),
    edge("owner","grant",start="right",finish="left"),edge("grant","native"),
    edge("native","worker",start="left",finish="right"),edge("worker","result",start="left",finish="right"),
    edge("result","notice"),edge("native","blocked","denied or unsupported"),
], "TARGET: test restart, duplicate delivery, changed targets, revocation and crash reconciliation. No live bridge is installed.")

page("Memory retrieval and source authority", "Retrieve only what can affect the task; history and generated summaries cannot grant authority.", [
    node("need",295,74,252,60,"Task and evidence need","A simple answer may stop here"),
    node("scope",295,169,252,60,"Resolve authorized scope","Project, source revision, privacy","E"),
    node("exact",36,272,234,72,"Exact / lexical lookup","Current sections and source spans","E"),
    node("semantic",304,272,234,72,"Semantic retrieval","Optional; needs local comparison"),
    node("relations",572,272,234,72,"Evidence graph query","Optional multi-source relations"),
    node("validate",245,390,352,68,"Check support and currency","Correction, withdrawal, stale or missing","E"),
    node("packet",245,491,352,42,"Small cited context packet / explicit UNKNOWN"),
], [edge("need","scope"),
    *[edge("scope",k,via=[(421,250),(x,250)]) for k,x in [("exact",153),("semantic",421),("relations",689)]],
    *[edge(k,"validate",via=[(x,367),(421,367)]) for k,x in [("exact",153),("semantic",421),("relations",689)]],
    edge("validate","packet"),
], "Originals and source receipts stay authoritative. Embeddings, summaries and graph views are rebuildable derivatives.")

page("Cross-session pickup without message relays", "Automatic structured outcomes replace user-written handoffs; offline clients catch up on the next read.", [
    node("writer",36,87,234,78,"Session A: material work","Result, artifacts, checks, blockers"),
    node("state",310,87,220,78,"Atomic outcome record","Task ID and acknowledged revision"),
    node("reader",572,87,234,78,"Session B: resume","Read compact dependency state"),
    node("check",572,252,234,78,"Revalidate before acting","Current inputs, owner and authority"),
    node("next",310,252,220,78,"Continue permitted work","Avoid duplicate effects"),
    node("publish",36,252,234,78,"Publish next outcome","Keep source and test references"),
    node("unknown",458,423,348,76,"Stale / disconnected / incomplete","Expose UNKNOWN; never invent task completion","H"),
    node("message",36,423,348,76,"Message only to activate or resolve","No repeated requests for recorded progress"),
], [edge("writer","state",start="right",finish="left"),edge("state","reader",start="right",finish="left"),
    edge("reader","check"),edge("check","next",start="left",finish="right"),
    edge("next","publish",start="left",finish="right"),edge("check","unknown","missing / stale"),
], "TARGET acceptance: a cold authorized session continues correctly without user recap or peer status messages.")

page("Learning, evaluation and safe updates", "Improve from trustworthy outcomes; discovery and candidate generation do not establish a benefit.", [
    node("observe",36,88,234,77,"Observe an outcome","Verified failure, repair or correction","E"),
    node("candidate",310,88,220,77,"Draft a scoped candidate","Skill, retrieval or workflow change","E"),
    node("eval",572,88,234,77,"Frozen independent evaluation","Baseline, held-out and negative cases"),
    node("hold",572,270,234,77,"Reject / hold failed candidate","Keep the failure evidence","H"),
    node("release",310,270,220,77,"Qualified promotion","Version and permitted scope"),
    node("canary",36,270,234,77,"Canary and real-use checks","Observe relevant regressions"),
    node("rollback",36,438,234,69,"Rollback on regression","Restore known revision"),
    node("stable",310,438,496,69,"Keep only demonstrated improvements","Quality >= baseline; aggregate model tokens <= baseline"),
], [edge("observe","candidate",start="right",finish="left"),edge("candidate","eval",start="right",finish="left"),
    edge("eval","hold","fails / unknown"),edge("eval","release","qualifies",via=[(689,205),(420,205)],finish="top",label_pos=(425,211)),
    edge("release","canary",start="left",finish="right"),edge("canary","rollback","regression"),
    edge("canary","stable","passes",via=[(286,309),(286,472)],start="right",finish="left"),
], "No candidate may edit its own evaluator or silently expand permissions. Broad automatic promotion remains unqualified.")


def main():
    c = Canvas(str(OUTPUT), pagesize=(W, H), pageCompression=1)
    c.setTitle("Harness system diagrams - target architecture and evidence boundaries")
    c.setAuthor("Agent harness project")
    for i, p in enumerate(PAGES, 1):
        text(c, 36, 17, "HARNESS / SYSTEM MAP", 9, MUTED, True)
        text(c, W-174, 17, "31 OCTOBER 2026", 9, MUTED)
        text(c, 36, 31, p["title"], 23, bold=True)
        text(c, 36, 57, p["subtitle"], 10, MUTED)
        nodes = {n["key"]: n for n in p["nodes"]}
        if len(nodes) != len(p["nodes"]):
            raise ValueError("Duplicate diagram identity")
        for n in nodes.values():
            if not (20 <= n["x"] < n["x"]+n["w"] <= W-20 and 70 <= n["y"] < n["y"]+n["h"] <= 538):
                raise ValueError("Diagram node outside content area: " + n["key"])
        for e in p["edges"]: draw_edge(c, e, nodes)
        for n in nodes.values(): draw_node(c, n)
        c.setStrokeColor(HexColor("#D6DFE5")); c.line(36, 50, W-36, 50)
        for j, line in enumerate(simpleSplit(p["note"], "Helvetica", 9, W-72)):
            text(c, 36, 549+j*11, line, 9, MUTED)
        text(c, 36, 579, "T target   E existing foundation   S source-tested repair   H held / unqualified", 8, MUTED)
        text(c, W-65, 579, f"{i} / {len(PAGES)}", 8, MUTED)
        c.showPage()
    c.save()
    print(f"RENDERED: {len(PAGES)} vector pages -> {OUTPUT.name}")


if __name__ == "__main__":
    main()
