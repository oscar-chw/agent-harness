"""Bounded CPU-only structural acceptance demo over a local README."""

import hashlib
import json
from pathlib import Path

_MAX_INPUT_BYTES = 1024 * 1024


def _transform(source: bytes) -> dict:
    """Actor: summarize nonempty source lines into a generated artifact."""
    lines = source.decode("utf-8").splitlines()
    kept = [line.strip() for line in lines if line.strip()]
    return {
        "source": "README.md",
        "sha256": hashlib.sha256(source).hexdigest(),
        "byte_length": len(source),
        "summary": {
            "nonempty_lines": len(kept),
            "first_heading": next((line[2:].strip() for line in kept
                                    if line.startswith("# ")), None),
            "words": sum(len(line.split()) for line in kept),
        },
    }


def _independent_grade(source: bytes, artifact: dict) -> bool:
    """Grader: derive the structural expectation from source, without actor helpers."""
    rows = source.decode("utf-8").split("\n")
    nonempty = [row.strip() for row in rows if row.strip()]
    heading = None
    for row in nonempty:
        candidate = row.strip()
        if candidate[:2] == "# ":
            heading = candidate[2:].strip()
            break
    expected = {
        "source": "README.md",
        "sha256": hashlib.sha256(source).hexdigest(),
        "byte_length": len(source),
        "summary": {
            "nonempty_lines": len(nonempty),
            "first_heading": heading,
            "words": sum(len(row.split()) for row in nonempty),
        },
    }
    return artifact == expected


def run(root: Path) -> dict:
    """Run one bounded source-to-artifact control and a rejected mutant."""
    checks = []
    artifact = None
    source_path = root / "README.md"
    try:
        source = source_path.read_bytes()
        if len(source) > _MAX_INPUT_BYTES:
            raise ValueError("README.md exceeds the 1 MiB input bound")
        generated = _transform(source)
        # JSON round-tripping makes the judged value the serialized artifact.
        artifact = json.loads(json.dumps(generated))
        control_pass = _independent_grade(source, artifact)
        checks.append({
            "name": "generated_artifact_passes_independent_structural_grader",
            "status": "PASS" if control_pass else "FAIL",
            "evidence": (
                "grader independently recomputed structural summary and source digest"
            ),
        })
        mutant = json.loads(json.dumps(artifact))
        mutant["summary"]["words"] += 1
        mutant_rejected = not _independent_grade(source, mutant)
        checks.append({
            "name": "mutated_artifact_fails_independent_structural_grader",
            "status": "PASS" if mutant_rejected else "FAIL",
            "evidence": "grader rejected a word-count mutant",
        })
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        checks.extend([
            {
                "name": "generated_artifact_passes_independent_structural_grader",
                "status": "FAIL",
                "evidence": f"input unavailable or invalid: {exc}",
            },
            {
                "name": "mutated_artifact_fails_independent_structural_grader",
                "status": "FAIL",
                "evidence": "no valid artifact was generated",
            },
        ])
    return {
        "section": "acceptance",
        "status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
        "checks": checks,
        "artifact": artifact,
        "accounting": {
            "direct_input_tokens": "UNKNOWN",
            "direct_output_tokens": "UNKNOWN",
            "cached_input_tokens": "UNKNOWN",
            "whole_cost": "UNKNOWN",
        },
        "claims": {
            "cost_superiority": "NOT_CLAIMED",
            "v1_qualification": "NOT_QUALIFIED",
            "semantic_quality": "NOT_EVALUATED",
            "model_delivery": "NOT_RUN",
        },
    }
