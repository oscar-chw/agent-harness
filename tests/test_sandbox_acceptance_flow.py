"""The acceptance demo derives a bounded artifact from real local input."""

from examples.sandbox_parts import acceptance_flow


def test_real_input_passes_independent_grader_and_mutant_fails(tmp_path):
    source = tmp_path / "README.md"
    source.write_text("# Local input\nA real acceptance control.\n")

    result = acceptance_flow.run(tmp_path)

    assert result["section"] == "acceptance"
    assert result["status"] == "PASS"
    assert {check["name"]: check["status"] for check in result["checks"]} == {
        "generated_artifact_passes_independent_structural_grader": "PASS",
        "mutated_artifact_fails_independent_structural_grader": "PASS",
    }
    assert result["artifact"]["source"] == "README.md"
    assert result["artifact"]["byte_length"] == len(source.read_bytes())
    assert result["artifact"]["sha256"]
    assert result["accounting"] == {
        "direct_input_tokens": "UNKNOWN",
        "direct_output_tokens": "UNKNOWN",
        "cached_input_tokens": "UNKNOWN",
        "whole_cost": "UNKNOWN",
    }
    assert result["claims"] == {
        "cost_superiority": "NOT_CLAIMED",
        "v1_qualification": "NOT_QUALIFIED",
        "semantic_quality": "NOT_EVALUATED",
        "model_delivery": "NOT_RUN",
    }


def test_missing_real_input_fails_closed(tmp_path):
    result = acceptance_flow.run(tmp_path)
    assert result["status"] == "FAIL"
    assert all(check["status"] == "FAIL" for check in result["checks"])
