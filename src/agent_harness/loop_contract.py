"""Pure assessment of declared paired observations; no execution or promotion.

Matching bindings do not attest that checks or measurements actually ran.
"""
from fractions import Fraction
import math
import re

SHA = re.compile(r"[0-9a-f]{64}\Z")
SCOPES = ("local", "installed", "native", "live")
STATUSES = ("PASS", "FAIL", "UNKNOWN", "NOT_RUN")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _fields(value, fields, label):
    _require(isinstance(value, dict) and set(value) == set(fields),
             "invalid " + label + " fields")


def _text(value, label):
    _require(isinstance(value, str) and bool(value.strip()) and len(value) <= 4096,
             "invalid " + label)
    return value


def _hash(value, label):
    _require(isinstance(value, str) and SHA.fullmatch(value) is not None,
             "invalid " + label)


def _integer(value, label, minimum=0, maximum=None):
    _require(type(value) is int and value >= minimum
             and (maximum is None or value <= maximum), "invalid " + label)


def _number(value, label, nonnegative=False):
    _require(type(value) in (int, float), "invalid " + label)
    _require(type(value) is int or math.isfinite(value), "nonfinite " + label)
    _require(not nonnegative or value >= 0, "negative " + label)
    return Fraction(value)


def _names(value, label, maximum):
    _require(isinstance(value, list) and 1 <= len(value) <= maximum,
             "invalid " + label + " list")
    for name in value:
        _text(name, label)
    _require(len(set(value)) == len(value), "duplicate " + label)
    return set(value)


def _context(value):
    _fields(value, ("model", "effort", "tools_sha256", "source_scope_sha256"), "context")
    for name in ("model", "effort"):
        _text(value[name], "context " + name)
    for name in ("tools_sha256", "source_scope_sha256"):
        _hash(value[name], "context " + name)


def _run(value, checks, scope, metric, run_ids):
    _fields(value, ("run_id", "artifact_sha256", "scope", "checks", "input_tokens",
                    "output_tokens", "metric_samples"), "run")
    run_id = _text(value["run_id"], "run ID")
    _require(run_id not in run_ids, "duplicate run ID across paired observations")
    run_ids.add(run_id)
    _hash(value["artifact_sha256"], "run artifact hash")
    _require(value["scope"] == scope, "run scope does not match required scope")
    _fields(value["checks"], checks, "run checks")
    statuses = {}
    for name in checks:
        check = value["checks"][name]
        _fields(check, ("run_id", "artifact_sha256", "status"), "check")
        _require(check["run_id"] == run_id
                 and check["artifact_sha256"] == value["artifact_sha256"],
                 "check must bind its containing run and artifact")
        _require(check["status"] in STATUSES, "invalid check status")
        statuses[name] = check["status"]
    for name in ("input_tokens", "output_tokens"):
        _integer(value[name], name)
    samples = value["metric_samples"]
    _require(isinstance(samples, list) and len(samples) <= 4096,
             "invalid metric samples")
    _require(bool(samples) if metric is not None else not samples,
             "metric samples do not match contract metric")
    samples = sorted(_number(sample, "metric sample") for sample in samples)
    median = None
    if samples:
        # Exact arithmetic avoids overflow for finite extreme samples/gains.
        median = (samples[(len(samples) - 1) // 2] + samples[len(samples) // 2]) / 2
    return statuses, value["input_tokens"] + value["output_tokens"], median, len(samples)


def _add(reasons, reason):
    if reason not in reasons:
        reasons.append(reason)


def assess(contract, results, *, contract_sha256):
    """Validate frozen bindings, then assess non-regression and observed gain.

    Known rejection takes priority over incomplete observations. Neither an
    accepted declaration nor a bounded next action grants activation authority.
    """
    _fields(contract, ("schema", "objective", "cases", "required_checks", "required_scope",
                       "max_attempts", "metric"), "contract")
    _require(contract["schema"] == "harness.loop-contract/v1", "unsupported contract schema")
    _text(contract["objective"], "objective")
    cases = _names(contract["cases"], "case ID", 1000)
    _names(contract["required_checks"], "required check", 32)
    checks = contract["required_checks"]
    scope = contract["required_scope"]
    _require(scope in SCOPES, "invalid required scope")
    _integer(contract["max_attempts"], "maximum attempts", 1, 1000)
    metric = contract["metric"]
    if metric is not None:
        _fields(metric, ("name", "direction", "minimum_effect", "noise_floor"), "metric")
        _text(metric["name"], "metric name")
        _require(metric["direction"] in ("min", "max"), "invalid metric direction")
        minimum = _number(metric["minimum_effect"], "minimum effect", nonnegative=True)
        noise = _number(metric["noise_floor"], "noise floor", nonnegative=True)
    _hash(contract_sha256, "contract hash")
    _fields(results, ("schema", "contract_sha256", "attempt", "usage_complete", "overhead_tokens",
                      "base_context", "candidate_context", "pairs"), "results")
    _require(results["schema"] == "harness.loop-results/v1", "unsupported results schema")
    _require(results["contract_sha256"] == contract_sha256, "results contract hash mismatch")
    _integer(results["attempt"], "attempt", 1, contract["max_attempts"])
    _require(type(results["usage_complete"]) is bool, "usage_complete must be boolean")
    _integer(results["overhead_tokens"], "overhead tokens")
    _context(results["base_context"])
    _context(results["candidate_context"])
    _require(results["base_context"] == results["candidate_context"], "comparison contexts differ")
    pairs = results["pairs"]
    _require(isinstance(pairs, list) and len(pairs) == len(cases),
             "results must contain exactly every frozen case")
    seen, run_ids = set(), set()
    rejected, uncertain, gains = [], [], []
    joint = {"base": 0, "candidate": 0}
    totals = {"base": 0, "candidate": results["overhead_tokens"]}
    if not results["usage_complete"]:
        uncertain.append("incomplete_usage")
    for pair in pairs:
        _fields(pair, ("case_id", "base", "candidate"), "pair")
        identity = _text(pair["case_id"], "pair case ID")
        _require(identity in cases and identity not in seen, "unknown or duplicate paired case")
        seen.add(identity)
        observations = {}
        for arm in ("base", "candidate"):
            statuses, tokens, median, count = _run(pair[arm], checks, scope, metric, run_ids)
            observations[arm] = statuses, median, count
            totals[arm] += tokens
            joint[arm] += int(all(status == "PASS" for status in statuses.values()))
            if any(status in ("UNKNOWN", "NOT_RUN") for status in statuses.values()):
                _add(uncertain, "incomplete_checks")
        base, base_median, base_count = observations["base"]
        candidate, candidate_median, candidate_count = observations["candidate"]
        _require(base_count == candidate_count, "paired metric sample counts differ")
        for name in checks:
            if candidate[name] == "FAIL":
                _add(rejected, "candidate_check_failed")
                if base[name] == "PASS":
                    _add(rejected, "per_case_check_regression")
            if base[name] == "FAIL" and candidate[name] == "PASS":
                _add(gains, "check_improved")
        if metric is not None:
            gain = candidate_median - base_median
            if metric["direction"] == "min":
                gain = -gain
            if gain < 0:
                _add(rejected, "per_case_metric_regression")
            elif gain > 0 and gain >= minimum and gain > noise:
                _add(gains, "metric_improved")
    _require(seen == cases, "missing frozen case observations")
    if totals["candidate"] > totals["base"]:
        rejected.append("candidate_token_excess")
    elif totals["candidate"] < totals["base"]:
        gains.append("token_reduction")
    if rejected:
        decision, action = "REJECT_CANDIDATE", "REVIEW_REJECTION"
    elif uncertain:
        decision, action = "INCONCLUSIVE", "REVIEW_MISSING_EVIDENCE"
    elif gains and joint["candidate"] == len(cases):
        decision, action = "ACCEPT_CANDIDATE", "REVIEW_CANDIDATE"
    else:
        decision, action = "INCONCLUSIVE", "REVIEW_EXPERIMENT"
    reasons = rejected + uncertain + gains
    if not gains:
        reasons.append("no_observed_gain")
    stop = results["attempt"] == contract["max_attempts"]
    return {"schema": "harness.loop-assessment/v1", "decision": decision,
            "reasons": reasons, "promotion": "NOT_GRANTED", "stop": stop,
            "next_action": "STOP_EXPERIMENT" if stop else action,
            "base_tokens": totals["base"], "candidate_tokens": totals["candidate"],
            "joint_success": joint}
