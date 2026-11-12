"""Synthetic advisory-confirmation state machine, deliberately without an activation adapter.

These records model human events; their native authenticity is NOT_OBSERVABLE. No rule file,
permission, guard, model, connection or live instruction can be changed through this module.
"""
import json
import math
import uuid
from pathlib import Path

from .presets import _read
from .vault_sources import _bytes, _publish, _sha, _unique_object

RULES = {"reporting.detail": ("brief", "detailed"), "workflow.extra_notes": (True, False)}
RESTORE = {"complete", "cancel", "revoke", "expiry", "continuity-loss"}
REQUEST = {"project_id", "task_id", "session_id", "revision", "purpose", "action", "changes",
           "targets", "effects", "expires_at", "restore_on"}
CONFIRMATION = {"id", "origin", "kind", "project_id", "task_id", "session_id", "digest", "text"}


def digest(value):
    return _sha(_bytes(value))


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > 2048:
        raise ValueError("synthetic contract requires bounded nonempty text")


class Simulation:
    def __init__(self, directory, *, project_id, task_id, session_id, continuity, clock):
        self.directory = Path(directory)
        self.scope = {"project_id": project_id, "task_id": task_id, "session_id": session_id}
        for value in [*self.scope.values(), continuity]:
            _text(value)
        self.continuity, self.clock, self.epoch = continuity, clock, uuid.uuid4().hex
        self._halted_reason, self._write_failed = None, False
        if self.directory.is_symlink():
            raise ValueError("audit directory is redirected")
        self.directory.mkdir(mode=0o700, parents=False, exist_ok=True)
        self._load()
        self._append({"kind": "restart"}, self._normal("restart"))

    def _now(self):
        now = self.clock()
        if type(now) not in (int, float) or not math.isfinite(now):
            raise ValueError("invalid synthetic clock")
        return now

    def _normal(self, reason):
        return {"mode": "NORMAL", "preview": None, "restoration_reason": reason,
                "continuity": self.continuity, "epoch": self.epoch}

    def _load(self):
        if (self.directory.is_symlink() or not self.directory.is_dir()
                or self.directory.stat().st_mode & 0o077):
            raise ValueError("audit directory must be private and not redirected")
        records, total, previous, used = [], 0, None, set()
        paths = sorted(self.directory.iterdir())
        if len(paths) > 1000:
            raise ValueError("audit entry budget exceeded")
        for seq, path in enumerate(paths, 1):
            if path.name != f"{seq:06}.json":
                raise ValueError("audit sequence has a gap or unknown file")
            raw = _read(path, 65536)
            total += len(raw)
            record = json.loads(raw, object_pairs_hook=_unique_object)
            if (total > 4 * 1024 * 1024 or not isinstance(record, dict)
                    or set(record) != {"sequence", "previous", "scope", "event", "state", "sha256"}
                    or record["sequence"] != seq or record["previous"] != previous
                    or record["scope"] != self.scope or _bytes(record) != raw
                    or record["sha256"] != digest({k: v for k, v in record.items() if k != "sha256"})):
                raise ValueError("audit integrity, scope or byte budget failure")
            state = record["state"]
            if (not isinstance(state, dict) or set(state) != {"mode", "preview", "restoration_reason", "continuity", "epoch"}
                    or state["mode"] not in ("NORMAL", "AWAITING_CONFIRMATION", "SIMULATED_ADVISORY")):
                raise ValueError("invalid audit state")
            event = record["event"]
            if not isinstance(event, dict) or event.get("kind") not in ("restart", "preview", "confirm", "restore"):
                raise ValueError("invalid audit event")
            if "confirmation" in event:
                identity = event["confirmation"]["id"]
                if identity in used:
                    raise ValueError("replayed confirmation in audit")
                used.add(identity)
            records.append(record)
            previous = _sha(raw)
        return records, previous, total, used

    def _append(self, event, state, *, expected=None):
        records, previous, total, _ = self._load()
        if expected is not None and previous != expected:
            raise ValueError("audit revision changed")
        record = {"sequence": len(records) + 1, "previous": previous,
                  "scope": self.scope, "event": event, "state": state}
        raw = _bytes({**record, "sha256": digest(record)})
        if len(records) >= 1000 or len(raw) > 65536 or total + len(raw) > 4 * 1024 * 1024:
            raise ValueError("audit budget exceeded; no activation or pruning")
        try:
            _publish(self.directory / f"{len(records) + 1:06}.json", raw)
        except (OSError, ValueError):
            self._halted_reason, self._write_failed = "audit-write-failed", True
            raise

    def _current(self):
        if self._halted_reason is not None:
            raise ValueError("simulator is halted after an audit failure; restart with normal state")
        records, head, _, used = self._load()
        state = records[-1]["state"]
        if state["epoch"] != self.epoch:
            raise ValueError("continuity lost to a newer simulator instance")
        return state, head, used

    def _event(self, event, kind, expected_digest, used):
        if (not isinstance(event, dict) or set(event) != CONFIRMATION
                or any(event.get(key) != value for key, value in self.scope.items())
                or event["origin"] != "human-direct" or event["kind"] != kind
                or event["digest"] != expected_digest):
            raise ValueError("confirmation does not bind this exact scoped synthetic event")
        _text(event["id"])
        _text(event["text"])
        if event["id"] in used:
            raise ValueError("confirmation event was already used")

    def preview(self, request, first_confirmation):
        if (not isinstance(request, dict) or set(request) != REQUEST
                or any(request.get(key) != value for key, value in self.scope.items())
                or type(request["revision"]) is not int or request["revision"] < 1
                or request["action"] != "draft-only"):
            raise ValueError("invalid scoped advisory request")
        _text(request["purpose"])
        if (type(request["expires_at"]) not in (int, float) or not math.isfinite(request["expires_at"])
                or not self._now() < request["expires_at"] <= self._now() + 86400):
            raise ValueError("request needs a future expiry within one day")
        for key in ("targets", "effects", "restore_on"):
            if not isinstance(request[key], list) or not 1 <= len(request[key]) <= 16:
                raise ValueError("request lists must be bounded and explicit")
            for value in request[key]:
                _text(value)
        if set(request["restore_on"]) != RESTORE or len(request["restore_on"]) != len(RESTORE):
            raise ValueError("all fail-closed restoration conditions are required")
        changes = request["changes"]
        if not isinstance(changes, list) or not 1 <= len(changes) <= len(RULES):
            raise ValueError("explicit advisory components required")
        names = []
        for change in changes:
            if not isinstance(change, dict) or set(change) != {"rule", "value"}:
                raise ValueError("invalid advisory component")
            rule = change["rule"]
            if (not isinstance(rule, str) or rule not in RULES
                    or not any(type(change["value"]) is type(v) and change["value"] == v for v in RULES[rule])):
                raise ValueError("protected or unknown components cannot be advisory")
            names.append(rule)
        if len(names) != len(set(names)):
            raise ValueError("duplicate advisory component")
        _, head, used = self._current()
        self._event(first_confirmation, "request", digest(request), used)
        value = json.loads(_bytes({"request": request, "first_event": first_confirmation["id"],
                                  "epoch": self.epoch, "continuity": self.continuity}))
        preview = {"value": value, "sha256": digest(value)}
        state = {**self._normal(None), "mode": "AWAITING_CONFIRMATION", "preview": preview}
        self._append({"kind": "preview", "confirmation": first_confirmation}, state, expected=head)
        return json.loads(_bytes(preview))

    def confirm(self, second_confirmation):
        self.status()
        state, head, used = self._current()
        if state["mode"] != "AWAITING_CONFIRMATION":
            raise ValueError("an unexpired exact first confirmation is required")
        self._event(second_confirmation, "approve", state["preview"]["sha256"], used)
        self._append({"kind": "confirm", "confirmation": second_confirmation},
                     {**state, "mode": "SIMULATED_ADVISORY"}, expected=head)

    def restore(self, reason):
        if reason not in RESTORE:
            raise ValueError("unknown restoration reason")
        _, head, _ = self._current()
        # Losing the audit write must never keep even the simulated override effective.
        self._halted_reason = reason
        try:
            self._append({"kind": "restore", "reason": reason}, self._normal(reason), expected=head)
        except (OSError, ValueError):
            self._write_failed = True
            raise
        self._halted_reason = None

    def status(self, *, continuity=None):
        records, _, _, _ = self._load()
        state = records[-1]["state"]
        if self._halted_reason is not None:
            state = self._normal(self._halted_reason)
        elif state["epoch"] != self.epoch:
            state = self._normal("continuity-loss")
        elif continuity is not None and continuity != self.continuity:
            self.restore("continuity-loss")
            state, _, _ = self._current()
        elif state["preview"] is not None:
            if self._now() >= state["preview"]["value"]["request"]["expires_at"]:
                self.restore("expiry")
                state, _, _ = self._current()
        return {"mode": state["mode"], "restoration_reason": state["restoration_reason"],
                "components": state["preview"]["value"]["request"]["changes"]
                if state["mode"] == "SIMULATED_ADVISORY" else [],
                "preview_sha256": state["preview"]["sha256"] if state["preview"] else None,
                "native_effective_mode": "NORMAL", "execution_authorized": False,
                "native_confirmation_authenticity": "NOT_OBSERVABLE",
                "protected_controls": "NO_WRITE_CAPABILITY", "simulation_only": True,
                "audit_status": "WRITE_FAILED" if self._write_failed else "RECORDED"}
