"""A retained lead and a better foreign match never expand a cold KB scope."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_harness.mcp.kb import KB, fts5_available

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('fts', [False, True])
def test_retained_leads_do_not_authorize_stronger_foreign_hit(tmp_path, fts):
    if fts: assert fts5_available(), 'required FTS5 qualification backend is unavailable'
    own, foreign = tmp_path / 'own', tmp_path / 'foreign'
    own.mkdir(); foreign.mkdir()
    (own / 'policy.md').write_text('# Policy\nOWN_ALLOWED deployment readiness. ' + 'background ' * 300 + '\n')
    # These synthetic local locators represent retained lead identities, not
    # permission to read their targets. No real external/private source is used.
    (own / 'inventory.md').write_text(
        '# Retained leads\nItems 19, 20, 104: CROSS_PROJECT_RETAINED; not access/adoption authority.\n'
        'Locator: ../foreign/private.md\n')
    private = foreign / 'private.md'
    private.write_text('# Deployment readiness\nEXCLUDEDQUASAR57291 deployment readiness.\n')
    cache = tmp_path / 'cache'
    script = tmp_path / 'consumer.py'
    script.write_text('''import json,sys
from pathlib import Path
from agent_harness.mcp.kb import KB
kb=KB(home=Path(sys.argv[1]),paths=[Path(sys.argv[2])],fts=sys.argv[3]=='True')
try:
 hits=kb.search('deployment readiness',min_score=0)
 lead=kb.get('own/inventory.md#retained-leads')
 missing=kb.search('EXCLUDEDQUASAR57291',min_score=0)
 try: kb.get('foreign/private.md#deployment-readiness'); outside='returned'
 except KeyError: outside='refused'
 print(json.dumps({'hits':hits,'lead':lead,'missing':missing,'outside':outside,'availability':kb.availability}))
finally: kb.close()
''')
    home = tmp_path / 'child-home'; home.mkdir()
    def read():
        result = subprocess.run([sys.executable, str(script), str(cache), str(own), str(fts)],
            cwd=own, env={'PATH': os.defpath, 'PYTHONPATH': str(ROOT / 'src'), 'HOME': str(home),
                          'HARNESS_HOME': str(home / 'hh'), 'PYTHONDONTWRITEBYTECODE': '1'},
            text=True, capture_output=True, timeout=15)
        assert result.returncode == 0, result.stderr
        assert not result.stderr
        return json.loads(result.stdout)
    before = read()
    assert len(before['hits']) == 1 and 'OWN_ALLOWED' in json.dumps(before['hits'])
    wide = KB(home=cache, paths=[own, foreign], fts=fts)
    try:
        # Independent fixture validity check: when explicitly admitted, the
        # foreign page really outranks the own page. Mere label claims are not a control.
        both = wide.search('deployment readiness', k=10, min_score=0)
        assert both[0]['path'].startswith('foreign/')
        own_hit = next(hit for hit in both if hit['path'].startswith('own/'))
        assert both[0]['score'] > own_hit['score']
        assert wide.con.execute('SELECT body FROM kb_sections WHERE path=?', (str(private),)).fetchone()
    finally: wide.close()
    private.chmod(0)
    try:
        assert not os.access(private, os.R_OK), 'NOT_VERIFIED: excluded fixture is still readable'
        after = read()
        assert after['hits'] == before['hits']
        assert after['missing'] == [] and after['outside'] == 'refused'
        assert 'EXCLUDEDQUASAR57291' not in json.dumps(after)
        assert '19, 20, 104' in after['lead']['text']
        assert after['availability'] == {'unavailable_sources': 0, 'reasons': {}, 'discovery_errors': 0}
        # No purge is needed to pass the scoped read; retained cache/body survive.
        reader = KB(home=cache, paths=[own], fts=fts)
        try:
            saved = reader.con.execute('SELECT body FROM kb_sections WHERE path=?', (str(private),)).fetchone()
            assert saved is not None and 'EXCLUDEDQUASAR57291' in saved['body']
        finally: reader.close()
        (tmp_path / 'observed.json').write_text(json.dumps({'backend': 'fts5' if fts else 'lexical',
            'wide_foreign_score': both[0]['score'], 'wide_own_score': own_hit['score'],
            'before': before, 'after': after, 'foreign_cache_preserved': True,
            'fresh_process_each_read': True, 'excluded_fixture_effectively_unreadable': True}, indent=2))
    finally: private.chmod(0o600)
