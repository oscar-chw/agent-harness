"""One explicit install preference; native clients retain final permission authority."""
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import uuid

MODES = ('preserve', 'explicit', 'autonomous')
SUDO_MODES = ('deny', 'ask', 'adaptive', 'scoped')
_LEGACY = "- No `sudo`; stay in the project and the user's home."
_RULE = re.compile(r'^- Sudo `sudo_policy=(deny|ask|adaptive|scoped)`: work-loop/recovery.md\.', re.M)


def validate_sudo(mode):
    if mode not in SUDO_MODES:
        raise ValueError('sudo policy must be deny, ask, adaptive or scoped')
    return mode


def _rule(mode):
    return f'- Sudo `sudo_policy={validate_sudo(mode)}`: work-loop/recovery.md.'


def render_sudo(text, mode, *, required=False):
    validate_sudo(mode)
    legacy = list(re.finditer('^' + re.escape(_LEGACY), text, re.M))
    current = list(_RULE.finditer(text))
    if len(legacy) + len(current) != 1:
        if not legacy and not current and not required:
            return text  # A custom rules template is not ours to rewrite.
        raise ValueError('expected exactly one recognized sudo policy rule')
    match = (legacy + current)[0]
    return text[:match.start()] + _rule(mode) + text[match.end():]


def _read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 256 * 1024:
            raise ValueError('policy input must be a regular file under 256 KiB')
        with os.fdopen(fd, 'rb', closefd=False) as handle:
            data = handle.read(256 * 1024 + 1)
        if len(data) > 256 * 1024:
            raise ValueError('policy input exceeds 256 KiB')
        return data, stat.S_IMODE(info.st_mode)
    finally:
        os.close(fd)


def saved_sudo(hh, profile=None):
    path = Path(hh) / 'privileges.json'
    if path.exists() or path.is_symlink():
        data, _ = _read(path)
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError('invalid saved privilege policy')
        return validate_sudo(value.get('sudo_policy'))
    return validate_sudo((profile or {}).get('sudo_policy', 'adaptive'))


def _write(path, data, mode=0o600):
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.privilege-', delete=False) as handle:
            temp = Path(handle.name)
            handle.write(data)
        temp.chmod(mode)
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


def configure_sudo(home, hh, mode=None):
    """Only Codex instructions and the shared template; never native config or Claude."""
    home, hh = Path(home), Path(hh)
    paths = [home / '.codex/AGENTS.md', hh / 'content/AGENTS.md']
    if mode is not None:
        validate_sudo(mode)
    prepared = []
    observed = []
    for path in paths:
        if not path.exists() and not path.is_symlink():
            continue
        data, permissions = _read(path)
        text = data.decode('utf-8')
        render_sudo(text, mode or 'adaptive', required=True)
        match = _RULE.search(text)
        observed.append(match.group(1) if match else 'deny')
        new = render_sudo(text, mode, required=True).encode('utf-8') if mode else data
        prepared.append((path, data, new, permissions))
    if not prepared:
        raise ValueError('no installed Codex rules or shared template found')
    policy = hh / 'privileges.json'
    # Validate an existing preference before touching any instruction file.
    saved = saved_sudo(hh) if policy.exists() or policy.is_symlink() else None
    if mode is None:
        if len(set(observed)) != 1 or (saved is not None and saved != observed[0]):
            raise ValueError('instruction policies disagree; choose a mode explicitly')
        return {'sudo_policy': observed[0], 'changed': [], 'scope': 'instructions, not native permissions'}
    changed = []
    backup = hh / 'rollback' / ('privileges-' + uuid.uuid4().hex)
    for index, (path, old, new, permissions) in enumerate(prepared):
        if old == new:
            continue
        # Detect owner edits after preflight; never silently overwrite them.
        if _read(path)[0] != old:
            raise ValueError('rules changed during policy update; existing backups retained')
        backup.mkdir(mode=0o700, parents=True, exist_ok=True)
        saved_path = backup / f'{index}-AGENTS.md'
        _write(saved_path, old)
        _write(path, new, permissions)
        changed.append({'path': str(path), 'backup': str(saved_path)})
    hh.mkdir(parents=True, exist_ok=True)
    _write(policy, (json.dumps({'sudo_policy': mode}, sort_keys=True) + '\n').encode())
    return {'sudo_policy': mode, 'changed': changed,
            'scope': 'instructions, not native permissions; no privileged command executed'}


def command(args):
    home = Path(args.home).expanduser() if args.home else Path.home()
    hh = Path(os.environ.get('HARNESS_HOME', str(home / '.agent-harness'))).expanduser()
    try:
        result = configure_sudo(home, hh, args.mode)
    except (ValueError, OSError, UnicodeError) as error:
        print(json.dumps({'error': str(error)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


def validate(value):
    if value not in MODES:
        raise ValueError('unknown permission profile; choose preserve, explicit or autonomous')
    return value


def choose(requested, saved, interactive=False):
    if requested is not None:
        return validate(requested)
    if saved is not None:
        return validate(saved)
    if not interactive:
        return 'preserve'
    answer = input('Permission control: 1 explicit review, 2 native workspace autonomy, '
                   '3 keep current settings [3]: ').strip()
    if answer not in ('', '1', '2', '3'):
        raise ValueError('invalid permission choice; nothing installed')
    return {'1': 'explicit', '2': 'autonomous', '3': 'preserve', '': 'preserve'}[answer]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Toggle the harness instruction policy; never execute sudo.')
    parser.add_argument('--home')
    parser.add_argument('--mode', choices=SUDO_MODES)
    raise SystemExit(command(parser.parse_args()))
