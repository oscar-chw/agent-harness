"""Generate the shipped capability inventory from source, or check it for drift."""
import argparse
import json
from pathlib import Path
import posixpath
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def inventory():
    from agent_harness import __version__
    from agent_harness.adapters import _REGISTRY, names
    from agent_harness.cli import build_parser
    from agent_harness.matrix import matrix
    from agent_harness.mcp.checks import OFF_BY_DEFAULT
    from agent_harness.mcp.server import TOOLS
    from agent_harness.installer import load_toml

    skills = []
    for file in sorted((ROOT / "content/skills").glob("*/SKILL.md")):
        description = re.search(r"^description: (.+)$", file.read_text(), re.M)
        if description is None:
            raise ValueError("skill description missing " + file.parent.name)
        skills.append({"name": file.parent.name, "description": description[1],
                       "path": file.relative_to(ROOT).as_posix()})
    parser = build_parser()
    commands = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))
    available = names()
    if set(available) != {name for name, _, _ in _REGISTRY}:
        raise ValueError("an adapter failed to load")
    presets = json.loads((ROOT / "content/presets/catalog.json").read_text())
    return {"schema": "harness.capability-catalog/v1", "package_version": __version__,
            "skills": skills,
            "mcp_tools": [{"name": tool["name"], "description": tool["description"],
                           "exposure": "opt-in" if tool["name"] in OFF_BY_DEFAULT else "default"}
                          for tool in TOOLS],
            "default_off_features": sorted(OFF_BY_DEFAULT),
            "cli": [name for name in commands.choices if not name.startswith("_")],
            "internal_hooks": [name for name in commands.choices if name.startswith("_")],
            "templates": [p.name for p in sorted((ROOT / "content/templates").iterdir()) if p.is_file()],
            "prompts": [p.name for p in sorted((ROOT / "content/prompts").iterdir()) if p.is_file()],
            "presets": presets["presets"], "adapters": matrix(available),
            "routing_tiers": list(load_toml((ROOT / "content/routing.toml").read_text())["tiers"]),
            "optional_editor_extensions": [
                {key: row[key] for key in ("id", "why", "targets", "where")}
                for row in load_toml((ROOT / "content/extensions.toml").read_text())["extension"]],
            "model_family_roles": load_toml((ROOT / "content/discovery.toml").read_text())["family"]}


def markdown(data):
    rows = ["# Shipped capability catalogue", "",
            "Generated from package source. Run `python3 scripts/build_capability_catalog.py --check` to detect drift.",
            "The JSON companion provides the same inventory for tooling.", "",
            "For mechanisms and worked examples, read the [four walkthroughs](walkthrough/README.md).", "",
            "## What belongs where", "",
            "| Layer | Purpose | Activation boundary |", "|---|---|---|",
            "| Rules and skills | Guide task framing, implementation, debugging and review | Client loads installed guidance; model compliance needs behavioral checks |",
            "| MCP tools | Read/write scoped memory, documents and task checkpoints | Registered MCP connection; disabled flags and shell capability apply |",
            "| Work graph | Dependency scheduling, claims, gate execution and recovery | Plan CLI or exposed plan tool; a passing gate has its declared scope |",
            "| Guard and native controls | Screen commands and retain permission boundaries | Guard hooks exist for supported clients; native approvals and OS rights remain separate |",
            "| Templates and presets | Start a task, source record, handoff or bounded workflow | Selected for the task; templates supply structure |",
            "| Learning lifecycle | Draft, evaluate, correct or withdraw a reusable method | Adoption requires independently checked outcomes and complete measured cost |",
            "| Knowledge sources | Supply domain evidence and examples | Profile-selected accessible documents, retained revisions and scoped retrieval |", "",
            "## Skills", "", "| Skill | Purpose |", "|---|---|"]
    for item in data["skills"]:
        rows.append(f"| [{item['name']}](../{item['path']}) | {item['description']} |")
    rows += ["", "## MCP tools", "",
             "Default exposure assumes an enabled MCP connection. `HARNESS_DISABLE` overrides enabling flags.",
             "Shell-less connections withhold command-executing tools. Delivery and model use have separate evidence.", "",
             "| Tool | Purpose | Exposure |", "|---|---|---|"]
    for tool in data["mcp_tools"]:
        rows.append(f"| `{tool['name']}` | {tool['description'].replace('|', '/')} | {tool['exposure']} |")
    rows += ["", "Additional default-off features are `check_guard`, `memory_snapshot` and `skill_nudge`.",
             "`check_guard` checks test changes. The command guard is a distinct control.", "",
             "## CLI commands", "", "Use `harness COMMAND --help` for exact options.", "",
             " · ".join("`" + name + "`" for name in data["cli"]), "",
             "The separate `plan` CLI provides graph operations including new, context, ready, claim, gate, status and run.", "",
             "Internal lifecycle entrypoints are client integration surfaces.", "",
             " · ".join("`" + name + "`" for name in data["internal_hooks"]), "",
             "## Templates and reusable prompts", "",
             "Templates are stored under `content/templates`.", "",
             " · ".join(f"[{name}](../content/templates/{name})" for name in data["templates"]), "",
             "Reusable prompts are stored under `content/prompts`.", "",
             " · ".join(f"[{name}](../content/prompts/{name})" for name in data["prompts"]), "",
             "## Task presets", "", "| Preset | Output contract |", "|---|---|"]
    for name, value in data["presets"].items():
        rows.append(f"| `{name}` | {value['output_contract']} |")
    rows += ["", "## Models, extensions and external tools", "",
             "Routing tiers are `quick`, `standard`, `deep` and `review`. `content/routing.toml` binds supported model/effort pairs from the account configuration. Advisory automatic progression ships disabled until configured and qualified.",
             "`content/extensions.toml` contains curated optional editor extensions. `harness discover` supplies extension/plugin/MCP discovery and vetting. Installation depends on exact approval, supported pin/readback behavior and the client's installation capability. A catalogue listing does not establish installed or current compatibility.",
             "Browser automation, GitHub/email connectors, PDF tooling and other app-provided tools are supplied by their host or explicit integrations. They are outside this package inventory. Profile-selected skills may replace or extend shipped guidance.", "",
             "### Optional editor extension catalogue", "",
             "These are curated source entries. Install only through supported editor tooling after reviewing the proposed list. Publisher metadata and compatibility require current verification.", "",
             "| Extension | Purpose | Targets | Placement |", "|---|---|---|---|"]
    for row in data["optional_editor_extensions"]:
        rows.append(f"| `{row['id']}` | {row['why']} | {', '.join(row['targets'])} | {row['where']} |")
    rows += ["", "### Model-family policy", "",
             "These roles are declared task hypotheses. Account visibility, supported effort and independent outcomes constrain use. They carry no comparative benchmark claim.", "",
             "| Family | Configured model | Effort | Intended role |", "|---|---|---|---|"]
    for name, row in data["model_family_roles"].items():
        rows.append(f"| {name} | `{row['model']}` | {row['effort']} | {row['role']} |")
    rows += ["",
             "## Declared adapter support", "",
             "This table comes from `matrix.py`. It describes integration surfaces; native end-to-end verification is client-specific. Use `harness status --matrix` for reasons and current selection.", "",
             "| Adapter | Guard | Plan | Memory | Review | Run | Discover | Capture | Improve |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, values in data["adapters"].items():
        rows.append("| " + name + " | " + " | ".join("available" if value == "yes" else "limited"
                                                     for value in values.values()) + " |")
    rows += ["", "The JSON companion retains each limitation's reason. The `agents-md` adapter exports rules only. A native guard hook is installed for Claude Code and Kimi Code; Codex retains its own native sandbox and approvals.", "",
             "## Memory and knowledge boundaries", "",
             "The operational board stores task state. Project memory retains source-linked revisions. Facts and lessons have scoped stores. Search indexes are derived views. Profile `kb_paths` selects document sources, and session search handles explicitly supported local history formats. A useful handoff names evidence and the next action.",
             "Domain coverage depends on the supplied sources and their freshness. This package's mechanism and methodology documents are distinct from a deployment's personal or organizational knowledge vault. Cross-device synchronization requires separate configuration and verification.", "",
             "## Development and GitHub delivery", "",
             "The [delivery playbook](DEVELOPMENT.md) covers task/issue scope, branches, PR evidence, CI/CD, reviews, releases and stack-specific check selection. It includes small task/PR/release draft examples. Those documented examples supplement the seven shipped file templates. Repository settings and observed checks establish enforcement.", "",
             "## Current evidence", "",
             "The release candidate's [qualification report](v3/qualification-20261113.md) records the four-pair memory result, retained failed learning trials and remaining gaps. The [interview pack](../examples/interview/README.md) exercises installed CLI/MCP processes with disposable data and zero model calls. Generated-procedure adoption remains held after token regression.", ""]
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = inventory()
    encoded = json.dumps(data, indent=2, sort_keys=True) + "\n"
    document = markdown(data)
    def offline_link(match):
        label, target = match.groups()
        if target.startswith(("https://", "http://", "#")):
            return match[0]
        target = posixpath.normpath(posixpath.join("docs", target))
        return "[" + label + "](https://github.com/oscar-chw/agent-harness/blob/main/" + target + ")"
    offline = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", offline_link, document)
    outputs = {ROOT / "docs/CAPABILITIES.json": encoded, ROOT / "docs/CAPABILITIES.md": document,
               ROOT / "examples/interview/capability-catalog.json": encoded,
               ROOT / "examples/interview/capability-catalog.md": offline}
    for path, expected in outputs.items():
        if args.check:
            if not path.is_file() or path.read_text() != expected:
                raise SystemExit("catalogue drift " + str(path.relative_to(ROOT)))
        else:
            path.write_text(expected)
    print("PASS capability catalogue" if args.check else "Generated capability catalogue")


if __name__ == "__main__":
    main()
