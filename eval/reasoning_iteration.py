"""Frozen paired decision instrument. Local fixtures never establish native evidence.

The owner/controller and append-only filesystem are trusted, as in the existing
procedure controller. Native boundary observations are supplied only by that
controller. Acceptance is recomputed, never read from a claimed result file.
"""

import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_harness import procedure_execution as C, procedures as P  # noqa: E402
from agent_harness.redact import redact  # noqa: E402

CASES = ROOT / "eval/reasoning_iteration_cases.json"
FULL_GUIDE = ROOT / "content/skills/work-loop/reasoning.md"
CANDIDATE = (
    "Identify the requested deliverable and decisive facts. Check units, denominators, "
    "dependence, timing, and whether observations distinguish alternatives. Choose the "
    "action justified by those facts, preserving uncertainty. Verify consequences and "
    "the output contract. For direct requests give the result. For teaching include "
    "a short derivation."
)
ACCEPTANCE = {
    "grader": "exact-json-per-case-v1",
    "candidate_all_correct": True,
    "no_corresponding_case_regression": True,
    "candidate_task_tokens_lte_baseline": True,
    "strict_quality_or_token_improvement": True,
    "complete_native_receipt_replay": True,
    "format_failure_holds": True,
    "automatic_retries": 0,
}
SCOPE = (
    "Six paired batches of authored closed-world decisions, fresh-thread upstream "
    "inference tokens including cached input and reasoning subsets once. "
    "Preparation, selection history, whole-project cost and general intelligence "
    "are unmeasured."
)
CEILING_POLICY = (
    "Stop before the next call at the observed ceiling. "
    "An in-flight call can overshoot."
)
BINDINGS = ("request_sha256", "prompt_sha256", "context_sha256", "memory_receipts")


def read_json(path):
    return C._json(Path(path))


def _immutable(path, value):
    """Fixed objects are reusable only if byte-identical; updates become new events."""
    path = Path(path)
    raw = P.encoded(value)
    if len(raw) > P.MAX_BYTES:
        raise ValueError("record exceeds 64 KiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        if P._read_regular(path) != raw:
            raise ValueError("immutable artifact changed: " + str(path)) from None
    else:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    return {"path": path.name, "sha256": C._sha(raw)}


def _bound(oracle, ref):
    if not isinstance(ref, dict) or set(ref) != {"path", "sha256"}:
        raise ValueError("invalid artifact reference")
    from agent_harness.launch import _json

    return _json(C._bound(Path(oracle), ref["path"], ref["sha256"]))


def validate_cases(cases):
    if not isinstance(cases, list) or not 6 <= len(cases) <= 24 or len(cases) % 6:
        raise ValueError("need 6–24 cases in six equal batches")
    ids, tasks = set(), set()
    for case in cases:
        if (
            not isinstance(case, dict)
            or set(case) != {"id", "family", "facts", "output", "expected"}
            or any(
                not isinstance(case[k], str) or not case[k].strip()
                for k in ("id", "family", "facts", "output")
            )
            or case["id"] in ids
            or not isinstance(case["expected"], dict)
            or not case["expected"]
        ):
            raise ValueError("invalid, duplicate or missing oracle case")
        task = P.digest({k: case[k] for k in ("facts", "output")})
        if task in tasks:
            raise ValueError("renamed task repeats an input")
        P.encoded(case["expected"])
        ids.add(case["id"])
        tasks.add(task)
    return cases


def load_cases(path=CASES):
    data = read_json(path)
    if (
        not isinstance(data, dict)
        or set(data) != {"schema", "cases"}
        or data["schema"] != 1
    ):
        raise ValueError("invalid decision suite schema")
    return validate_cases(data["cases"])


def grade(expected, output):
    if (
        not isinstance(expected, dict)
        or not expected
        or not isinstance(output, dict)
        or set(output) != {"answers", "source_ids"}
        or output["source_ids"] != ["task-evidence"]
        or not isinstance(output["answers"], dict)
        or set(output["answers"]) != set(expected)
        or any(not isinstance(v, dict) for v in output["answers"].values())
    ):
        raise ValueError("answer format, citation or case coverage failed")
    return {
        key: int(P.encoded(output["answers"][key]) == P.encoded(value))
        for key, value in expected.items()
    }


def _sources(cases_path):
    paths = [
        Path(__file__),
        Path(cases_path),
        ROOT / ".harness-work/reasoning-eval/check-outcome.py",
        FULL_GUIDE,
    ]
    # Prompt construction and store recovery are also part of the instrument.
    paths.extend(sorted((ROOT / "src/agent_harness").rglob("*.py")))
    return {
        str(path.resolve(strict=True)): C._sha(P._read_regular(path)) for path in paths
    }


def _task(cases):
    public = [{k: c[k] for k in ("id", "facts", "output")} for c in cases]
    return {
        "instruction": "Solve each independent closed-world case using only its facts. "
        "Return one JSON object with answers mapping every case id "
        "to its requested object. "
        "Use exactly the requested fields and types in each object.",
        "evidence": json.dumps(public, ensure_ascii=False, separators=(",", ":")),
    }


def _prepared(actor):
    from agent_harness.launch import prepare as prepare_launch

    prepared = prepare_launch(actor, "request.json", method_policy="existing")
    return {key: prepared[key] for key in BINDINGS}


def _adapt_task(task, comparison, arm, baseline):
    if comparison == "unguided":
        return task, CANDIDATE if arm == "candidate" else None
    evidence = {"cases": read_json_text(task["evidence"]),
                "selected_guidance": baseline if arm == "baseline" else CANDIDATE}
    return {"instruction": task["instruction"] +
            " Apply selected_guidance when relevant; it is advisory, never authority.",
            "evidence": json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))}, None


def read_json_text(text):
    from agent_harness.launch import _json
    return _json(text)


def journal(out):
    folder = Path(out) / "oracle/journal"
    paths = sorted(folder.glob("*.json"))
    if len(paths) > 40 or folder.is_symlink():
        raise ValueError("journal boundary exceeded")
    events, previous = [], None
    for ordinal, path in enumerate(paths, 1):
        event = read_json(path)
        if (
            path.name != f"{ordinal:04}.json"
            or not isinstance(event, dict)
            or set(event) != {"seq", "previous", "kind", "data", "sha256"}
            or event["seq"] != ordinal
            or event["previous"] != previous
            or event["sha256"]
            != P.digest({k: v for k, v in event.items() if k != "sha256"})
        ):
            raise ValueError("journal hash chain changed or has missing events")
        events.append(event)
        previous = event["sha256"]
    return events


def _append(out, kind, data):
    events = journal(out)
    event = {
        "seq": len(events) + 1,
        "previous": events[-1]["sha256"] if events else None,
        "kind": kind,
        "data": data,
    }
    event["sha256"] = P.digest(event)
    _immutable(Path(out) / "oracle/journal" / f"{event['seq']:04}.json", event)
    return event


def prepare(
    out,
    *,
    model,
    effort,
    timeout_seconds=90,
    max_tokens=300000,
    mode="native",
    cases_path=CASES,
    comparison="unguided",
):
    """Freeze only. The separate execute action requires this manifest's digest."""
    if (
        not isinstance(model, str)
        or not model.strip()
        or effort not in ("low", "medium", "high", "xhigh")
        or type(timeout_seconds) is not int
        or not 1 <= timeout_seconds <= 120
        or type(max_tokens) is not int
        or not 1 <= max_tokens <= 350000
        or mode not in ("native", "simulation")
        or comparison not in ("unguided", "existing-full-guide")
    ):
        raise ValueError("need pinned model, effort, timeout and bounded ceiling")
    cases = load_cases(cases_path)
    baseline = FULL_GUIDE.read_text() if comparison == "existing-full-guide" else None
    sources = _sources(cases_path)
    out = Path(out).absolute()
    if out.is_symlink():
        raise ValueError("run directory cannot be linked")
    out.mkdir(parents=True, exist_ok=False)
    out = out.resolve(strict=True)
    oracle = out / "oracle"
    oracle.mkdir()
    batches = []
    for index in range(6):
        selected = cases[index::6]
        task = _task(selected)
        C._prompt(task, CANDIDATE)
        if len(task["evidence"].encode()) > 8192:
            raise ValueError("batch evidence exceeds native input bound")
        refs = {}
        for key, value in (
            ("task", task),
            ("answers", {c["id"]: c["expected"] for c in selected}),
        ):
            ref = _immutable(oracle / key / f"{index + 1}.json", value)
            refs[key] = {**ref, "path": key + "/" + ref["path"]}
        actors = {}
        for arm in ("baseline", "candidate"):
            actor = out / f"{index + 1}-{arm}"
            actor.mkdir(parents=True)
            arm_task, procedure = _adapt_task(task, comparison, arm, baseline)
            if len(arm_task["evidence"].encode()) > 8192:
                raise ValueError("arm evidence exceeds native input bound")
            C._actor(actor, arm_task, procedure)
            actors[arm] = _prepared(actor)
        batches.append(
            {
                "ids": [c["id"] for c in selected],
                **refs,
                "actors": actors,
                "order": ["baseline", "candidate"]
                if index % 2 == 0
                else ["candidate", "baseline"],
            }
        )
    frozen = {
        "schema": "reasoning-iteration/v1",
        "oracle": str(oracle),
        "cases_path": str(Path(cases_path).resolve()),
        "sources": sources,
        "runtime": C._runtime(),
        "mode": mode,
        "model": model,
        "effort": effort,
        "timeout_seconds": timeout_seconds,
        "max_tokens": max_tokens,
        "max_calls": 12,
        "require_complete_usage": True,
        "candidate": CANDIDATE,
        "comparison": comparison,
        "baseline": baseline,
        "acceptance": ACCEPTANCE,
        "batches": batches,
        "scope": SCOPE,
        "ceiling_policy": CEILING_POLICY,
        "native_cli_expected": "0.167.0-alpha.4.1",
        "preparation_model_calls": 0,
    }
    ref = _immutable(oracle / "freeze.json", frozen)
    _append(out, "FROZEN", ref)
    read_freeze(out)
    return {
        "status": "FROZEN_NOT_RUN",
        "freeze_sha256": ref["sha256"],
        "mode": mode,
        "max_calls": 12,
        "max_tokens": max_tokens,
        "ceiling_policy": CEILING_POLICY,
        "promotion": "NOT_GRANTED",
    }


def read_freeze(out):
    out = Path(out).resolve(strict=True)
    events = journal(out)
    if not events or events[0]["kind"] != "FROZEN":
        raise ValueError("frozen input receipt missing")
    frozen = _bound(out / "oracle", events[0]["data"])
    if (
        frozen["oracle"] != str(out / "oracle")
        or frozen["schema"] != "reasoning-iteration/v1"
        or frozen["runtime"] != C._runtime()
        or frozen["candidate"] != CANDIDATE
        or frozen["comparison"] not in ("unguided", "existing-full-guide")
        or frozen["baseline"] != (FULL_GUIDE.read_text() if frozen["comparison"] == "existing-full-guide" else None)
        or frozen["acceptance"] != ACCEPTANCE
        or frozen["sources"] != _sources(frozen["cases_path"])
    ):
        raise ValueError("frozen instrument, input or runtime changed")
    cases = load_cases(frozen["cases_path"])
    for index, batch in enumerate(frozen["batches"]):
        selected = cases[index::6]
        if (
            batch["ids"] != [c["id"] for c in selected]
            or _bound(out / "oracle", batch["task"]) != _task(selected)
            or _bound(out / "oracle", batch["answers"])
            != {c["id"]: c["expected"] for c in selected}
        ):
            raise ValueError("frozen batch inputs or oracle changed")
        for arm, binding in batch["actors"].items():
            actor = out / f"{index + 1}-{arm}"
            task, _ = _adapt_task(_task(selected), frozen["comparison"], arm, frozen["baseline"])
            C._bound(actor, "evidence.md", C._sha(task["evidence"].encode()))
            if _prepared(actor) != binding:
                raise ValueError("frozen actor request, prompt or context changed")
    if len(frozen["batches"]) != 6:
        raise ValueError("missing batch")
    return frozen


def _schedule(frozen):
    return [
        (index, arm)
        for index, batch in enumerate(frozen["batches"])
        for arm in batch["order"]
    ]


def _attempts(out, frozen):
    """Rebuild immutable events. Unreceipted calls stay spent."""
    schedule, rows = _schedule(frozen), []
    for event in journal(out)[1:]:
        data = event["data"]
        if event["kind"] == "CONSUMED":
            index = len(rows)
            if index >= 12 or (rows and not rows[-1].get("receipt")):
                raise ValueError("attempt limit or unresolved consumed trial")
            batch, arm = schedule[index]
            if set(data) != {"ordinal", "batch", "arm", "actor", "request_sha256"} or (
                data["ordinal"],
                data["batch"],
                data["arm"],
                data["actor"],
            ) != (index + 1, batch, arm, f"{batch + 1}-{arm}"):
                raise ValueError("unmatched consumed case set or arm")
            rows.append(dict(data))
        elif event["kind"] in ("RECEIVED", "FAILED"):
            if (
                not rows
                or data.get("ordinal") != len(rows)
                or rows[-1].get("receipt")
                or rows[-1].get("failure")
            ):
                raise ValueError("duplicate or unmatched trial receipt")
            if event["kind"] == "RECEIVED":
                rows[-1]["receipt"] = data["receipt"]
            else:
                rows[-1]["failure"] = data
        else:
            raise ValueError("unknown journal event")
    return rows


def _partial_tokens(receipt):
    usage = receipt.get("observed_usage_not_final", receipt.get("usage"))
    if isinstance(usage, dict) and "inputTokens" in usage:
        usage = {
            k: usage.get(v)
            for k, v in (
                ("input_tokens", "inputTokens"),
                ("output_tokens", "outputTokens"),
            )
        }
    if not isinstance(usage, dict):
        return 0
    counts = [usage.get(k) for k in ("input_tokens", "output_tokens")]
    return sum(n for n in counts if type(n) is int and n >= 0)


def _receipt_grade(out, frozen, row, receipt):
    actor = Path(out) / row["actor"]
    batch = frozen["batches"][row["batch"]]
    task = _bound(frozen["oracle"], batch["task"])
    expected = _bound(frozen["oracle"], batch["answers"])
    task, candidate = _adapt_task(task, frozen["comparison"], row["arm"], frozen["baseline"])
    if frozen["mode"] == "native":
        request = C._request(actor, row["request_sha256"], receipt, frozen)
        tokens = C._complete_tokens(receipt, frozen)
    else:
        request = _bound(
            actor, {"path": "request.json", "sha256": row["request_sha256"]}
        )
        if (
            receipt.get("kind") != "MODEL_FREE_SIMULATION"
            or type(receipt.get("tokens")) is not int
            or receipt["tokens"] <= 0
        ):
            raise ValueError("simulation receipt missing")
        tokens = receipt["tokens"]
    C._bound(actor, "evidence.md", C._sha(task["evidence"].encode()))
    if request["task"] != C._prompt(task, candidate):
        raise ValueError("actual prompt differs from frozen task and candidate")
    from agent_harness.launch import _json

    output = _json(receipt["answer"])
    return grade(expected, output), tokens


def _se(values):
    return statistics.stdev(values) / len(values) ** 0.5 if len(values) > 1 else None


def replay(out):
    """Recheck inputs, event chain, requests, native receipts and exact answers."""
    out = Path(out).resolve(strict=True)
    frozen = read_freeze(out)
    rows = _attempts(out, frozen)
    holds, unknown, observed = [], [], {}
    known, partial, threads, responses = 0, 0, set(), set()
    totals = {"baseline": 0, "candidate": 0}
    referenced = set()
    for row in rows:
        if "receipt" not in row:
            unknown.append(row["ordinal"])
            failure = row.get("failure", {})
            fragments = failure.get("partials", [])
            partial += max(
                [_partial_tokens(_bound(frozen["oracle"], ref)) for ref in fragments],
                default=0,
            )
            referenced.update(ref["path"] for ref in fragments)
            holds.append("failed_or_incomplete_trial")
            continue
        # Hash mismatches are fatal, before any interpretation of the receipt.
        receipt = _bound(frozen["oracle"], row["receipt"])
        referenced.add(row["receipt"]["path"])
        try:
            count = (
                P._native_tokens(receipt)
                if frozen["mode"] == "native"
                else receipt["tokens"]
            )
            if type(count) is not int or count <= 0:
                raise ValueError("invalid usage")
            known += count
            totals[row["arm"]] += count
        except (ValueError, KeyError, TypeError):
            unknown.append(row["ordinal"])
            partial += _partial_tokens(receipt)
        try:
            scores, tokens = _receipt_grade(out, frozen, row, receipt)
            if frozen["mode"] == "native":
                thread = receipt["thread_id"]
                ids = set(
                    receipt["evaluation_boundary"]["provider_usage"][
                        "response_id_sha256"
                    ]
                )
                if thread in threads or ids & responses:
                    raise ValueError("fresh native thread or upstream response reused")
                threads.add(thread)
                responses.update(ids)
            observed[(row["batch"], row["arm"])] = {"scores": scores, "tokens": tokens}
        except (ValueError, TypeError, KeyError) as error:
            holds.append("invalid_trial_" + str(row["ordinal"]) + ": " + str(error))
    orphans = []
    orphan_usage = {}
    for path in sorted((Path(out) / "oracle/receipts").glob("*.json")):
        relative = "receipts/" + path.name
        if relative in referenced:
            continue
        ref = {"path": relative, "sha256": path.stem}
        receipt = _bound(frozen["oracle"], ref)
        orphans.append(ref)
        request = receipt.get("request_sha256")
        unmatched = [
            row
            for row in rows
            if "receipt" not in row and row["request_sha256"] == request
        ]
        if unmatched:
            ordinal = unmatched[0]["ordinal"]
            orphan_usage[ordinal] = max(
                orphan_usage.get(ordinal, 0), _partial_tokens(receipt)
            )
    partial += sum(orphan_usage.values())
    if orphans:
        holds.append("uncommitted_receipt")
    if len(rows) != 12:
        holds.append("missing_trials")
    if known + partial >= frozen["max_tokens"]:
        holds.append("token_ceiling_reached")
    token_diffs, quality_diffs = [], []
    for index in range(6):
        baseline = observed.get((index, "baseline"))
        candidate = observed.get((index, "candidate"))
        if candidate and not all(candidate["scores"].values()):
            holds.append("candidate_wrong_decision")
        if not baseline or not candidate:
            continue
        if any(
            candidate["scores"][key] < value
            for key, value in baseline["scores"].items()
        ):
            holds.append("case_quality_regression")
        token_diffs.append(candidate["tokens"] - baseline["tokens"])
        quality_diffs.append(
            sum(candidate["scores"].values()) - sum(baseline["scores"].values())
        )
    if len(token_diffs) == 6:
        if totals["candidate"] > totals["baseline"]:
            holds.append("candidate_cost_increase")
        if totals["candidate"] >= totals["baseline"] and sum(quality_diffs) <= 0:
            holds.append("no_strict_improvement")
    else:
        holds.append("unmatched_pairs")
    if frozen["mode"] != "native":
        holds.append("simulation_is_not_native_evidence")
    holds = sorted(set(holds))
    return {
        "status": "HOLD" if holds else "PASS_BOUNDED",
        "promotion": "NOT_GRANTED",
        "evidence": (
            "MODEL_FREE_SIMULATION"
            if frozen["mode"] == "simulation"
            else "NATIVE_RECEIPT_REPLAY"
            if len(observed) == 12
            else "NATIVE_EVIDENCE_INCOMPLETE"
        ),
        "holds": holds,
        "consumed_calls": len(rows),
        "usage_complete": len(observed) == 12 and not unknown,
        "known_consumed_tokens": known,
        "partial_tokens_lower_bound": partial,
        "unknown_attempts": unknown,
        "orphan_receipts": orphans,
        "baseline_tokens": totals["baseline"],
        "candidate_tokens": totals["candidate"],
        "paired_token_differences": token_diffs,
        "paired_quality_differences": quality_diffs,
        "token_difference_se": _se(token_diffs),
        "quality_difference_se": _se(quality_diffs),
        "scope": SCOPE,
        "uncertainty": "Six authored batch pairs, descriptive differences "
        "and standard errors only. "
        "No population confidence or generalization claim.",
        "ceiling_policy": CEILING_POLICY,
    }


@contextmanager
def _lock(out):
    path = Path(out) / "oracle/execute.lock"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def _store_receipt(out, value):
    name = P.digest(value) + ".json"
    ref = _immutable(Path(out) / "oracle/receipts" / name, value)
    return {**ref, "path": "receipts/" + name}


def _simulation(frozen, batch, arm):
    expected = _bound(frozen["oracle"], frozen["batches"][batch]["answers"])
    return {
        "kind": "MODEL_FREE_SIMULATION",
        "tokens": 10 if arm == "baseline" else 9,
        "answer": json.dumps({"answers": expected, "source_ids": ["task-evidence"]}),
    }


def execute(out, *, authorized_execute):
    """Resume unstarted slots. Unknown, failed or invalid spent slots hold."""
    out = Path(out).resolve(strict=True)
    with _lock(out):
        frozen = read_freeze(out)
        if authorized_execute != journal(out)[0]["data"]["sha256"]:
            raise ValueError(
                "separate explicit execute authorization must name the frozen digest"
            )
        while True:
            result = replay(out)
            rows = _attempts(out, frozen)
            allowed = {
                "missing_trials",
                "unmatched_pairs",
                "simulation_is_not_native_evidence",
            }
            if len(rows) == 12 or set(result["holds"]) - allowed:
                return result
            index, arm = _schedule(frozen)[len(rows)]
            actor = out / f"{index + 1}-{arm}"
            request = read_json(actor / "request.json")
            read_freeze(out)
            ordinal = len(rows) + 1
            _append(
                out,
                "CONSUMED",
                {
                    "ordinal": ordinal,
                    "batch": index,
                    "arm": arm,
                    "actor": actor.relative_to(out).as_posix(),
                    "request_sha256": P.digest(request),
                },
            )
            try:
                receipt = (
                    C._call(actor, request, frozen)
                    if frozen["mode"] == "native"
                    else _simulation(frozen, index, arm)
                )
            except (
                OSError,
                ValueError,
                TypeError,
                KeyError,
                RuntimeError,
                KeyboardInterrupt,
                SystemExit,
            ) as error:
                data = {
                    "ordinal": ordinal,
                    "error_type": type(error).__name__,
                    "error": redact(str(error))[:512],
                }
                data["partials"] = [
                    _store_receipt(out, read_json(path))
                    for path in (
                        actor / "native.json.failure.json",
                        actor / "native.json",
                    )
                    if path.exists()
                ]
                _append(out, "FAILED", data)
                if isinstance(error, (KeyboardInterrupt, SystemExit)):
                    raise
                return replay(out)
            # Save invalid output and usage before any interpretation can fail.
            ref = _store_receipt(out, receipt)
            _append(out, "RECEIVED", {"ordinal": ordinal, "receipt": ref})
            read_freeze(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    freeze = actions.add_parser("prepare")
    freeze.add_argument("out", type=Path)
    freeze.add_argument("--model", required=True)
    freeze.add_argument(
        "--effort", required=True, choices=["low", "medium", "high", "xhigh"]
    )
    freeze.add_argument("--timeout-seconds", type=int, default=90)
    freeze.add_argument("--max-tokens", type=int, default=300000)
    freeze.add_argument("--comparison", choices=["unguided", "existing-full-guide"], default="unguided")
    freeze.add_argument("--mode", choices=["native", "simulation"], default="native")
    run = actions.add_parser("execute")
    run.add_argument("out", type=Path)
    run.add_argument(
        "--authorized-execute",
        required=True,
        help="Frozen digest, supplied only after owner authorization",
    )
    check = actions.add_parser("check")
    check.add_argument("out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            result = prepare(
                args.out,
                model=args.model,
                effort=args.effort,
                timeout_seconds=args.timeout_seconds,
                max_tokens=args.max_tokens,
                mode=args.mode,
                comparison=args.comparison,
            )
        elif args.action == "execute":
            result = execute(args.out, authorized_execute=args.authorized_execute)
        else:
            result = replay(args.out)
    except (OSError, ValueError, TypeError, KeyError) as error:
        result = {
            "status": "HOLD",
            "promotion": "NOT_GRANTED",
            "error": redact(str(error))[:512],
        }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in ("FROZEN_NOT_RUN", "PASS_BOUNDED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
