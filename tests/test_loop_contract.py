"""Public contract examples; execution belongs to the finalisation owner."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent_harness.loop_contract import assess


PIN = "a" * 64


def example():
    contract = {
        "schema": "harness.loop-contract/v1",
        "objective": "Reduce tokens while preserving every required result.",
        "cases": ["small", "large"],
        "required_checks": ["correctness", "coverage"],
        "required_scope": "local",
        "max_attempts": 3,
        "metric": None,
    }
    context = {"model": "declared-model", "effort": "high",
               "tools_sha256": "b" * 64, "source_scope_sha256": "c" * 64}
    pairs = []
    for index, case_id in enumerate(contract["cases"]):
        pair = {"case_id": case_id}
        for arm, prefix in (("base", "d"), ("candidate", "e")):
            run_id = f"{arm}-{case_id}"
            artifact = prefix * 63 + str(index)
            pair[arm] = {
                "run_id": run_id, "artifact_sha256": artifact, "scope": "local",
                "checks": {
                    name: {"run_id": run_id, "artifact_sha256": artifact, "status": "PASS"}
                    for name in contract["required_checks"]
                },
                "input_tokens": 80, "output_tokens": 20, "metric_samples": [],
            }
        pairs.append(pair)
    results = {
        "schema": "harness.loop-results/v1", "contract_sha256": PIN,
        "attempt": 1, "usage_complete": True, "overhead_tokens": 0,
        "base_context": deepcopy(context), "candidate_context": deepcopy(context),
        "pairs": pairs,
    }
    return contract, results


def evaluate(contract, results):
    return assess(contract, results, contract_sha256=PIN)


def change(document, path, value):
    parent = document
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value


def token_gain(results):
    for pair in results["pairs"]:
        pair["candidate"]["input_tokens"] = 70


def metric_example(direction="min", minimum=2, noise=1):
    contract, results = example()
    contract["metric"] = {"name": "latency", "direction": direction,
                          "minimum_effect": minimum, "noise_floor": noise}
    sign = 1 if direction == "min" else -1
    for pair in results["pairs"]:
        # Medians improve by two despite the candidate's adverse outlier.
        pair["base"]["metric_samples"] = [0, 10 * sign, 11 * sign]
        pair["candidate"]["metric_samples"] = [0, 8 * sign, 1000 * sign]
    return contract, results


@pytest.mark.parametrize("gain", ["tokens", "check"])
def test_sound_gain_accepts_without_granting_promotion_or_mutating_inputs(gain):
    contract, results = example()
    if gain == "tokens":
        token_gain(results)
    else:
        results["pairs"][0]["base"]["checks"]["correctness"]["status"] = "FAIL"
    original = deepcopy((contract, results))
    answer = evaluate(contract, results)
    assert answer["decision"] == "ACCEPT_CANDIDATE"
    assert answer["schema"] == "harness.loop-assessment/v1"
    assert answer["promotion"] == "NOT_GRANTED"
    assert isinstance(answer["reasons"], list)
    assert all(isinstance(reason, str) for reason in answer["reasons"])
    assert answer["stop"] is False
    assert isinstance(answer["next_action"], str) and answer["next_action"]
    assert answer["next_action"] != "STOP_EXPERIMENT"
    assert answer["base_tokens"] == 200
    assert answer["candidate_tokens"] == (180 if gain == "tokens" else 200)
    assert (contract, results) == original


def test_joint_success_is_conjunction_on_each_run_not_minimum_of_marginals():
    contract, results = example()
    results["pairs"][0]["base"]["checks"]["coverage"]["status"] = "FAIL"
    results["pairs"][1]["base"]["checks"]["correctness"]["status"] = "FAIL"
    answer = evaluate(contract, results)
    assert answer["decision"] == "ACCEPT_CANDIDATE"
    assert answer["joint_success"] == {"base": 0, "candidate": 2}


@pytest.mark.parametrize("field", ["run_id", "artifact_sha256"])
def test_check_cannot_borrow_another_runs_success_or_artifact(field):
    contract, results = example()
    token_gain(results)
    check = results["pairs"][0]["candidate"]["checks"]["coverage"]
    check[field] = results["pairs"][1]["candidate"][field]
    with pytest.raises(ValueError):
        evaluate(contract, results)


@pytest.mark.parametrize("source", [(0, "base"), (1, "candidate")])
def test_run_ids_are_unique_across_both_arms_and_cases(source):
    contract, results = example()
    run = results["pairs"][0]["candidate"]
    run["run_id"] = results["pairs"][source[0]][source[1]]["run_id"]
    for check in run["checks"].values():
        check["run_id"] = run["run_id"]
    with pytest.raises(ValueError):
        evaluate(contract, results)


@pytest.mark.parametrize("arm", ["base", "candidate"])
@pytest.mark.parametrize("status", ["UNKNOWN", "NOT_RUN"])
def test_unknown_observation_prevents_acceptance_even_with_token_gain(arm, status):
    contract, results = example()
    token_gain(results)
    results["pairs"][0][arm]["checks"]["coverage"]["status"] = status
    assert evaluate(contract, results)["decision"] == "INCONCLUSIVE"


def test_incomplete_usage_prevents_acceptance():
    contract, results = example()
    token_gain(results)
    results["usage_complete"] = False
    assert evaluate(contract, results)["decision"] == "INCONCLUSIVE"


@pytest.mark.parametrize("known_failure", ["check", "metric", "tokens"])
@pytest.mark.parametrize("incomplete", ["unknown_check", "usage"])
def test_known_rejection_takes_priority_over_other_incomplete_evidence(known_failure, incomplete):
    contract, results = metric_example() if known_failure == "metric" else example()
    if known_failure == "check":
        results["pairs"][0]["candidate"]["checks"]["correctness"]["status"] = "FAIL"
    elif known_failure == "metric":
        results["pairs"][0]["candidate"]["metric_samples"] = [11, 11, 11]
    else:
        results["overhead_tokens"] = 1
    if incomplete == "unknown_check":
        results["pairs"][1]["base"]["checks"]["coverage"]["status"] = "UNKNOWN"
    else:
        results["usage_complete"] = False
    answer = evaluate(contract, results)
    assert answer["decision"] == "REJECT_CANDIDATE"
    assert answer["reasons"]


@pytest.mark.parametrize("base_status", ["PASS", "FAIL"])
def test_candidate_failure_cannot_be_offset_by_other_case_or_token_gain(base_status):
    contract, results = example()
    token_gain(results)
    results["pairs"][0]["base"]["checks"]["coverage"]["status"] = base_status
    results["pairs"][0]["candidate"]["checks"]["coverage"]["status"] = "FAIL"
    results["pairs"][1]["base"]["checks"]["correctness"]["status"] = "FAIL"
    assert evaluate(contract, results)["decision"] == "REJECT_CANDIDATE"


@pytest.mark.parametrize("overhead, expected", [
    (19, "ACCEPT_CANDIDATE"), (20, "INCONCLUSIVE"), (21, "REJECT_CANDIDATE"),
])
def test_all_candidate_overhead_counts_against_total_token_budget(overhead, expected):
    contract, results = example()
    token_gain(results)
    results["overhead_tokens"] = overhead
    answer = evaluate(contract, results)
    assert answer["decision"] == expected
    assert answer["base_tokens"] == 200
    assert answer["candidate_tokens"] == 180 + overhead


def test_token_increase_rejects_even_when_a_required_check_improves():
    contract, results = example()
    results["pairs"][0]["base"]["checks"]["coverage"]["status"] = "FAIL"
    results["overhead_tokens"] = 1
    assert evaluate(contract, results)["decision"] == "REJECT_CANDIDATE"


@pytest.mark.parametrize("direction", ["min", "max"])
@pytest.mark.parametrize("minimum, noise, expected", [
    (2, 1, "ACCEPT_CANDIDATE"),
    (3, 1, "INCONCLUSIVE"),
    (2, 2, "INCONCLUSIVE"),
    (0, 3, "INCONCLUSIVE"),
])
def test_median_gain_must_meet_effect_and_strictly_exceed_noise(direction, minimum, noise, expected):
    contract, results = metric_example(direction, minimum, noise)
    assert evaluate(contract, results)["decision"] == expected


@pytest.mark.parametrize("direction", ["min", "max"])
def test_metric_regression_in_one_case_cannot_be_offset_by_gain_elsewhere(direction):
    contract, results = metric_example(direction)
    sign = 1 if direction == "min" else -1
    results["pairs"][0]["base"]["metric_samples"] = [100 * sign]
    results["pairs"][0]["candidate"]["metric_samples"] = [1 * sign]
    results["pairs"][1]["base"]["metric_samples"] = [10 * sign]
    results["pairs"][1]["candidate"]["metric_samples"] = [11 * sign]
    token_gain(results)
    assert evaluate(contract, results)["decision"] == "REJECT_CANDIDATE"


def test_unchanged_metric_and_checks_are_not_positive_evidence():
    contract, results = metric_example(minimum=0, noise=0)
    for pair in results["pairs"]:
        pair["candidate"]["metric_samples"] = list(pair["base"]["metric_samples"])
    assert evaluate(contract, results)["decision"] == "INCONCLUSIVE"
    contract, results = example()
    assert evaluate(contract, results)["decision"] == "INCONCLUSIVE"


@pytest.mark.parametrize("attempt, maximum, stop", [(1, 3, False), (3, 3, True), (1, 1, True), (1000, 1000, True)])
def test_exhaustion_stops_even_when_candidate_is_acceptable(attempt, maximum, stop):
    contract, results = example()
    token_gain(results)
    contract["max_attempts"] = maximum
    results["attempt"] = attempt
    answer = evaluate(contract, results)
    assert answer["decision"] == "ACCEPT_CANDIDATE"
    assert answer["stop"] is stop
    assert (answer["next_action"] == "STOP_EXPERIMENT") is stop
    assert answer["promotion"] == "NOT_GRANTED"


@pytest.mark.parametrize("field, value", [
    ("model", "another-model"), ("effort", "low"),
    ("tools_sha256", "f" * 64), ("source_scope_sha256", "f" * 64),
])
def test_unmatched_control_context_is_malformed(field, value):
    contract, results = example()
    token_gain(results)
    results["candidate_context"][field] = value
    with pytest.raises(ValueError):
        evaluate(contract, results)


@pytest.mark.parametrize("pin, observed", [
    (PIN, "f" * 64), ("g" * 64, "g" * 64), ("a" * 63, "a" * 63), (True, True),
])
def test_results_bind_to_exact_valid_caller_contract_digest(pin, observed):
    contract, results = example()
    results["contract_sha256"] = observed
    with pytest.raises(ValueError):
        assess(contract, results, contract_sha256=pin)


@pytest.mark.parametrize("path", [
    ("pairs",), ("pairs", 0, "candidate"),
    ("pairs", 0, "candidate", "checks", "coverage"),
    ("pairs", 0, "candidate", "checks", "coverage", "status"),
    ("pairs", 0, "candidate", "input_tokens"), ("base_context", "model"),
])
def test_missing_observations_are_errors_not_silent_defaults(path):
    contract, results = example()
    parent = results
    for key in path[:-1]:
        parent = parent[key]
    del parent[path[-1]]
    with pytest.raises(ValueError):
        evaluate(contract, results)


@pytest.mark.parametrize("kind", ["missing", "duplicate", "unknown"])
def test_pairs_cover_exactly_the_frozen_cases(kind):
    contract, results = example()
    if kind == "missing":
        results["pairs"].pop()
    elif kind == "duplicate":
        results["pairs"][1]["case_id"] = "small"
    else:
        results["pairs"][1]["case_id"] = "unfrozen"
    with pytest.raises(ValueError):
        evaluate(contract, results)


@pytest.mark.parametrize("side, path", [
    ("contract", ()), ("contract", ("metric",)), ("results", ()),
    ("results", ("base_context",)), ("results", ("candidate_context",)),
    ("results", ("pairs", 0)), ("results", ("pairs", 0, "candidate")),
    ("results", ("pairs", 0, "candidate", "checks")),
    ("results", ("pairs", 0, "candidate", "checks", "coverage")),
])
def test_unknown_fields_are_rejected_at_each_schema_layer(side, path):
    contract, results = metric_example()
    target = contract if side == "contract" else results
    for key in path:
        target = target[key]
    target["unexpected"] = "value"
    with pytest.raises(ValueError):
        evaluate(contract, results)


@pytest.mark.parametrize("side, path, value", [
    ("contract", ("schema",), "harness.loop-contract/v2"),
    ("contract", ("objective",), ""),
    ("contract", ("objective",), "x" * 4097),
    ("contract", ("cases",), []),
    ("contract", ("cases",), ["small", "small"]),
    ("contract", ("cases",), [""]),
    ("contract", ("cases",), [str(i) for i in range(1001)]),
    ("contract", ("required_checks",), []),
    ("contract", ("required_checks",), ["coverage", "coverage"]),
    ("contract", ("required_checks",), [str(i) for i in range(33)]),
    ("contract", ("required_scope",), "remote"),
    ("contract", ("max_attempts",), True),
    ("contract", ("max_attempts",), 1.0),
    ("contract", ("max_attempts",), 0),
    ("contract", ("max_attempts",), 1001),
    ("results", ("schema",), "harness.loop-results/v2"),
    ("results", ("attempt",), True),
    ("results", ("attempt",), 1.0),
    ("results", ("attempt",), 0),
    ("results", ("attempt",), 4),
    ("results", ("usage_complete",), 1),
    ("results", ("overhead_tokens",), True),
    ("results", ("overhead_tokens",), -1),
    ("results", ("base_context", "tools_sha256"), "bad"),
    ("results", ("pairs", 0, "candidate", "run_id"), ""),
    ("results", ("pairs", 0, "candidate", "artifact_sha256"), "bad"),
    ("results", ("pairs", 0, "candidate", "scope"), "native"),
    ("results", ("pairs", 0, "candidate", "input_tokens"), True),
    ("results", ("pairs", 0, "candidate", "output_tokens"), 1.0),
    ("results", ("pairs", 0, "candidate", "output_tokens"), -1),
    ("results", ("pairs", 0, "candidate", "metric_samples"), [1]),
    ("results", ("pairs", 0, "candidate", "checks", "coverage", "status"), "PASSED"),
])
def test_malformed_schema_and_exact_integer_limits_raise_value_error(side, path, value):
    contract, results = example()
    change(contract if side == "contract" else results, path, value)
    with pytest.raises(ValueError):
        evaluate(contract, results)


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("target", ["minimum_effect", "noise_floor", "sample"])
def test_metric_numbers_are_finite_and_never_booleans(value, target):
    contract, results = metric_example()
    if target == "sample":
        results["pairs"][0]["candidate"]["metric_samples"][0] = value
    else:
        contract["metric"][target] = value
    with pytest.raises(ValueError):
        evaluate(contract, results)


@pytest.mark.parametrize("target, value", [
    ("minimum_effect", -1), ("noise_floor", -1), ("name", ""), ("direction", "lower"),
])
def test_metric_definition_has_bounded_valid_fields(target, value):
    contract, results = metric_example()
    contract["metric"][target] = value
    with pytest.raises(ValueError):
        evaluate(contract, results)


def test_extreme_finite_metric_inputs_keep_comparisons_meaningful():
    contract, results = metric_example(minimum=1e308, noise=1e308)
    for pair in results["pairs"]:
        pair["base"]["metric_samples"] = [1e308, 1e308]
        pair["candidate"]["metric_samples"] = [-1e308, -1e308]
    # The exact median gain exceeds both finite thresholds; a float overflow
    # while averaging or subtracting must not turn it into a neutral result.
    assert evaluate(contract, results)["decision"] == "ACCEPT_CANDIDATE"


@pytest.mark.parametrize("samples", [[], [8], [8] * 4097])
def test_metric_runs_require_nonempty_bounded_matched_samples(samples):
    contract, results = metric_example()
    results["pairs"][0]["candidate"]["metric_samples"] = samples
    with pytest.raises(ValueError):
        evaluate(contract, results)
