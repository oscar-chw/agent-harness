"""The knowledge add-on reuses the vetted data publisher, never the runtime installer."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fixture(tmp_path):
    bundle = tmp_path / "bundle space's"
    bundle.mkdir()
    shutil.copyfile(ROOT / 'scripts/add-laptop-knowledge.py', bundle / 'add-knowledge.py')
    shutil.copyfile(ROOT / 'scripts/install-laptop.py', bundle / 'install.py')
    wheel = bundle / 'agent_harness-2.0.0.dev3-py3-none-any.whl'
    wheel.write_bytes(b'NOT_AN_INSTALLABLE_WHEEL: data-only path must not invoke pip')
    body = b'# SWE\nBounded local knowledge.\n'
    knowledge = bundle / 'knowledge.zip'
    with zipfile.ZipFile(knowledge, 'w') as archive:
        archive.writestr('swe-core/SWE.md', body)
    manifest = {'version': '2.0.0.dev3',
        'wheel': {'file': wheel.name, 'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest()},
        'knowledge': {'file': knowledge.name, 'sha256': hashlib.sha256(knowledge.read_bytes()).hexdigest(),
                      'files': [{'path': 'swe-core/SWE.md', 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}]}}
    (bundle / 'MANIFEST.json').write_text(json.dumps(manifest))
    home = tmp_path / "home space's"
    home.mkdir()
    hh = home / '.agent-harness'
    preserved = {}
    for name, value in {'profile/rules.md': 'My rules', 'profile/knowledge/old.md': 'Original notes',
                        'memory/user/fixture.md': 'Existing memory'}.items():
        path = hh / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
        preserved[path] = path.read_bytes()
    config = home / '.codex/config.toml'
    config.parent.mkdir()
    config.write_text('approval_policy = "on-request"\nsandbox_mode = "read-only"\n')
    preserved[config] = config.read_bytes()
    return bundle, home, hh, manifest, body, preserved


def invoke(fixture, *extra):
    bundle, home, _, _, _, _ = fixture
    return subprocess.run([sys.executable, str(bundle / 'add-knowledge.py'), '--home', str(home), *extra],
        env={'PATH': os.defpath, 'HOME': str(home), 'HARNESS_HOME': '/DO_NOT_USE_THIS_ENV_STORE',
             'PYTHONDONTWRITEBYTECODE': '1'}, capture_output=True, text=True, timeout=15)


def test_data_only_install_and_repeat_preserve_runtime_settings_and_memory(fixture):
    _, _, hh, manifest, body, preserved = fixture
    for _ in range(2):
        result = invoke(fixture)
        assert result.returncode == 0, result.stderr
        assert 'no runtime' in result.stdout
        assert all(path.read_bytes() == expected for path, expected in preserved.items())
        assert not (hh / 'lib').exists() and not (hh / 'installed.json').exists()
    target = hh / 'profile/knowledge' / ('swe-core-' + manifest['knowledge']['sha256'][:16])
    assert (target / 'swe-core/SWE.md').read_bytes() == body
    assert len(list((hh / 'profile/knowledge').glob('swe-core-*'))) == 1


def test_check_mode_does_not_publish(fixture):
    result = invoke(fixture, '--check')
    assert result.returncode == 0 and 'no changes' in result.stdout
    assert not list((fixture[2] / 'profile/knowledge').glob('swe-core-*'))


def test_modified_existing_knowledge_is_not_overwritten(fixture):
    assert invoke(fixture).returncode == 0
    target = next((fixture[2] / 'profile/knowledge').glob('swe-core-*')) / 'swe-core/SWE.md'
    target.write_text('User-edited version')
    result = invoke(fixture)
    assert result.returncode == 2 and 'existing knowledge changed' in result.stderr
    assert target.read_text() == 'User-edited version'


def test_explicit_custom_store_and_redirect_refusal(fixture, tmp_path):
    custom = tmp_path / "custom store's"
    result = invoke(fixture, '--harness-home', str(custom))
    assert result.returncode == 0, result.stderr
    assert list((custom / 'profile/knowledge').glob('swe-core-*'))
    linked = tmp_path / 'redirected-store'
    linked.symlink_to(custom)
    result = invoke(fixture, '--harness-home', str(linked))
    assert result.returncode == 2 and 'redirected' in result.stderr


def test_changed_archive_refuses_before_publication(fixture):
    (fixture[0] / 'knowledge.zip').write_bytes(b'Changed after packaging')
    result = invoke(fixture)
    assert result.returncode == 2 and 'changed or invalid knowledge' in result.stderr
    assert not list((fixture[2] / 'profile/knowledge').glob('swe-core-*'))
