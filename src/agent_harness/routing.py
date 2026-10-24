"""Model and effort routing: content/routing.toml resolved against what this account can use.

No model is named in code. The template names selectors (`smallest`, `fast`, `default`, ...); this module turns
them into a model per tool from what the tool reports (Codex: ~/.codex/models_cache.json, Claude Code: the
template's alias ladder) and lowers each effort to the template's ceiling and to what that model offers.

    resolve(content_dir, home, profile) -> {tier: {"when": str, "claude": {...}, "codex": {...}}}

Each tool entry is {"model": str or None, "effort": str, "why": str}; model None means "the tool's own default"
(nothing discovered, so nothing is pinned).
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
from typing import Dict, List, Optional

from . import installer as I

TEMPLATE = "routing.toml"
USER_FILE = "routing.toml"          # in ~/.agent-harness


def merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load(content: Path, home: Path, profile: Optional[dict]) -> dict:
    t = I.load_toml((content / TEMPLATE).read_text(encoding="utf-8"))
    t = merge(t, (profile or {}).get("routing") or {})
    user = home / ".agent-harness" / USER_FILE
    if user.is_file():
        t = merge(t, I.load_toml(user.read_text(encoding="utf-8")))
    return t


def lower_effort(want: str, offered: Optional[List[str]], ladder: List[str], ceiling: str) -> str:
    """`want`, lowered to the ceiling, then to the highest effort the model offers that is not above it."""
    rank = {e: i for i, e in enumerate(ladder)}
    cap = min(rank.get(want, rank.get("medium", 0)), rank.get(ceiling, len(ladder) - 1))
    if not offered:
        return ladder[cap]
    ok = [e for e in offered if e in rank and rank[e] <= cap]
    if ok:
        return max(ok, key=lambda e: rank[e])
    return min((e for e in offered if e in rank), key=lambda e: rank[e], default=ladder[cap])


def codex_models(home: Path, visible: List[str]) -> List[dict]:
    """The account's picker models, in picker order (priority), from Codex's own cache. [] if none."""
    p = home / ".codex" / "models_cache.json"
    try:
        models = json.loads(p.read_text(encoding="utf-8")).get("models") or []
    except (OSError, ValueError, AttributeError):
        return []
    out = [m for m in models if isinstance(m, dict) and m.get("slug") and m.get("visibility") in visible]
    return sorted(out, key=lambda m: (m.get("priority") is None, m.get("priority") or 0))


def codex_configured(home: Path) -> Optional[str]:
    p = home / ".codex" / "config.toml"
    try:
        v = I.load_toml(p.read_text(encoding="utf-8")).get("model")
    except (OSError, ValueError):
        return None
    return v if isinstance(v, str) and v else None


def pick_codex(sel: str, models: List[dict], configured: Optional[str], words: List[str]) -> (Optional[dict], str):
    """`default` is what Codex itself would run: the user's config.toml model, else NOTHING pinned. The model list
    holds only the picker's models; the account's actual default can be absent from it (2026-10-06: Codex ran
    gpt-5.6-sol, the list held only older ones, and "first in the picker" sent the deep tier to an older model)."""
    by_slug = {m["slug"]: m for m in models}
    default = (by_slug.get(configured) or {"slug": configured}) if configured else None
    dwhy = "your config.toml model" if configured else "Codex's own default (not pinned)"
    if sel == "fast":
        for m in models:
            if any(w in (m.get("description") or "").lower() for w in words):
                return m, f"fast: '{m.get('description')}'"
        return default, "fast: none described as fast, so " + dwhy
    if sel == "default":
        return default, "default: " + dwhy
    if sel in by_slug:                       # a profile or user may name a model they have
        return by_slug[sel], "named in an override"
    return default, f"'{sel}' is not in your model list, so " + dwhy


def pick_claude(sel: str, ladder: List[str]) -> (Optional[str], str):
    if sel == "inherit" or not ladder:
        return None, "the main conversation's model"
    idx = {"smallest": 0, "middle": (len(ladder) - 1) // 2, "largest": len(ladder) - 1}
    if sel in idx:
        return ladder[idx[sel]], f"{sel} of {'/'.join(ladder)}"
    return sel, "named in an override"


def resolve(content: Path, home: Path, profile: Optional[dict] = None) -> Dict[str, dict]:
    t = load(content, home, profile)
    ladder = list(t.get("efforts") or ["low", "medium", "high"])
    ceiling = t.get("ceiling") or "high"
    cx = t.get("codex") or {}
    models = codex_models(home, list(cx.get("visible") or ["list"]))
    configured = codex_configured(home)
    cl_ladder = list((t.get("claude") or {}).get("ladder") or [])
    out: Dict[str, dict] = {}
    for name, tier in (t.get("tiers") or {}).items():
        want = tier.get("effort") or "medium"
        m, why = pick_codex(tier.get("codex") or "default", models, configured, list(cx.get("fast_words") or []))
        offered = [x.get("effort") for x in (m or {}).get("supported_reasoning_levels") or [] if isinstance(x, dict)]
        c_model, c_why = pick_claude(tier.get("claude") or "inherit", cl_ladder)
        out[name] = {
            "when": tier.get("when") or "",
            "brief": tier.get("brief") or "",
            "codex": {"model": (m or {}).get("slug"), "effort": lower_effort(want, offered, ladder, ceiling),
                      "why": why if (m or models) else "no model list found (run codex once): the tool's own default"},
            # Claude Code lowers an effort a model does not offer itself; the ceiling still applies here
            "claude": {"model": c_model, "effort": lower_effort(want, None, ladder, ceiling), "why": c_why},
        }
    return out


def next_decision(content: Path, home: Path, state: dict, *, current_context_sha256: str,
                  current_artifact_sha256: Optional[str] = None,
                  profile: Optional[dict] = None) -> dict:
    """Advisory next step from the existing tier resolver and a bound gate history.

    The caller supplies independent gate receipts; this function never accepts a
    worker's success text as task truth and never dispatches a model itself.
    """
    counters = {"attempts": 0, "total_tokens": 0, "tool_calls": 0, "wall_seconds": 0}
    result = {"schema": "harness.route-decision/v1", "decision": "HOLD",
              "reason": "invalid_state", "tier": None, "model": None, "effort": None,
              "route_version": None, "attempt_index": None, "counters": counters,
              "context_sha256": current_context_sha256}

    def finish(decision, reason, *, tier=None, model=None, effort=None, index=None):
        return {**result, "decision": decision, "reason": reason, "tier": tier,
                "model": model, "effort": effort, "attempt_index": index,
                "counters": dict(counters)}

    if (not isinstance(state, dict) or state.get("schema") != "harness.route-state/v1"
            or state.get("provider") != "codex" or not isinstance(current_context_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", current_context_sha256)
            or not isinstance(state.get("context_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", state["context_sha256"])
            or not isinstance(state.get("check_id"), str) or not state["check_id"].strip()
            or len(state["check_id"]) > 128):
        return finish("HOLD", "invalid_state")
    if state["context_sha256"] != current_context_sha256:
        return finish("HOLD", "stale_context")
    t = load(content, home, profile)
    policy = t.get("progression") or {}
    if policy.get("enabled") is not True:
        return finish("HOLD", "route_disabled")
    steps = policy.get("codex_steps")
    tiers = t.get("tiers") or {}
    if (not isinstance(steps, list) or not 1 <= len(steps) <= 16
            or any(not isinstance(s, str) or s not in tiers for s in steps)
            or len(set(steps)) != len(steps)):
        return finish("HOLD", "invalid_policy")
    resolved = resolve(content, home, profile)
    cx = t.get("codex") or {}
    models = codex_models(home, list(cx.get("visible") or ["list"]))
    by_slug = {m["slug"]: m for m in models}
    ceiling = t.get("ceiling")
    ladder = list(t.get("efforts") or [])
    if ceiling not in ladder or len(ladder) != len(set(ladder)):
        return finish("HOLD", "invalid_policy")
    attempts = state.get("attempts")
    limits = state.get("limits")
    if (not isinstance(attempts, list) or len(attempts) > 32 or not isinstance(limits, dict)
            or any(type(limits.get(k)) is not int or limits[k] <= 0 for k in
                   ("max_attempts", "max_total_tokens", "max_tools"))
            or type(limits.get("max_wall_seconds")) not in (int, float)
            or not math.isfinite(limits["max_wall_seconds"])
            or limits["max_wall_seconds"] <= 0):
        return finish("HOLD", "invalid_budget")
    start = state.get("start_tier", steps[0])
    max_tier = state.get("max_tier", steps[-1])
    if start not in steps or max_tier not in steps:
        return finish("HOLD", "invalid_state")
    start_index, max_index = steps.index(start), steps.index(max_tier)
    if start_index > max_index:
        return finish("HOLD", "tier_ceiling")
    if start_index and (not isinstance(state.get("start_reason"), str)
                        or not 1 <= len(state["start_reason"].strip()) <= 256):
        return finish("HOLD", "unjustified_start")
    version_material = {"steps": steps, "tiers": {s: tiers[s] for s in steps},
                        "resolved": {s: resolved[s]["codex"] for s in steps},
                        "ceiling": ceiling, "models": models, "limits": limits,
                        "start_tier": start, "start_reason": state.get("start_reason"),
                        "max_tier": max_tier, "context_sha256": current_context_sha256,
                        "check_id": state["check_id"]}
    result["route_version"] = hashlib.sha256(json.dumps(
        version_material, sort_keys=True, default=str).encode()).hexdigest()[:16]
    if state.get("route_version") not in (None, result["route_version"]):
        return finish("HOLD", "stale_route")
    if attempts and state.get("route_version") != result["route_version"]:
        return finish("HOLD", "stale_route")
    total_tokens = total_tools = 0
    total_seconds = 0.0
    for i, attempt in enumerate(attempts):
        if (not isinstance(attempt, dict) or attempt.get("route_version") != result["route_version"]
                or attempt.get("context_sha256") != current_context_sha256
                or start_index + i >= len(steps) or attempt.get("tier") != steps[start_index + i]):
            return finish("HOLD", "stale_state")
        gate = attempt.get("gate")
        if (not isinstance(gate, dict) or gate.get("schema") != "harness.gate-result/v1"
                or gate.get("check_id") != state["check_id"]
                or gate.get("status") not in ("PASS", "FAIL")
                or not isinstance(gate.get("artifact_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", gate["artifact_sha256"])
                or attempt.get("artifact_sha256") != gate["artifact_sha256"]):
            return finish("HOLD", "unknown_outcome")
        if gate["status"] == "PASS":
            if not isinstance(current_artifact_sha256, str) or not re.fullmatch(
                    r"[0-9a-f]{64}", current_artifact_sha256):
                return finish("HOLD", "artifact_unverified")
            if current_artifact_sha256 != gate["artifact_sha256"]:
                return finish("HOLD", "stale_artifact")
        usage = attempt.get("usage")
        if (not isinstance(usage, dict)
                or any(type(usage.get(k)) is not int or usage[k] < 0 for k in
                       ("input_tokens", "output_tokens", "tool_calls"))
                or type(usage.get("wall_seconds")) not in (int, float)
                or not math.isfinite(usage["wall_seconds"]) or usage["wall_seconds"] < 0):
            if gate["status"] == "PASS" and i == len(attempts) - 1:
                counters.update(attempts=i + 1, total_tokens=None, tool_calls=None, wall_seconds=None)
                return finish("STOP", "independent_gate_passed")
            return finish("HOLD", "usage_unknown")
        total_tokens += usage["input_tokens"] + usage["output_tokens"]
        total_tools += usage["tool_calls"]
        total_seconds += usage["wall_seconds"]
        counters.update(attempts=i + 1, total_tokens=total_tokens, tool_calls=total_tools,
                        wall_seconds=round(total_seconds, 3))
        if gate["status"] == "PASS":
            return finish("STOP", "independent_gate_passed") if i == len(attempts) - 1 else finish("HOLD", "invalid_history")
    if counters["attempts"] >= limits["max_attempts"] or total_tokens >= limits["max_total_tokens"] \
            or total_tools >= limits["max_tools"] or total_seconds >= limits["max_wall_seconds"]:
        return finish("HOLD", "budget_exhausted")
    index = start_index + len(attempts)
    if index > max_index:
        return finish("HOLD", "tier_ceiling")
    if index >= len(steps):
        return finish("HOLD", "route_exhausted")
    tier = steps[index]
    selected = resolved[tier]["codex"]
    model = selected["model"]
    want = tiers[tier].get("effort") or "medium"
    if want not in ladder:
        return finish("HOLD", "invalid_policy")
    if ladder.index(want) > ladder.index(ceiling):
        return finish("HOLD", "tier_ceiling")
    if not model or model not in by_slug:
        return finish("HOLD", "model_unavailable")
    selector = tiers[tier].get("codex") or "default"
    if selector == "fast" and not any(
            any(word in (candidate.get("description") or "").lower()
                for word in (cx.get("fast_words") or [])) for candidate in models):
        return finish("HOLD", "model_unavailable")
    if selector not in ("fast", "default") and selector != model:
        return finish("HOLD", "model_unavailable")
    offered = {x.get("effort") for x in by_slug[model].get("supported_reasoning_levels") or []
               if isinstance(x, dict)}
    if want not in offered or selected["effort"] != want:
        return finish("HOLD", "pair_unsupported")
    reason = ("independent_gate_failed" if attempts else
              "declared_direct_start" if start_index else "configured_minimum_start")
    return finish("DISPATCH", reason, tier=tier, model=model, effort=want,
                  index=len(attempts) + 1)


# ---- what the adapters write: one agent file per tier, named harness-<tier> --------------------------------

PREFIX = "harness-"


def _quote(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)       # a JSON string is a valid TOML basic string and YAML scalar


def claude_agent(name: str, tier: dict) -> str:
    c = tier["claude"]
    lines = ["---", f"name: {PREFIX}{name}", f"description: {_quote('Use for ' + tier['when'])}"]
    if c["model"]:
        lines.append(f"model: {c['model']}")
    lines += [f"effort: {c['effort']}", "---", "", tier["brief"],
              "", f"<!-- written by agent-harness from routing.toml: model {c['why']}; edit "
                  "~/.agent-harness/routing.toml, not this file -->", ""]
    return "\n".join(lines)


def codex_agent(name: str, tier: dict) -> str:
    c = tier["codex"]
    lines = [f"# written by agent-harness from routing.toml (model: {c['why']}); edit ~/.agent-harness/routing.toml",
             f"name = {_quote(PREFIX + name)}", f"description = {_quote('Use for ' + tier['when'])}",
             f"developer_instructions = {_quote(tier['brief'])}"]
    if c["model"]:
        lines.append(f"model = {_quote(c['model'])}")
    lines.append(f"model_reasoning_effort = {_quote(c['effort'])}")
    return "\n".join(lines) + "\n"


def available(content: Path) -> bool:
    return (content / TEMPLATE).is_file()
