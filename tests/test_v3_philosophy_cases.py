"""Structural checks of visible authored cases, without scoring tutor responses."""
import copy
import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "eval/v3_philosophy_cases.json"
pytestmark = pytest.mark.case

# Keep these independent of the pack so removal cannot erase its own coverage.
REQUIRED_OBSERVABLES = {
    "PH-01": {"unknown_outcome", "missing_contract", "reversal"},
    "PH-02": {"discriminating_question", "repair", "responsive_help"},
    "PH-03": {"focused_step", "use_known_prerequisites", "learner_work"},
    "PH-04": {"answer_now", "derivation", "respect_intent"},
    "PH-05": {"purpose_first", "small_example", "bridge"},
    "PH-06": {"result_first", "concise_reason", "no_blocking_question"},
    "PH-07": {"changed_sign", "check", "limited_claim"},
    "PH-08": {"current_unknown", "history_and_scope", "next_check"},
}
DIMENSIONS = {"grounding", "counterexample", "adaptation", "transfer", "calibration"}
EXECUTION = {
    "model_comparison": "NOT_RUN",
    "learner_transfer": "NOT_RUN",
    "teaching_efficacy": "NOT_RUN",
    "complete_usage": "NOT_RUN",
    "promotion": "NOT_GRANTED",
}


def load_pack():
    return json.loads(PACK.read_text(encoding="utf-8"))


def validate_structure(pack):
    assert pack["schema"] == "harness.v3-philosophy-cases/v1", "schema"
    assert pack["classification"] == (
        "AUTHORED_VISIBLE_DEVELOPMENT_CASES"
    ), "classification"
    assert pack["execution"] == EXECUTION, "authoring cannot establish execution"
    dimensions = pack["rubric"]["dimensions"]
    assert set(dimensions) == DIMENSIONS, "rubric dimensions"
    for anchors in dimensions.values():
        assert set(anchors) == {"0", "1", "2"}, "score anchors"
        assert all(
            isinstance(text, str) and text.strip() for text in anchors.values()
        ), "empty anchor"
        assert len(set(anchors.values())) == 3, "indistinguishable anchors"
    cases = pack["cases"]
    assert len(cases) == len(REQUIRED_OBSERVABLES), "case count"
    assert {case["id"] for case in cases} == set(REQUIRED_OBSERVABLES), "case coverage"
    for case in cases:
        assert set(case["observables"]) == (
            REQUIRED_OBSERVABLES[case["id"]]
        ), "observable coverage"
        assert case["dimension_ids"] and (
            set(case["dimension_ids"]) <= DIMENSIONS
        ), "dimension references"
        assert case["source_ids"] and (
            set(case["source_ids"]) <= set(pack["sources"])
        ), "source references"
        assert case["critical_failures"] and all(
            case["critical_failures"]
        ), "critical failures"
        assert all(
            isinstance(text, str) and text.strip()
            for text in case["observables"].values()
        ), "empty observable"
        assert (
            case["prompt"] and case["supplied_facts"] and case["changed_constraint"]
        ), "case context"
        controls = case["calibration"]
        assert set(controls) == {"acceptable", "reject"}, "response controls"
        assert controls["acceptable"] and controls["reject"], "empty control"
        assert controls["acceptable"] != controls["reject"], "identical controls"


def test_visible_case_pack_has_independent_coverage_and_unrun_status():
    validate_structure(load_pack())


def test_local_source_bindings_match_the_frozen_case_basis():
    sources = load_pack()["sources"]
    for key in ("reasoning", "decision_cases", "decision_contract"):
        source = sources[key]
        relative = Path(source["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == (
            source["sha256"]
        ), key
    assert sources["janestreet_tutor"]["url"] == (
        "https://github.com/janestreet/agent_skills/blob/master/socratic-tutor/SKILL.md"
    )


def test_guided_direct_and_urgent_cases_control_for_prior_knowledge():
    cases = {case["id"]: case for case in load_pack()["cases"]}
    assert cases["PH-03"]["supplied_facts"] == cases["PH-04"]["supplied_facts"]
    assert cases["PH-04"]["supplied_facts"] == cases["PH-06"]["supplied_facts"]
    assert len({cases[key]["prompt"] for key in ("PH-03", "PH-04", "PH-06")}) == 3
    assert "follow_up" in cases["PH-02"], "missing observed learner steering"


@pytest.mark.parametrize("defect", [
    "missing_case", "missing_observable", "missing_dimension", "unknown_source",
    "empty_failures", "identical_controls", "pretend_efficacy", "missing_anchor",
])
def test_incomplete_or_promoted_case_pack_is_rejected(defect):
    pack = copy.deepcopy(load_pack())
    case = pack["cases"][0]
    if defect == "missing_case":
        pack["cases"].pop()
    elif defect == "missing_observable":
        case["observables"].pop("missing_contract")
    elif defect == "missing_dimension":
        pack["rubric"]["dimensions"].pop("transfer")
    elif defect == "unknown_source":
        case["source_ids"] = ["unobserved_source"]
    elif defect == "empty_failures":
        case["critical_failures"] = []
    elif defect == "identical_controls":
        case["calibration"]["reject"] = case["calibration"]["acceptable"]
    elif defect == "pretend_efficacy":
        pack["execution"]["teaching_efficacy"] = "PASS"
    elif defect == "missing_anchor":
        pack["rubric"]["dimensions"]["adaptation"].pop("1")
    with pytest.raises(AssertionError):
        validate_structure(pack)
