"""harness: install | uninstall | status | doctor | warmup | update | learn | sync."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shlex
import shutil
import signal
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

if __package__ in (None, ""):  # run as a file: make the package importable
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "agent_harness"

from . import installer as I  # noqa: E402
from .adapters import all_adapters  # noqa: E402

MB = 1024 * 1024
BASE_CAP = 20 * MB
WARM_CAP = 1024 * MB

# Known warm-up plugins: command, what must be on PATH, and a size estimate (download + cache).
PLUGINS = {
    "fetch": {"command": ["uvx", "mcp-server-fetch"], "requires": "uvx", "size_mb": 60,
              "prefetch": ["uvx", "mcp-server-fetch", "--help"]},
    "playwright": {"command": ["npx", "-y", "@playwright/mcp@latest"], "requires": "npx", "size_mb": 450,
                   "prefetch": ["npx", "-y", "@playwright/mcp@latest", "--help"]},
}


def _out(msg: str = "") -> None:
    print(msg, flush=True)


def _paths(args):
    home = Path(args.home).expanduser() if args.home else Path.home()
    return home, I.harness_home(home)


def _profile_dir(args, hh: Path, state: dict) -> Optional[Path]:
    if getattr(args, "profile", None):
        return Path(args.profile).expanduser().resolve()
    if (hh / "profile").is_dir():
        return hh / "profile"
    return None


def kb_index(hh: Path, profile: dict, profile_dir: Optional[Path]) -> str:
    """The always-loaded knowledge index ('' if unavailable). Its roots are exactly the ones the MCP
    server searches (the profile folder's files as their own roots + the profile's kb_paths), so every
    id printed here resolves with kb_get. The profile may name the pages whose section ids are listed
    (`index_pages`, globs); the extra-rules file is left out (it is in the rules already)."""
    from .mcp import kb as kbmod
    paths = (kbmod.profile_folder_roots(Path(profile_dir)) if profile_dir else []) + I.kb_paths(profile, profile_dir)
    paths = [p for p in paths if p.exists()]
    if not paths:
        return ""
    detail = profile.get("index_pages")
    extra = I._pget(profile, "extra_rules", "rules.extra_rules")
    try:
        k = kbmod.KB(home=hh, paths=paths)
        try:
            text = k.build_index(max_bytes=INDEX_CAP, detail=list(detail) if detail else None,
                                 exclude=[Path(str(extra)).name] if extra else [])
        finally:
            getattr(k, "close", lambda: None)()
    except Exception:  # kb absent or broken: the rules still install
        return ""
    return "## Knowledge index\n\n" + text.strip() + "\n" if text.strip() else ""


INDEX_CAP = 4000
DIGEST_CAP = 2048


def memory_digest(hh: Path, project=None) -> str:
    """'## What you remember' from A1's `agent_harness.mcp.memory digest` ('' if none/absent)."""
    lib = hh / "lib"
    if not (lib / "agent_harness" / "mcp" / "memory.py").is_file():
        return ""
    cmd = [sys.executable, "-m", "agent_harness.mcp.memory", "digest"]
    if project:
        cmd += ["--project", str(project)]
    env = dict(os.environ, PYTHONPATH=str(lib), HARNESS_HOME=str(hh))
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    text = p.stdout.strip() if p.returncode == 0 else ""
    if not text:
        return ""
    body = ""
    for line in text.splitlines(keepends=True):
        if len((body + line).encode("utf-8")) > DIGEST_CAP - 40:
            break
        body += line
    return "## What you remember\n\n" + body.rstrip("\n") + "\n"


def build_ctx(home: Path, hh: Path, content: Path, profile_dir: Optional[Path], project, extra_mcp,
              with_index: bool):
    ctx = I.make_ctx(home, hh, content, profile_dir, project, extra_mcp)
    if with_index:
        for extra_part in (kb_index(hh, ctx.profile, profile_dir), memory_digest(hh, project)):
            if extra_part:
                ctx.rules = ctx.rules.rstrip("\n") + "\n\n" + extra_part
    return ctx


def _select(args, ctx, adapters) -> List[str]:
    if args.tools in (None, ""):
        return [n for n, a in adapters.items() if a.detect(ctx)]
    if args.tools == "all":
        return list(adapters)
    names = [t.strip() for t in args.tools.split(",") if t.strip()]
    unknown = [n for n in names if n not in adapters]
    if unknown:
        raise I.InstallError(f"unknown tool(s): {', '.join(unknown)}; known: {', '.join(adapters)}")
    return names


# ---------------------------------------------------------------- install

def _notes(adapter, ctx) -> List[str]:
    fn = getattr(adapter, "notes", None)
    return list(fn(ctx)) if callable(fn) else []


def cmd_install(args) -> int:
    home, hh = _paths(args)
    source = Path(args.source).resolve() if args.source else I.REPO_ROOT
    state = I.load_state(hh)
    profile_dir = _profile_dir(args, hh, state)
    project = Path(args.project).resolve() if args.project else None
    adapters = all_adapters()
    extra = state.get("extra_mcp", {})
    ctx = build_ctx(home, hh, source / "content", profile_dir, project, extra, with_index=False)
    tools = _select(args, ctx, adapters)
    if not tools:
        _out("No supported AI coding tool found. Name one with --tools (" + ", ".join(adapters) + ").")
        return 1
    if not args.dry_run and not args.yes and not I.is_tty():
        _out("Refusing to change your tool setup without a terminal to ask you. Re-run with --yes to accept.")
        return 2
    chosen = []
    for name in tools:
        a = adapters[name]
        for line in I.plan_lines(a, a.plan(ctx)) + [f"  note: {n}" for n in _notes(a, ctx)]:
            _out(line)
        _out("  Warning: " + I.WARNING.format(title=a.title))
        if args.dry_run:
            continue
        if args.yes or I.ask(f"Install for {a.title}?"):
            chosen.append(name)
    if args.dry_run:
        _out("Dry run: nothing was written.")
        return 0
    if not chosen:
        _out("Nothing installed.")
        return 0
    I.copy_harness(hh, source, profile_dir if profile_dir != hh / "profile" else None)
    installed_profile = hh / "profile" if (hh / "profile").is_dir() else None
    ctx = build_ctx(home, hh, hh / "content", installed_profile, project, extra, with_index=True)
    # the content folder was just replaced, so the tools installed earlier are refreshed too (as `update` does):
    # their files live there, and every tool on the machine gets the same rules
    earlier = [n for n in state.get("tools", []) if n in adapters and n not in chosen]
    changes = [(n, adapters[n].plan(ctx)) for n in chosen + earlier]
    state = I.apply(hh, changes, state, [home] + ([project] if project else []))
    state.update({"source": str(source), "project": str(project) if project else None,
                  "tools": sorted(set(state.get("tools", [])) | set(chosen))})
    I.save_state(hh, state)
    state = extensions_step(home, hh, state, ctx, args.yes)
    for n in chosen:
        for note in _notes(adapters[n], ctx):
            _out(f"  {adapters[n].title}: {note}")
        for c in adapters[n].post_install(ctx):
            _out(f"  ({adapters[n].title}: if the harness server does not show up, run: {c})")
    _out(f"Installed for {', '.join(adapters[n].title for n in chosen)}. "
         "Next: restart the tool, then run `harness doctor` to check it.")
    return 0


def _real_home(home: Path) -> bool:
    """Editor CLIs can escape HOME overrides; compare with the account home on POSIX."""
    try:
        if os.name == "posix":
            import pwd
            account_home = Path(pwd.getpwuid(os.getuid()).pw_dir)
        else:
            account_home = Path.home()
        return Path(home).resolve() == account_home.resolve()
    except (ImportError, KeyError, OSError):
        return False


def extensions_step(home: Path, hh: Path, state: dict, ctx, yes: bool, budget_bytes=None) -> dict:
    """Editor settings (through the installer, so uninstall undoes them) and curated extensions.
    Editor CLIs install into the REAL user's editor, so they only run when `home` is the real HOME."""
    try:
        from . import extensions as X
    except ImportError:
        return state
    catalog = hh / "content" / X.CATALOG
    tools = state.get("tools", [])
    if catalog.is_file():
        changes, refused = X.settings_changes(ctx, catalog, tools)
        for r in refused:
            _out(f"  editor settings: {r}")
        if changes:
            for ch in changes:
                _out(f"  merge into {ch.path} - {ch.note}")
            if yes or (I.is_tty() and I.ask("Apply these editor settings?")):
                state = I.apply(hh, [("editor-settings", changes)], state)
                I.save_state(hh, state)
    if not _real_home(home):
        _out("Editor extensions: skipped (HOME override; editor CLIs act on your real HOME).")
        return state
    kw = {} if budget_bytes is None else {"budget_bytes": budget_bytes}
    state = X.install(hh, state, tools=tools, yes=yes, log=_out, **kw)
    I.save_state(hh, state)
    return state


def _reapply(hh: Path, home: Path, state: dict) -> None:
    adapters = all_adapters()
    project = Path(state["project"]) if state.get("project") else None
    profile_dir = hh / "profile" if (hh / "profile").is_dir() else None
    ctx = build_ctx(home, hh, hh / "content", profile_dir, project, state.get("extra_mcp", {}), True)
    changes = [(n, adapters[n].plan(ctx)) for n in state.get("tools", []) if n in adapters]
    state = I.apply(hh, changes, state)
    I.save_state(hh, state)


def cmd_uninstall(args) -> int:
    home, hh = _paths(args)
    for f in ("notices.json", ".notices-mcp-day"):  # pending notices go with the setup (mcp/server.py)
        try:
            (hh / f).unlink()
        except OSError:
            pass
    if not I.load_state(hh):
        _out("Nothing to uninstall.")
        return 0
    state = I.load_state(hh)
    if state.get("extensions"):
        try:
            from . import extensions as X
            I.save_state(hh, X.uninstall(state, log=_out))
        except ImportError:
            pass
    done = I.uninstall(hh, _out)
    _out(f"Restored {len(done)} path(s). Memory and lessons are kept in {hh}.")
    return 0


def cmd_status(args) -> int:
    if getattr(args, "runtime", False):
        from . import runtime_inventory
        _, hh = _paths(args)
        report = runtime_inventory.inspect_runtime(hh, launcher=sys.argv[0])
        _out(json.dumps(report, indent=1) if args.json else runtime_inventory.render(report))
        return 0
    if getattr(args, "matrix", False):
        from . import matrix
        m = matrix.matrix(sorted(all_adapters()))
        _out(json.dumps(m, indent=1) if args.json else matrix.render(m))
        return 0
    home, hh = _paths(args)
    state = I.load_state(hh)
    if not state:
        _out(f"Not installed (HARNESS_HOME {hh}).")
        return 1
    _out(f"Installed in {hh} for: {', '.join(state.get('tools', []))}")
    for e in state.get("entries", []):
        p = Path(e["path"])
        mark = "ok" if I.path_hash(p) == e.get("written") else ("missing" if not p.exists() else "changed")
        _out(f"  [{mark}] {p}  ({', '.join(e['tools'])})")
    if state.get("extra_mcp"):
        _out("Plugins: " + ", ".join(state["extra_mcp"]))
    return 0


# ---------------------------------------------------------------- doctor

def mcp_probe(cmd: List[str], timeout: float = 5.0) -> Optional[List[str]]:
    """Start the server, ask tools/list, return the tool names (None on failure)."""
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "harness-doctor", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    data = "".join(json.dumps(m) + "\n" for m in msgs)
    try:
        p = subprocess.run(cmd, input=data, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    for line in p.stdout.splitlines():
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if msg.get("id") == 2 and "result" in msg:
            return [t.get("name") for t in msg["result"].get("tools", [])]
    return None


def cmd_explain(args) -> int:
    from . import diagnose
    home, _ = _paths(args)
    path = args.session or diagnose.latest(args.client, home, None if args.client == "codex" else Path.cwd())
    if not path:
        _out("No %s session found." % args.client)
        return 1
    r = diagnose.explain(args.client, path, home)
    _out(json.dumps(r, indent=1) if args.json else diagnose.render(r))
    return 0


def cmd_doctor(args) -> int:
    home, hh = _paths(args)
    state = I.load_state(hh)
    checks = []

    def check(ok: bool, what: str, hint: str = ""):
        checks.append(ok)
        _out(f"[{'ok' if ok else 'FAIL'}] {what}" + ("" if ok or not hint else f" - {hint}"))

    check(sys.version_info >= (3, 9), f"python {sys.version.split()[0]}", "needs Python 3.9 or newer")
    try:
        sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        fts = True
    except sqlite3.Error:
        fts = False
    _out(f"[{'ok' if fts else 'info'}] SQLite FTS5 " + ("available" if fts else "missing; search uses the slower fallback"))
    if not state:
        check(False, "harness installed", "run `harness install`")
        return 1
    for e in state.get("entries", []):
        p = Path(e["path"])
        check(p.exists() or p.is_symlink(), f"{', '.join(e['tools'])}: {p}", "missing; re-run `harness install`")
    server = hh / "lib" / "agent_harness" / "mcp" / "server.py"
    if server.is_file():
        names = mcp_probe(I.mcp_cmd(hh))
        check(bool(names), "MCP server answers tools/list within 5 s" + (f" ({len(names)} tools)" if names else ""),
              "the server did not answer; run it by hand: " + " ".join(shlex.quote(x) for x in I.mcp_cmd(hh)))
    else:
        check(False, "MCP server present", f"{server} missing; run `harness update`")
    from . import storage
    try:
        storage.prune(hh)                        # every store back under its own cap first
    except Exception as e:
        _out(f"[info] pruning stopped early: {e}")
    size = I.dir_size(hh)
    cap = WARM_CAP if state.get("extra_mcp") else BASE_CAP
    rep = storage.report(hh, apparent=True)
    check(size < cap, f"disk footprint {size / MB:.1f} MB (cap {cap // MB} MB)",
          "over the cap; largest: " + ", ".join(f"{n} {storage.human(b)}" for n, b in rep["largest"][:3]))
    cc = home / ".claude" / "projects"
    if cc.is_dir():
        _out(f"[info] Claude Code's own transcripts {storage.human(I.dir_size(cc))} in {cc} (not the harness's; "
             "Claude Code keeps them for cleanupPeriodDays)")
    return 0 if all(checks) else 1


# ---------------------------------------------------------------- warmup

def plugin_specs(profile: dict, include_optional: bool = False) -> dict:
    out = {}
    for p in ((profile.get("warmup") or {}).get("plugins") or []):
        if isinstance(p, str):
            if p in PLUGINS:
                out[p] = dict(PLUGINS[p])
            else:
                _out(f"  unknown plugin {p!r} (known: {', '.join(PLUGINS)}); skipped")
        elif isinstance(p, dict) and p.get("name") and p.get("command"):
            if p.get("optional") and not include_optional:
                _out(f"  {p['name']}: optional; add --include-optional to install it")
                continue
            cmd = p["command"] if isinstance(p["command"], list) else [p["command"]] + list(p.get("args", []))
            known = PLUGINS.get(p["name"], {})
            out[p["name"]] = {"command": cmd, "requires": p.get("requires", cmd[0]),
                              "size_mb": int(p.get("est_mb", p.get("size_mb", known.get("size_mb", 100)))),
                              "prefetch": p.get("prefetch", known.get("prefetch"))}
    return out


def cmd_warmup(args) -> int:
    home, hh = _paths(args)
    state = I.load_state(hh)
    if not state:
        _out("Install first: `harness install`.")
        return 1
    if args.background:
        log = hh / "warmup.log"
        argv = [sys.executable, "-m", "agent_harness.cli", "--home", str(home), "warmup"]
        if args.include_optional:
            argv.append("--include-optional")
        if args.yes:
            argv.append("--yes")
        env = dict(os.environ, PYTHONPATH=str(I.PKG_DIR.parent))
        with open(log, "ab") as f:
            subprocess.Popen(argv, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             env=env, start_new_session=True)
        _out(f"Warm-up running in the background; log: {log}")
        return 0
    try:
        from .mcp import kb as kbmod
        k = kbmod.KB(home=hh)
        stats = k.refresh()
        getattr(k, "close", lambda: None)()
        _out(f"Knowledge index built: {stats}")
    except Exception as e:
        _out(f"Knowledge index skipped ({type(e).__name__}: {e})")
    profile = I.load_profile(hh / "profile")
    specs = plugin_specs(profile, args.include_optional)
    extra = dict(state.get("extra_mcp", {}))
    budget = WARM_CAP - I.dir_size(hh)
    for name, spec in specs.items():
        if name in extra:
            continue
        if not shutil.which(spec["requires"]):
            _out(f"  {name}: needs `{spec['requires']}` on PATH; skipped")
            continue
        need = spec["size_mb"] * MB
        if need > budget:
            _out(f"  {name}: about {spec['size_mb']} MB would exceed the 1 GB cap; skipped")
            continue
        if spec.get("prefetch"):
            try:
                subprocess.run(spec["prefetch"], capture_output=True, timeout=600)
            except (OSError, subprocess.TimeoutExpired):
                _out(f"  {name}: download failed; skipped")
                continue
        budget -= need
        extra[name] = spec["command"]
        _out(f"  {name}: ready (about {spec['size_mb']} MB)")
    if extra != state.get("extra_mcp", {}):
        state["extra_mcp"] = extra
    _reapply(hh, home, state)
    state = I.load_state(hh)
    profile_dir = hh / "profile" if (hh / "profile").is_dir() else None
    ctx = build_ctx(home, hh, hh / "content", profile_dir,
                    Path(state["project"]) if state.get("project") else None, state.get("extra_mcp", {}), False)
    extensions_step(home, hh, state, ctx, args.yes, budget_bytes=max(budget, 0))
    _out("Warm-up done. Restart your tools to pick up the changes.")
    return 0


# ---------------------------------------------------------------- update / learn

def cmd_update(args) -> int:
    home, hh = _paths(args)
    state = I.load_state(hh)
    if not state:
        _out("Install first: `harness install`.")
        return 1
    source = Path(args.source or state.get("source") or I.REPO_ROOT).resolve()
    if not (source / "content").is_dir():
        _out(f"No harness source at {source}; pass --source DIR.")
        return 1
    profile = Path(args.profile).expanduser().resolve() if args.profile else None
    if profile and not (profile / "profile.toml").is_file():
        _out(f"No profile.toml in {profile}.")
        return 1
    I.copy_harness(hh, source, profile)
    state["source"] = str(source)
    _reapply(hh, home, state)
    _out(f"Updated from {source}; memory and lessons kept.")
    return 0


def cmd_learn(args) -> int:
    home, hh = _paths(args)
    d = hh / "lessons"
    items = []
    for f in sorted(d.glob("*.json")) if d.is_dir() else []:
        try:
            items.append(json.loads(f.read_text(encoding="utf-8")))
        except ValueError:
            continue
    if not items:
        _out("No lessons recorded yet.")
        return 0
    items.sort(key=lambda x: -int(x.get("uses", 0) or 0))
    _out(f"{len(items)} lesson(s), most used first:")
    for x in items:
        _out(f"- when {x.get('trigger', '?')}: {x.get('fix', '?')}  (was: {x.get('mistake', '?')}; used {x.get('uses', 0)}x)")
    return 0


# ---------------------------------------------------------------- sync

def cmd_sync(args) -> int:
    from . import sync as S
    home, hh = _paths(args)
    cfg_file = hh / "sync.json"
    cfg = json.loads(cfg_file.read_text()) if cfg_file.is_file() else {}
    remote = args.remote or cfg.get("remote")
    ssh_cmd = args.ssh_cmd or cfg.get("ssh_cmd") or "ssh"
    if args.config:
        if not args.remote:
            _out("harness sync --config needs --remote <ssh-target>:<remote HARNESS_HOME>.")
            return 1
        hh.mkdir(parents=True, exist_ok=True)
        cfg_file.write_text(json.dumps({"remote": args.remote, "ssh_cmd": ssh_cmd}, indent=1) + "\n")
        _out(f"Saved: `harness sync` now syncs with {args.remote}.")
        return 0
    if not remote:
        _out("No remote. Run `harness sync --config --remote <ssh-target>:<remote HARNESS_HOME>` once.")
        return 1
    try:
        for line in S.run_sync(hh, remote, ssh_cmd, args.dry_run):
            _out(line)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
        _out(f"harness sync: {e}")
        return 1
    return 0


# ---------------------------------------------------------------- Claude Code Stop hook

STOP_REASON = ("Files changed: before you finish, run this project's checks (tests, linters, type checks) "
               "on what you changed and report the result, or say why not. Then session_note in one line, and "
               "state_save if the work is unfinished.")
# D2 (run_checks on): the gate is the recorded result, not a reminder. Blocks once per user turn.
GATE_REASON = ("Files changed since the last passing run_checks ({why}): call run_checks and report its result, "
               "or say why this project cannot be checked. Then session_note in one line.")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
# Arm skill_nudge (HARNESS_ENABLE=skill_nudge; off by default until the eval shows it helps): after a long turn
# with no skill saved, one reminder, as Hermes' post-session review but inside the session.
NUDGE_TOOLS = 10   # the calibration's first sessions of repeat questions took 11-16 tool calls
NUDGE_REASON = ("Long task: if a method recurred on distinct task inputs, use skill_manage draft with bound "
                "source episodes; independent comparison is required before use. Otherwise finish.")


def _own_memory(path: str) -> bool:
    """A write to the assistant's own memory (~/.claude, the harness home) is not a project edit: the eval's
    'remember ...' sessions were sent back to run checks after saving a memory file."""
    if not path:
        return False
    try:
        p = Path(os.path.expanduser(path)).resolve()
    except (OSError, RuntimeError):
        return False
    for root in (Path.home() / ".claude", I.harness_home(Path.home())):
        try:
            p.relative_to(root.resolve())
            return True
        except (ValueError, OSError):
            continue
    return False


def stop_hook(stdin=None) -> int:
    """Once per user turn, and only when files were edited in that turn: with run_checks (D2), block while
    no passing run_checks covers the current files; without it, ask for the checks. Never loops."""
    try:
        data = json.loads((stdin or sys.stdin).read() or "{}")
        try:   # candidate lessons first, also after the harness's own block: its marker records a turn once
            from . import capture
            capture.capture_turn(I.harness_home(Path.home()), data["transcript_path"],
                                 str(data.get("session_id")), project=Path.cwd())
        except Exception:
            pass
        if data.get("stop_hook_active"):
            return 0
        last_user, edited, n_tools, skill_saved = None, False, 0, False
        with open(data["transcript_path"], encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                content = (e.get("message") or {}).get("content")
                if e.get("type") == "user":
                    if isinstance(content, str) or any(
                            isinstance(c, dict) and c.get("type") == "text" for c in content or []):
                        last_user, edited, n_tools, skill_saved = e.get("uuid") or line[:64], False, 0, False
                elif e.get("type") == "assistant" and isinstance(content, list):
                    uses = [c for c in content if isinstance(c, dict) and c.get("type") == "tool_use"]
                    n_tools += len(uses)
                    skill_saved |= any(str(c.get("name", "")).endswith("skill_manage") for c in uses)
                    edited |= any(c.get("name") in EDIT_TOOLS
                                  and not _own_memory(str((c.get("input") or {}).get("file_path") or ""))
                                  for c in uses)
        from .mcp import checks
        reason = ""
        if edited:
            reason = STOP_REASON
            from .mcp.state import project_root
            root = project_root(data.get("cwd") or None)
            if not checks.disabled("run_checks") and checks.gated(root) and checks.fingerprint(root):
                stale, why = checks.unchecked_changes(root)
                reason = GATE_REASON.format(why=why) if stale else ""
        if not checks.disabled("skill_nudge") and n_tools >= NUDGE_TOOLS and not skill_saved:
            reason = (reason + " " + NUDGE_REASON).strip()
        if not reason:
            return 0
        hh = I.harness_home(Path.home())
        marker = hh / "state" / f"stop-{data.get('session_id', 'x')}"
        if marker.is_file() and marker.read_text() == str(last_user):
            return 0
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(last_user))
        print(json.dumps({"decision": "block", "reason": reason}))
    except Exception:
        pass  # a hook must never break the tool
    return 0


def capture_hook(stdin=None) -> int:
    """A Stop hook that only records candidate lessons: for a setup that keeps its own rules and hooks and wants
    nothing else from the harness at turn end (no check reminder, never blocks). Always exits 0, prints nothing."""
    try:
        data = json.loads((stdin or sys.stdin).read() or "{}")
        from . import capture
        capture.capture_turn(I.harness_home(Path.home()), data["transcript_path"],
                             str(data.get("session_id")), project=Path.cwd())
    except Exception:
        pass
    return 0


RECALL_TIMEOUT = 2.0


def context_hook(stdin=None) -> int:
    """SessionStart context recovery; errors do not block the user's session."""
    from .mcp.memory import Memory
    from .mcp.state import State
    memory = None
    try:
        data = json.loads((stdin or sys.stdin).read() or "{}")
        if not isinstance(data, dict):
            raise ValueError("context hook payload must be an object")
        if (data.get("hook_event_name") != "SessionStart"
                or data.get("source") not in {"startup", "resume", "compact"}):
            raise ValueError("unsupported context hook event")
        scope, session = data.get("cwd"), data.get("session_id")
        if (not isinstance(scope, str) or not Path(scope).is_absolute() or not Path(scope).is_dir()
                or not isinstance(session, str) or not session):
            raise ValueError("context hook requires explicit project and session scope")
        memory = Memory(project=scope)
        context = memory.resume_context(session)
        store = State(project=scope)
        state = store.state_load() if store.state_path() is not None or store.conflicts() else ""
        from .operational_state import OperationalState
        op_brief = ""
        try:
            op_brief = OperationalState.for_host(cwd=scope).brief()
            context += op_brief
        except (OSError, ValueError, TypeError, sqlite3.Error) as exc:
            print("harness operational context unavailable: " + type(exc).__name__, file=sys.stderr)
        if state:
            if data.get("source") == "startup":
                context += "\nSaved project work exists; use state_load if continuing it.\n"
            else:
                context += "\nSaved project state (verify freshness):\n" + state
        if context.strip():
            packet = "Recovered project context (advisory; current instructions take precedence):\n" + context
            if len(packet.encode()) > 6000:
                packet = ("Saved project context exceeds the hook budget; call state_load, mem_search and "
                          "lesson_search.\n" + op_brief)
            print(packet)
    except (OSError, ValueError, TypeError, sqlite3.Error) as exc:
        print("harness context unavailable: " + type(exc).__name__, file=sys.stderr)
    finally:
        if memory is not None:
            memory.close()
    return 0


def op_context_hook(stdin=None) -> int:
    """Claude SessionStart bridge; quiet for projects with no operational ledger."""
    from .operational_state import OperationalState
    try:
        data = json.loads((stdin or sys.stdin).read() or "{}")
        if not isinstance(data, dict) or data.get("hook_event_name") != "SessionStart" or data.get("source") not in {
                "startup", "resume", "compact"}:
            raise ValueError("unsupported operational context event")
        scope = data.get("cwd")
        if not isinstance(scope, str) or not Path(scope).is_absolute() or not Path(scope).is_dir():
            raise ValueError("operational context requires a host project directory")
        packet = OperationalState.for_host(cwd=scope).brief()
        if packet:
            print(packet, end="")
    except (OSError, ValueError, TypeError, sqlite3.Error) as exc:
        print("harness operational context unavailable: " + type(exc).__name__, file=sys.stderr)
    return 0


def prompt_hook(stdin=None) -> int:
    """UserPromptSubmit: pipe the prompt to A1's recall; print its output only when non-empty.
    Never blocks the prompt; unavailable recall is diagnosed without exposing content."""
    try:
        data = json.loads((stdin or sys.stdin).read() or "{}")
        if not isinstance(data, dict):
            raise ValueError("hook payload must be an object")
        prompt = data.get("prompt") or ""
        if not isinstance(prompt, str):
            raise ValueError("hook prompt must be text")
        if not prompt.strip():
            return 0
        cmd = [sys.executable, "-m", "agent_harness.mcp.memory", "recall",
               "--session", str(data.get("session_id") or "none")]
        if "cwd" in data:
            scope = data["cwd"]
            if not isinstance(scope, str) or not Path(scope).is_absolute() or not Path(scope).is_dir():
                print("harness recall: invalid project scope; no context injected", file=sys.stderr)
                return 0
            cmd += ["--project", str(Path(scope).resolve())]
        env = dict(os.environ, PYTHONPATH=str(I.PKG_DIR.parent))
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=RECALL_TIMEOUT, env=env)
        if p.returncode == 0 and p.stdout.strip():
            sys.stdout.write(p.stdout if p.stdout.endswith("\n") else p.stdout + "\n")
        elif p.returncode != 0:
            print("harness recall unavailable: subprocess exit %s" % p.returncode, file=sys.stderr)
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired) as exc:
        print("harness recall unavailable: " + type(exc).__name__, file=sys.stderr)
    return 0


def cmd_self_update(args) -> int:
    from . import selfupdate
    home, hh = _paths(args)
    rc, msg = selfupdate.run(hh, home, check_only=args.check, now=args.now)
    _out(msg)
    return rc


def cmd_improve(args) -> int:
    from . import improve
    _, hh = _paths(args)
    if args.weekly_intake:
        if any((args.propose, args.draft_procedure, args.correct_procedure,
                args.rollback, args.apply, args.trend)):
            _out("intake: HOLD — weekly intake cannot also draft, apply, roll back or judge a release")
            return 1
        from .weekly_intake import take
        try:
            result = take(hh, since=args.since, max_items=args.max_items,
                          max_output_bytes=args.max_output_bytes)
        except (OSError, ValueError) as error:
            _out("intake: HOLD — " + str(error))
            return 1
        # One compact wire format regardless of --json: otherwise the human
        # rendering could exceed the budget after the cursor had advanced.
        _out(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    if args.draft_procedure or args.correct_procedure or args.rollback or (args.apply and args.apply.startswith("pr-")):
        from . import procedures
        try:
            if args.correct_procedure and (not args.draft_procedure or any((args.rollback, args.apply,
                                                                            args.trend, args.propose, args.eval))):
                raise ValueError("--correct-procedure needs one --draft-procedure file and no other action")
            if args.draft_procedure:
                candidate = procedures.read_json(args.draft_procedure)
                result = (procedures.correct(hh, args.project, args.correct_procedure, candidate)
                          if args.correct_procedure else procedures.draft(hh, args.project, candidate))
            else:
                evidence = procedures.read_json(args.eval) if args.eval else None
                result = procedures.change(hh, args.project, args.rollback or args.apply,
                                           evidence, rollback=bool(args.rollback))
            _out(json.dumps(result))
            return 0
        except (OSError, ValueError, TypeError, KeyError) as exc:
            _out("improve: refused: " + str(exc))
            return 1
    if args.trend:
        rc, msg = improve.trend(args.trend, args.release, args.new_baseline)
    elif args.apply:
        rc, msg = improve.apply(hh, args.apply, args.eval)
    elif args.propose:
        props = improve.propose(hh)
        rc = 0
        msg = json.dumps(props, indent=1) if args.json else "\n".join(
            "%s  seen %sx  [%s] %s" % (p["id"], p["count"], p["source"], p["summary"]) for p in props) or \
            "improve: nothing has recurred yet"
    else:
        rc, msg = 2, "harness improve: --propose, --apply ID --eval FILE, or --trend HISTORY"
    _out(msg)
    return rc


def cmd_discover(args) -> int:
    from . import discover as D
    _, hh = _paths(args)
    if args.install:
        rc, msg = D.install(args.install, args.approve, args.override, hh, args.catalog, not args.no_network)
        _out(msg)
        return rc
    if not args.need.strip():
        _out("harness discover: say what you need, e.g. harness discover \"postgres\"")
        return 2
    recs = D.search(args.need, args.catalog, not args.no_network, hh=hh)
    _out(D.results_json(recs) if args.json else D.render(recs))
    return 0


def cmd_run(args) -> int:
    """`plan run` from the harness's own engine: one node per worker, the node's routing tier, and only the
    gate's exit code marks a node done. plan/<slug>.STOP halts it between rounds."""
    engine = I.PKG_DIR / "workgraph" / "bin" / "plan"
    # Streamed line by line: a drain runs for hours, and its round status, held nodes and gate failures are
    # what the person watching needs while it runs, not after; Ctrl-C reaches the engine as SIGINT.
    p = subprocess.Popen([str(engine), "run", args.slug, "--workers", str(max(1, args.workers))],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                         env=dict(os.environ, PYTHONUNBUFFERED="1"), start_new_session=True)
    # The engine runs in its own session, so a stop reaches it only through here: Ctrl-C (SIGINT), a closed
    # terminal (SIGHUP) or a kill (SIGTERM), from the terminal or sent to this process alone, is forwarded
    # exactly once. A second would land in its cleanup and leave claimed nodes leased for hours.
    got = []
    stops = (signal.SIGINT, signal.SIGHUP, signal.SIGTERM)

    def forward(signum, _frame):
        if not got:
            got.append(signum)
            for s in stops:
                signal.signal(s, signal.SIG_IGN)
            try:   # its whole process group: a gate the engine is running stops too, not only the engine
                os.killpg(p.pid, signum)
            except OSError:
                p.send_signal(signum)
    old = {s: signal.signal(s, forward) for s in stops}
    try:
        for line in p.stdout:
            try:
                _out(line.rstrip("\n"))
            except OSError:
                pass                                     # the terminal is gone (SIGHUP): keep draining
        rc = p.wait()
    finally:
        for s, h in old.items():
            signal.signal(s, h)
    return 128 + got[0] if got else rc


def cmd_review(args) -> int:
    from . import review
    from .mcp.state import project_root
    if args.gate:
        rc, msg = review.gate(args.gate, Path(project_root(None)))
        _out(msg)
        return rc
    if not args.run:
        _out("harness review: --run to review the changes, --gate FILE to check a review")
        return 2
    home, _ = _paths(args)
    root = Path(project_root(None))
    out = args.out or review.default_out(root)
    rc, msg = review.run(args.base, out, home, root=root)
    _out(msg)
    return rc


# ---------------------------------------------------------------- main

def cmd_vault_read(args) -> int:
    from .vault_sources import read_shared_source
    try:
        result = read_shared_source(args.vault_root, vault_id=args.vault_id, source=args.source,
                                    sha256=args.sha256, start_line=args.start_line,
                                    end_line=args.end_line, max_bytes=args.max_bytes)
    except (OSError, ValueError) as error:
        print(f"harness vault-read: {error}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_vault_document(args) -> int:
    from .vault_sources import read_shared_document
    try:
        result = read_shared_document(args.vault_root, vault_id=args.vault_id, manifest=args.manifest,
                                      manifest_sha256=args.manifest_sha256, document_id=args.document_id,
                                      start_line=args.start_line, end_line=args.end_line, max_bytes=args.max_bytes)
    except (OSError, ValueError) as error:
        print(f"harness vault-document: {error}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_vault_search(args) -> int:
    from .vault_retrieval import search_shared_documents
    try:
        result = search_shared_documents(args.vault_root, vault_id=args.vault_id, manifest=args.manifest,
                                          manifest_sha256=args.manifest_sha256, allowed_ids=args.allow_id,
                                          query=args.query, backend=args.backend,
                                          max_results=args.max_results, max_bytes=args.max_bytes,
                                          context_lines=args.context_lines)
    except (OSError, ValueError) as error:
        print(f"harness vault-search: {error}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0


def _memory_object(raw, label):
    def unique_object(pairs):
        value = dict(pairs)
        if len(value) != len(pairs):
            raise ValueError(f"duplicate field in memory {label}")
        return value

    if len(raw.encode("utf-8")) > 1024:
        raise ValueError(f"memory {label} exceeds the 1024-byte input budget")
    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except json.JSONDecodeError:
        raise ValueError(f"memory {label} must be a JSON object") from None
    if not isinstance(value, dict):
        hint = "; omit --cursor for the first page" if label == "cursor" else ""
        raise ValueError(f"memory {label} must be a JSON object{hint}")
    return value


def cmd_memory_page(args) -> int:
    from .project_memory import ProjectMemory
    try:
        cursor = _memory_object(args.cursor, "cursor") if args.cursor is not None else None
        store = ProjectMemory(args.project_root, args.project_id)
        result = store.search_page(args.query, allowed_sensitivities=args.allow_sensitivity,
                                   allowed_scopes=args.allow_scope, layers=args.layer, cursor=cursor,
                                   page_size=args.page_size, max_bytes=args.max_bytes)
    except (OSError, ValueError) as error:
        print(f"harness memory-page: {error}", file=sys.stderr)
        return 2
    # The API budgets UTF-8 JSON bytes, irrespective of the caller's terminal encoding.
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    return 0


def cmd_memory_read(args) -> int:
    from .project_memory import ProjectMemory
    try:
        receipt = _memory_object(args.receipt, "receipt")
        store = ProjectMemory(args.project_root, args.project_id)
        scope = {"allowed_sensitivities": args.allow_sensitivity, "allowed_scopes": args.allow_scope,
                 "layers": args.layer, "max_bytes": args.max_bytes}
        if args.recover:
            if args.historical:
                raise ValueError("--recover cannot be combined with --historical")
            verified = (_memory_object(args.verified_receipt, "verified receipt")
                        if args.verified_receipt is not None else None)
            result = store.recover(receipt, phase=args.recover, depends_on_memory=True,
                                   verified_receipt=verified, **scope)
        else:
            if args.verified_receipt is not None:
                raise ValueError("--verified-receipt requires --recover")
            result = store.read_scoped(receipt, historical=args.historical, **scope)
    except (OSError, ValueError) as error:
        print(f"harness memory-read: {error}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    return 0


def cmd_op(args) -> int:
    from .operational_state import Conflict, OperationalState, dispatch
    try:
        if args.action == "snapshot":
            request = {"action": "snapshot"}
        elif args.action == "changes":
            request = {"action": "changes", "cursor": args.cursor, "limit": args.limit}
        else:
            raw = sys.stdin.read(8193)
            if len(raw.encode("utf-8")) > 8192:
                raise ValueError("operational request exceeds 8192 bytes")
            def unique(pairs):
                value = dict(pairs)
                if len(value) != len(pairs):
                    raise ValueError("duplicate operational request field")
                return value
            request = json.loads(raw, object_pairs_hook=unique)
            if not isinstance(request, dict):
                raise ValueError("operational request must be a JSON object")
            if request.get("action", args.action) != args.action:
                raise ValueError("operational action does not match command")
            request["action"] = args.action
        result = dispatch(OperationalState.for_host(), request)
    except (OSError, ValueError, Conflict, json.JSONDecodeError) as error:
        print(f"harness op: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_task(args) -> int:
    """Human-facing view of the same host-scoped operational ledger as MCP op_state."""
    from .operational_state import OperationalState, dispatch
    try:
        checkpoint_fields = ("goal", "stage", "summary", "next", "resource", "checkpoint", "evidence")
        if args.action != "checkpoint" and any(getattr(args, key) is not None for key in checkpoint_fields):
            raise ValueError("checkpoint fields require the checkpoint action")
        if args.action != "stop" and args.reason is not None:
            raise ValueError("reason requires the stop action")
        if args.action in ("status", "evidence") and (args.expected is not None or args.request_id is not None):
            raise ValueError("read-only task actions do not accept mutation fields")
        store = OperationalState.for_host()
        if args.action in ("status", "evidence"):
            if args.action == "evidence" and not args.task:
                raise ValueError("evidence needs a task id")
            result = dispatch(store, {"action": args.action, **({"task": args.task} if args.task else {})})
        else:
            if not args.task:
                raise ValueError("checkpoint, stop and resume need a task id")
            if args.request_id is not None and args.expected is None:
                raise ValueError("--request-id requires --expected so a retry preserves its original version")
            snapshot = store.snapshot()
            row = next((item for item in snapshot["tasks"] if item["task"] == args.task), None)
            expected = args.expected if args.expected is not None else row["version"] if row else 0
            request = {"action": args.action, "task": args.task, "expected": expected,
                       "request_id": args.request_id or "cli-" + secrets.token_hex(16)}
            if args.action == "checkpoint":
                value = dict(row["value"]) if row else {}
                for key in ("goal", "stage", "summary", "next", "resource", "checkpoint"):
                    supplied = getattr(args, key)
                    if supplied is not None:
                        value[key] = supplied
                if args.evidence is not None:
                    value["evidence"] = args.evidence
                    value["evidence_sha256"] = store.bind_evidence(args.evidence)
                request["value"] = value
            elif args.action == "stop":
                request["reason"] = args.reason
            result = dispatch(store, request)
    except (OSError, ValueError) as error:
        print(f"harness task: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif args.action == "status":
        if not result["tasks"]:
            _out("No local tasks in this project.")
        for row in result["tasks"]:
            value = row["value"]
            _out(f"{row['task']} v{row['version']} {row['activity']}")
            for key in ("goal", "stage", "checkpoint", "next", "blocked_on"):
                if value.get(key):
                    _out(f"  {key}: {value[key]}")
            if value.get("evidence"):
                _out(f"  evidence: {value['evidence']} ({row['evidence_status']}; reference only)")
    elif args.action == "evidence":
        _out(f"{result['task']}: {result['path'] or 'none'} ({result['status']}; reference only)")
    else:
        _out(f"{result['task']} v{result['version']}: {args.action} recorded; run the graph gate to prove completion")
    return 0


def cmd_launch(args) -> int:
    from .launch import execute, prepare
    try:
        if args.execute:
            if not args.receipt_out:
                raise ValueError("--execute requires --receipt-out")
            result = execute(args.project_root, args.request, args.receipt_out, timeout=args.timeout,
                             workspace_write=args.workspace_write, method_policy=args.method_policy,
                             resume_receipt=args.resume_receipt, artifact_path=args.artifact,
                             gate_receipt_path=args.gate_receipt,
                             native_model=args.native_model, native_effort=args.native_effort,
                             eval_deny_root=args.eval_deny_root)
        else:
            if args.receipt_out:
                raise ValueError("--receipt-out requires --execute")
            if args.workspace_write:
                raise ValueError("--workspace-write requires --execute")
            if args.resume_receipt:
                raise ValueError("--resume-receipt requires --execute")
            if args.artifact or args.gate_receipt:
                raise ValueError("--artifact and --gate-receipt require --execute")
            if args.native_model or args.native_effort:
                raise ValueError("--native-model and --native-effort require --execute")
            if args.eval_deny_root:
                raise ValueError("--eval-deny-root requires --execute")
            result = prepare(args.project_root, args.request, method_policy=args.method_policy)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"harness launch: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["native_completion"] in ("NOT_RUN", "COMPLETED_UNGRADED") else 1


def cmd_method(args) -> int:
    from .method_control import decide
    try:
        result = decide(args.project_root, args.request, receipt_path=args.receipt,
                        artifact_path=args.artifact, gate_receipt_path=args.gate_receipt,
                        dependencies=args.dependencies,
                        uncertainty=args.uncertainty)
    except (OSError, ValueError, TypeError) as error:
        print(f"harness method: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="harness", description=__doc__)
    ap.add_argument("--home", help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd")
    from .native_evidence import add_parser
    add_parser(sub)
    from .continuation import add_parser as add_continuation_parser
    add_continuation_parser(sub)
    p = sub.add_parser("install", help="set up your AI coding tools")
    p.add_argument("--tools", help="comma-separated tool names, or 'all' (default: the ones found)")
    p.add_argument("--yes", action="store_true", help="accept every tool without asking")
    p.add_argument("--profile", help="profile directory (profile.toml + descriptor)")
    p.add_argument("--project", help="install into this project instead of your user settings")
    p.add_argument("--dry-run", action="store_true", help="show the plan, write nothing")
    p.add_argument("--source", help=argparse.SUPPRESS)
    sub.add_parser("uninstall", help="restore what was there before")
    p = sub.add_parser("status", help="what is installed, for which tools")
    status_mode = p.add_mutually_exclusive_group()
    status_mode.add_argument("--matrix", action="store_true", help="which tool gets which feature, and why not")
    status_mode.add_argument("--runtime", action="store_true", help="read-only current package, PATH and installed-code identities")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("explain", help="what a session actually used: rules, skills, harness tools, checks, tokens")
    p.add_argument("--client", choices=["claude-code", "codex"], default="claude-code")
    p.add_argument("--session", help="transcript path (default: the newest for this client and folder)")
    p.add_argument("--json", action="store_true")
    sub.add_parser("doctor", help="check the installation")
    p = sub.add_parser("warmup", help="build the knowledge index and install optional plugins")
    p.add_argument("--background", action="store_true")
    p.add_argument("--include-optional", action="store_true", help="also install plugins marked optional")
    p.add_argument("--yes", action="store_true", help="accept editor settings and extensions without asking")
    p = sub.add_parser("update", help="refresh the harness, keeping memory and lessons")
    p.add_argument("--source", help="harness source directory")
    p.add_argument("--profile", help="replace the active profile with this directory, then re-render the rules")
    sub.add_parser("learn", help="show the lessons learned so far")
    p = sub.add_parser("sync", help="two-way sync of memory, lessons and state with another machine")
    p.add_argument("--remote", help="<ssh-target>:<remote HARNESS_HOME>, or a local path")
    p.add_argument("--ssh-cmd", help="ssh command to use (default: ssh)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--config", action="store_true", help="save --remote/--ssh-cmd as the default")
    p = sub.add_parser("self-update", help="update to the newest release whose checks passed (at most daily)")
    p.add_argument("--check", action="store_true", help="say what it would do, change nothing")
    p.add_argument("--now", action="store_true", help="ignore the once-a-day limit")
    p = sub.add_parser("improve", help="turn repeated lessons into proposals; apply one only behind an eval gain")
    p.add_argument("--weekly-intake", action="store_true", help="on-demand changed evidence only; no model or promotion")
    p.add_argument("--since", type=int, help="expected intake cursor; refuse stale readers")
    p.add_argument("--max-items", type=int, default=10, help="maximum changed candidates, 1..20")
    p.add_argument("--max-output-bytes", type=int, default=2048, help="conservative output budget, 120..4096 bytes")
    p.add_argument("--propose", action="store_true")
    p.add_argument("--draft-procedure", metavar="FILE", help="draft a scoped v1 method from source episodes")
    p.add_argument("--correct-procedure", metavar="ID",
                   help="withdraw this scoped method and link a proposed replacement from --draft-procedure")
    p.add_argument("--project", help="absolute project directory for v1 procedures")
    p.add_argument("--rollback", metavar="ID", help="revoke an active v1 procedure; preserve its evidence")
    p.add_argument("--apply", metavar="ID")
    p.add_argument("--eval", metavar="FILE", help="paired eval result for --apply")
    p.add_argument("--trend", metavar="HISTORY", help="refuse a release that scores below the previous one")
    p.add_argument("--release", help="the release --trend judges (default: this version)")
    p.add_argument("--new-baseline", action="store_true", help="with --trend: accept a changed eval as a new baseline")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("discover", help="find extensions for a need, vet them, install only what you approve")
    p.add_argument("need", nargs="?", default="")
    p.add_argument("--json", action="store_true")
    p.add_argument("--catalog", help="a catalogue file instead of the live sources")
    p.add_argument("--no-network", action="store_true", help="only the plugin lists the tools keep locally")
    p.add_argument("--install", metavar="ID", help="install this item (needs --approve)")
    p.add_argument("--approve", metavar="SHA256", help="the sha256 of the exact install command shown")
    p.add_argument("--override", action="store_true", help="also install an item vetted as block")
    p = sub.add_parser("run", help="drain a plan autonomously: each node to a worker on its tier, every gate run here")
    p.add_argument("slug")
    p.add_argument("--workers", type=int, default=2)
    p = sub.add_parser("review", help="review the current changes in a fresh context; gate on must-fix")
    p.add_argument("--run", action="store_true", help="run the reviewer on the diff and write the findings")
    p.add_argument("--base", help="review the branch against this ref (default: uncommitted changes)")
    p.add_argument("--out", help="findings file (default: .agent-harness-review.json in the project)")
    p.add_argument("--gate", metavar="FILE", help="exit 0 only if FILE is a valid review with no must-fix")
    p = sub.add_parser("vault-read", help="read one pinned source from a shared vault without making a local copy")
    p.add_argument("--vault-root", required=True)
    p.add_argument("--vault-id", required=True)
    p.add_argument("--source", required=True, help="relative source path inside the authorized shared root")
    p.add_argument("--sha256", required=True, help="digest from the approved source catalogue")
    p.add_argument("--start-line", type=int, default=1)
    p.add_argument("--end-line", type=int)
    p.add_argument("--max-bytes", type=int, default=65536)
    p = sub.add_parser("vault-document", help="read a document from one pinned public shared-vault catalogue")
    p.add_argument("--vault-root", required=True)
    p.add_argument("--vault-id", required=True)
    p.add_argument("--manifest", default="manifest.json")
    p.add_argument("--manifest-sha256", required=True)
    p.add_argument("--document-id", required=True)
    p.add_argument("--start-line", type=int, default=1)
    p.add_argument("--end-line", type=int)
    p.add_argument("--max-bytes", type=int, default=65536)
    p = sub.add_parser("vault-search", help="find exact cited excerpts within an explicit shared-document scope")
    p.add_argument("--vault-root", required=True)
    p.add_argument("--vault-id", required=True)
    p.add_argument("--manifest", default="manifest.json")
    p.add_argument("--manifest-sha256", required=True)
    p.add_argument("--allow-id", action="append", required=True, help="approved document ID; repeat for each allowed source")
    p.add_argument("--query", required=True)
    p.add_argument("--backend", choices=("lexical", "fts5"), default="lexical")
    p.add_argument("--max-results", type=int, default=5)
    p.add_argument("--max-bytes", type=int, default=8192)
    p.add_argument("--context-lines", type=int, default=0,
                   help="include 0..8 source lines before/after each match, within the same byte cap")
    p = sub.add_parser("memory-page", help="read one scoped page from an existing opt-in project memory")
    p.add_argument("--project-root", required=True, help="authorized project root; never auto-initialized")
    p.add_argument("--project-id", required=True, help="expected stable project UUID")
    p.add_argument("--query", required=True)
    p.add_argument("--allow-sensitivity", action="append", required=True, help="allowed sensitivity; repeat as needed")
    p.add_argument("--allow-scope", action="append", required=True, help="allowed item scope; repeat as needed")
    p.add_argument("--layer", action="append", required=True, help="allowed memory layer; repeat as needed")
    p.add_argument("--cursor", help="next_cursor JSON object from the preceding page (at most 1024 UTF-8 bytes)")
    p.add_argument("--page-size", type=int, default=5)
    p.add_argument("--max-bytes", type=int, default=8192)
    p = sub.add_parser("memory-read", help="resolve an exact retained memory receipt with explicit scope")
    p.add_argument("--project-root", required=True, help="authorized project root; never auto-initialized")
    p.add_argument("--project-id", required=True, help="expected stable project UUID")
    p.add_argument("--receipt", required=True, help="receipt JSON object from a page or save (at most 1024 UTF-8 bytes)")
    p.add_argument("--allow-sensitivity", action="append", required=True)
    p.add_argument("--allow-scope", action="append", required=True)
    p.add_argument("--layer", action="append", required=True)
    p.add_argument("--historical", action="store_true", help="explicitly read retained history without claiming it is current")
    p.add_argument("--recover", choices=("resume", "compact"), help="revalidate this dependency against retained current state")
    p.add_argument("--verified-receipt", help="complete previously verified receipt JSON; valid only with --recover")
    p.add_argument("--max-bytes", type=int, default=8192)
    p = sub.add_parser("op", help="local project task state: snapshot, changes or a CAS mutation")
    p.add_argument("action", choices=("snapshot", "changes", "put", "claim", "renew", "release", "withdraw"))
    p.add_argument("--cursor", type=int, default=0, help="for changes: prior cursor")
    p.add_argument("--limit", type=int, default=100, help="for changes: maximum events")
    p = sub.add_parser("task", help="shared project task state: status, checkpoint, stop, resume, evidence")
    p.add_argument("action", choices=("status", "checkpoint", "stop", "resume", "evidence"))
    p.add_argument("task", nargs="?", help="task id; optional only for status")
    p.add_argument("--goal")
    p.add_argument("--stage")
    p.add_argument("--summary")
    p.add_argument("--next")
    p.add_argument("--resource")
    p.add_argument("--checkpoint", help="existing project-local plan or checkpoint file")
    p.add_argument("--evidence", help="project-local receipt path (reference only, not proof of PASS)")
    p.add_argument("--reason", help="why new claims must stop; does not kill an active worker")
    p.add_argument("--expected", type=int, help="task version from status; omitted uses latest with CAS")
    p.add_argument("--request-id", help="idempotency key; requires --expected for stable retries")
    p.add_argument("--json", action="store_true", help="machine-readable result of the same task contract")
    p = sub.add_parser("launch", help="prepare scoped current context; optionally invoke one bounded native Codex turn")
    p.add_argument("--project-root", required=True)
    p.add_argument("--request", required=True, help="project-relative launch request JSON")
    p.add_argument("--execute", action="store_true", help="explicitly run native Codex read-only")
    p.add_argument("--workspace-write", action="store_true", help="use Codex workspace-write sandbox for explicit code tasks")
    p.add_argument("--method-policy", choices=("existing", "adaptive"), default="existing",
                   help="opt-in method-choice prompt for paired evaluation; no authority or grader changes")
    p.add_argument("--resume-receipt", help="project-relative prior failed or gate-rejected receipt for a same-thread continuation")
    p.add_argument("--artifact", help="existing project-relative artifact for independent feedback")
    p.add_argument("--gate-receipt", help="independent failed gate result bound to that artifact")
    p.add_argument("--receipt-out", help="new project-relative JSON receipt; required with --execute")
    p.add_argument("--timeout", type=float, default=120)
    p.add_argument("--native-model", help="pin requested Codex model for a controlled eval")
    p.add_argument("--native-effort", help="pin requested Codex effort with --native-model; not effective-identity proof")
    p.add_argument("--eval-deny-root", help="opt-in deny of a fixture sibling oracle or verified projection's frozen answer pack; profile use is not verified by this flag")
    p = sub.add_parser("method", help="read-only method decision from current task and observed feedback")
    p.add_argument("--project-root", required=True)
    p.add_argument("--request", required=True)
    p.add_argument("--receipt", help="project-relative previous native receipt")
    p.add_argument("--artifact", help="project-relative expected artifact")
    p.add_argument("--gate-receipt", help="project-relative independent gate result bound to artifact bytes")
    p.add_argument("--dependencies", type=int, default=0)
    p.add_argument("--uncertainty", choices=("none", "consequential"), default="none")
    from .presets import add_parser as add_preset_parser
    add_preset_parser(sub)
    sub.add_parser("_hook-stop")
    sub.add_parser("_hook-prompt")
    sub.add_parser("_hook-context")
    sub.add_parser("_hook-op")
    sub.add_parser("_hook-capture")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "evidence":
        from .native_evidence import command
        return command(args)
    if args.cmd == "preset":
        from .presets import command
        return command(args)
    if args.cmd == "continuation":
        from .continuation import command
        return command(args)
    fn = {"install": cmd_install, "uninstall": cmd_uninstall, "status": cmd_status, "doctor": cmd_doctor, "explain": cmd_explain,
          "warmup": cmd_warmup, "update": cmd_update, "learn": cmd_learn, "sync": cmd_sync,
          "review": cmd_review, "run": cmd_run, "discover": cmd_discover,
          "improve": cmd_improve, "self-update": cmd_self_update, "vault-read": cmd_vault_read,
          "vault-document": cmd_vault_document, "vault-search": cmd_vault_search,
          "memory-page": cmd_memory_page, "memory-read": cmd_memory_read,
          "launch": cmd_launch, "method": cmd_method, "op": cmd_op, "task": cmd_task}.get(args.cmd)
    if args.cmd == "_hook-stop":
        return stop_hook()
    if args.cmd == "_hook-prompt":
        return prompt_hook()
    if args.cmd == "_hook-context":
        return context_hook()
    if args.cmd == "_hook-op":
        return op_context_hook()
    if args.cmd == "_hook-capture":
        return capture_hook()
    if fn is None:
        build_parser().print_help()
        return 1
    try:
        return fn(args)
    except I.InstallError as e:
        _out(f"harness: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
