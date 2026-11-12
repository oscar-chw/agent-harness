"""Check local projections; domain/native selection outcomes remain NOT_RUN.

This informs the integration owner, never closes a parent gate or dispatches a
worker. Model names, home/cache and enabled route policy are disposable fixtures.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile

from agent_harness import routing

import replay_cases as methods


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCENARIOS = {"direct-no-tool", "local-sql", "uncertain-research", "independent-branches",
             "failed-gate", "stale-recipe", "missing-tool", "harmful-delegation"}
CONTEXT = "a" * 64
ARTIFACT = "b" * 64
SOURCE_PATHS = ["src/agent_harness/routing.py", "content/routing.toml",
                "src/agent_harness/method_control.py", "src/agent_harness/launch.py",
                "docs/v2/methodology/replay_cases.py",
                "docs/v2/methodology/replay_selection_cases.py"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in SOURCE_PATHS}


def validate(pack):
    require(pack.get("schema") == "harness.selection-cases/v1", "unknown selection schema")
    require(pack.get("split") == "development" and pack.get("origin") == "authored_synthetic",
            "visible synthetic development cases are required")
    require(pack.get("overall_domain_acceptance") == "NOT_RUN",
            "unsupported domain acceptance must remain NOT_RUN")
    cases = pack["cases"]
    require(len(cases) == len(SCENARIOS) and {c["id"] for c in cases} == SCENARIOS,
            "missing, duplicate or unknown selection scenario")
    ids = set()
    for case in cases:
        require(bool(case["failure"].strip()), f"{case['id']}: missing named failure")
        require(len(case["variants"]) == 2, f"{case['id']}: control and counterexample required")
        for variant in case["variants"]:
            identity = variant["id"]
            require(identity not in ids, "duplicate variant identity")
            ids.add(identity)
            require(bool(variant["task"].strip()) and bool(variant["changed_evidence"].strip())
                    and bool(variant["frozen_outcome"]), f"{identity}: missing outcome contract")
            require(set(variant["unsupported_checks"]) <= set(pack["unsupported_dimensions"])
                    and {"native_adoption", "efficiency"} <= set(variant["unsupported_checks"]),
                    f"{identity}: unsupported outcome checks must be explicit")
            require(bool(variant["method_projection"]) and bool(variant["route_projection"]),
                    f"{identity}: absent supported projection")
    return cases


def route_projection(spec, home):
    inputs = spec["input"]
    codex = home / ".codex"
    codex.mkdir(parents=True)
    # Only this synthetic home is ever passed to routing; no account cache or
    # native config is inspected or changed by a projected DISPATCH result.
    models = [{"slug": "fixture-small", "visibility": "list", "priority": 1,
               "description": "fast fixture", "supported_reasoning_levels": [{"effort": "low"}]},
              {"slug": "fixture-general", "visibility": "list", "priority": 2,
               "description": "general fixture", "supported_reasoning_levels":
               [{"effort": "medium"}, {"effort": "high"}]}]
    (codex / "models_cache.json").write_text(json.dumps({"models": models}))
    require(type(inputs["enabled"]) is bool, "route fixture enabled must be a boolean")
    profile = {"routing": {"ceiling": "high", "tiers": {
        "quick": {"codex": "fixture-small", "effort": "low"},
        "standard": {"codex": "fixture-general", "effort": "medium"},
        "deep": {"codex": "fixture-general", "effort": "high"}},
        "progression": {"enabled": inputs["enabled"], "selector": "task",
                        "codex_steps": ["quick", "standard", "deep"]}}}
    state = {"schema": "harness.route-state/v1", "provider": "codex",
             "context_sha256": CONTEXT, "check_id": "selection-fixture-gate",
             "task": inputs["task"], "route_version": None, "attempts": [],
             "limits": {"max_attempts": 3, "max_total_tokens": 100,
                        "max_wall_seconds": 30, "max_tools": 5}}
    scenario = inputs["scenario"]
    require(scenario in {"initial", "stale_context", "missing_pair", "failed_gate", "current_pass"},
            "unknown route projection scenario")
    current = CONTEXT
    artifact = None
    if scenario == "stale_context":
        current = "c" * 64
    if scenario == "missing_pair":
        profile["routing"]["tiers"]["standard"]["codex"] = "fixture-unavailable"
    if scenario in {"failed_gate", "current_pass"}:
        first = routing.next_decision(ROOT / "content", home, state,
                                      current_context_sha256=CONTEXT, profile=profile)
        require(first["decision"] == "DISPATCH", "history fixture requires a valid initial route")
        state["route_version"] = first["route_version"]
        state["attempts"] = [{"tier": first["tier"], "route_version": first["route_version"],
                              "context_sha256": CONTEXT, "artifact_sha256": ARTIFACT,
                              "usage": {"input_tokens": 18, "output_tokens": 2,
                                        "tool_calls": 1, "wall_seconds": 2},
                              "gate": {"schema": "harness.gate-result/v1",
                                       "status": "PASS" if scenario == "current_pass" else "FAIL",
                                       "check_id": state["check_id"], "artifact_sha256": ARTIFACT}}]
        if scenario == "current_pass":
            artifact = ARTIFACT
    result = routing.next_decision(ROOT / "content", home, state,
                                   current_context_sha256=current,
                                   current_artifact_sha256=artifact,
                                   profile=profile if inputs["enabled"] else None)
    observed = {key: result[key] for key in ("decision", "reason", "tier")}
    require(observed == spec["expected"], f"route projection mismatch: {observed}")
    return {"surface": "routing.next_decision", "status": "PASS", "observed": observed,
            "native_dispatch": "NOT_RUN", "fixture_only": True}


def sql_projection(spec):
    # The oracle uses exactly this visible bounded fixture. No pack-provided SQL,
    # filesystem database, connector, live account or production rows are opened.
    with sqlite3.connect(":memory:") as db:
        db.executescript("CREATE TABLE orders(id INTEGER, total INTEGER);"
                         "CREATE TABLE items(order_id INTEGER);")
        db.executemany("INSERT INTO orders VALUES (?, ?)", [(1, 100), (2, 50)])
        db.executemany("INSERT INTO items VALUES (?)", [(1,), (1,), (2,)])
        queries = {"revenue": "SELECT SUM(total) FROM orders",
                   "line_items": "SELECT COUNT(*) FROM items"}
        require(spec["query"] in queries, "unknown SQL projection")
        value = db.execute(queries[spec["query"]]).fetchone()[0]
        require(value == spec["expected"], f"SQL projection mismatch: {value}")
        result = {"surface": "sqlite3 visible fixture", "status": "PASS", "observed": value,
                  "native_tool_selection": "NOT_RUN"}
        if "invalid_join_total" in spec:
            joined = db.execute("SELECT SUM(total) FROM orders JOIN items ON id=order_id").fetchone()[0]
            require(joined == spec["invalid_join_total"] and joined != value,
                    "SQL fanout negative must disagree with the valid order-total oracle")
            result["invalid_fanout_result_rejected"] = joined
        return result


def evaluate_variant(variant, dimensions):
    with tempfile.TemporaryDirectory(prefix=".selection-replay-", dir=HERE) as temp:
        root = Path(temp)
        project = root / "project"
        project.mkdir()
        probe = {"id": variant["id"], **variant["method_projection"]}
        methods.replay(probe, project)
        supported = [{"surface": "method_control.decide", "status": "PASS",
                      "checked_expected": probe["expected"], "native_method_selection": "NOT_RUN"},
                     route_projection(variant["route_projection"], root / "home")]
        if "sql_projection" in variant:
            supported.append(sql_projection(variant["sql_projection"]))
    return {"id": variant["id"], "supported_projections": supported,
            "domain_outcome": "NOT_RUN", "unsupported": [
                {"check": name, "status": "NOT_RUN", "reason": dimensions[name]}
                for name in variant["unsupported_checks"]]}


def negative_controls(pack):
    cases = {case["id"]: case for case in pack["cases"]}
    mutations = []
    method = copy.deepcopy(cases["direct-no-tool"]["variants"][0])
    method["method_projection"]["expected"]["runtime_action"] = "PLAN"
    mutations.append(("invent-plan-for-direct", method, "got DIRECT, expected PLAN"))
    route = copy.deepcopy(cases["uncertain-research"]["variants"][0])
    route["route_projection"]["expected"]["tier"] = "quick"
    mutations.append(("underqualified-route-expectation", route, "route projection mismatch"))
    sql = copy.deepcopy(cases["local-sql"]["variants"][0])
    sql["sql_projection"]["expected"] = 250
    mutations.append(("accept-join-fanout-as-revenue", sql, "SQL projection mismatch"))
    results = []
    for name, variant, diagnostic in mutations:
        try:
            evaluate_variant(variant, pack["unsupported_dimensions"])
        except ValueError as error:
            require(diagnostic in str(error), f"{name}: mutant rejected for an unrelated reason")
        else:
            raise ValueError(f"{name}: false expected outcome survived")
        results.append({"mutation": name, "status": "REJECTED", "failure": diagnostic})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", nargs="?", type=Path, default=HERE / "selection-cases-20261103.json")
    parser.add_argument("--controls", action="store_true", help="also reject three false projected outcomes")
    parser.add_argument("--require-outcomes", action="store_true",
                        help="exit 2 when required domain/native outcomes remain NOT_RUN")
    args = parser.parse_args()
    before = hashes()
    raw = args.pack.read_bytes()
    pack = json.loads(raw)
    cases = validate(pack)
    results = [evaluate_variant(variant, pack["unsupported_dimensions"])
               for case in cases for variant in case["variants"]]
    controls = negative_controls(pack) if args.controls else "NOT_RUN"
    require(hashes() == before, "source changed during projection replay; results require a fresh run")
    print(json.dumps({"schema": "harness.selection-replay/v1",
                      "status": "NOT_RUN" if args.require_outcomes else "SUPPORTED_PROJECTIONS_PASS",
                      "claim_class": "supported_local_projections_only", "authority": "INFORMS root",
                      "overall_domain_acceptance": "NOT_RUN", "scenarios": len(cases),
                      "variants": len(results), "supported_projections": sum(
                          len(r["supported_projections"]) for r in results),
                      "pack_sha256": hashlib.sha256(raw).hexdigest(), "source_sha256": before,
                      "controls": controls, "results": results,
                      "not_proven": ["skill fitness", "MCP selection", "useful worker count",
                                     "native adoption", "held-out quality", "total-token benefit"]},
                     sort_keys=True))
    return 2 if args.require_outcomes else 0


if __name__ == "__main__":
    raise SystemExit(main())
