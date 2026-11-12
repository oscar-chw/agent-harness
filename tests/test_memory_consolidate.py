"""Unit tests for agent_harness.memory_consolidate (H1 node 7).

All fixtures are synthetic tmp_path corpora; the tests never read the live
memory corpus, never touch the network, and never call a model.
"""
import json
from pathlib import Path

import pytest

from agent_harness import memory_consolidate as mc


def write_page(root: Path, rel: str, body: str, modified: str = '') -> Path:
    fm = '---\nname: %s\n' % Path(rel).stem
    if modified:
        fm += 'metadata:\n  modified: %s\n' % modified
    fm += '---\n\n'
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(fm + body, encoding='utf-8')
    return p


def write_raw(root: Path, rel: str, content: str) -> Path:
    """Exact bytes — for duplicate fixtures, where the frontmatter name must match too."""
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')
    return p


def hashes_under(root: Path):
    return {p.read_bytes() and mc._sha256(p.read_bytes())
            for p in sorted(root.rglob('*.md'))}


def make_freeze(root: Path, out: Path) -> Path:
    pages = mc.load_pages(root)
    recs = [{'path': pg.rel, 'bytes': len(pg.data), 'sha256': pg.sha256} for pg in pages]
    doc = {'corpus': {'pages': recs, 'page_order': [pg.rel for pg in pages],
                      'corpus_sha256': mc.corpus_root_hash([pg.sha256 for pg in pages])}}
    out.write_text(json.dumps(doc))
    return out


# ---------------------------------------------------------------- dup merge

def test_exact_dups_merged_keeper_by_indegree_archive_not_delete(tmp_path):
    src = tmp_path / 'src'
    body = ('---\nname: dup\nmetadata:\n  modified: 2026-08-01T00:00:00Z\n---\n\n'
            'The rotated greeble valve seats at 45 degrees.\n' * 6)
    write_raw(src, 'dup-a.md', body)
    write_raw(src, 'dup-b.md', body)
    write_page(src, 'linker.md', 'See [[dup-b]] and again [[dup-b]]. Distinct content here.',
               '2026-08-02T00:00:00Z')
    dst = tmp_path / 'dst'
    report = mc.consolidate(src, dst, apply=True)
    assert report['counts']['exact_dup_groups'] == 1
    action = report['actions'][0]
    assert action['kind'] == 'dup_merge'
    assert action['keeper'] == 'dup-b.md'           # highest in-degree wins
    assert action['archive'] == ['dup-a.md']
    assert action['applied'] is True
    # archive, never delete: bytes survive under archive/
    archived = dst / 'archive' / 'dup-a.md'
    assert archived.is_file()
    assert mc._sha256(archived.read_bytes()) == mc._sha256(body.encode())
    assert not (dst / 'dup-a.md').exists()
    assert (dst / 'dup-b.md').is_file()
    assert report['fact_preservation']['ok'] is True


def test_near_dups_flagged_never_merged(tmp_path):
    src = tmp_path / 'src'
    shared = ' '.join('w%03d' % i for i in range(80))      # ~76 distinct shared 5-gram shingles
    write_page(src, 'p1.md', shared + ' tailone tailtwo tailthree tailfour tailfive.',
               '2026-08-01T00:00:00Z')
    write_page(src, 'p2.md', shared + 'tailsix tailseven taileight.', '2026-08-02T00:00:00Z')
    report = mc.consolidate(src, apply=False)
    assert report['counts']['exact_dup_groups'] == 0
    assert report['counts']['near_dup_review'] == 1
    flag = report['actions'][0]
    assert flag['kind'] == 'near_dup_review'
    assert flag['jaccard'] >= mc.NEAR_DUP_JACCARD
    assert flag['applied'] is False
    # and apply mode still does not merge them
    report2 = mc.consolidate(src, tmp_path / 'dst', apply=True)
    assert report2['counts']['exact_dup_groups'] == 0 and report2['counts']['pages_archived'] == 0
    assert (tmp_path / 'dst' / 'p1.md').is_file() and (tmp_path / 'dst' / 'p2.md').is_file()


def test_no_dups_means_no_merges(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'one.md', 'Quokka lattice maintenance notes.', '2026-08-01T00:00:00Z')
    write_page(src, 'two.md', 'Entirely different telescope collimation log.', '2026-08-01T00:00:00Z')
    report = mc.consolidate(src, apply=False)
    assert report['counts']['exact_dup_groups'] == 0
    assert report['counts']['near_dup_review'] == 0


# ---------------------------------------------------------------- supersedes

def test_supersedes_edge_directed_fact_scoped_and_receipt_only(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'old.md',
               'The widget-frob link runs at 1000 Mb/s; the gizmo switch is the limit.\n',
               '2026-08-01T00:00:00Z')
    write_page(src, 'new.md',
               '**Correction 2026-09-01:** the 1000 Mb/s reading of the widget-frob gizmo '
               'link was wrong; measured throughput establishes 5 Gb/s.\n',
               '2026-09-01T00:00:00Z')
    report = mc.consolidate(src, apply=False)
    assert report['counts']['supersedes_edges'] == 1
    edge = [a for a in report['actions'] if a['kind'] == 'supersedes_edge'][0]
    assert edge['successor'] == 'new.md'
    assert edge['superseded'] == 'old.md'
    assert '1000 Mb/s' in edge['fact_scope']['matched_literals']
    assert {'widget-frob', 'gizmo'} <= set(edge['fact_scope']['shared_tokens'])
    assert edge['applied'] is False
    # receipt-only: even with apply, neither page's bytes change
    dst = tmp_path / 'dst'
    mc.consolidate(src, dst, apply=True)
    assert (dst / 'old.md').read_bytes() == (src / 'old.md').read_bytes()
    assert (dst / 'new.md').read_bytes() == (src / 'new.md').read_bytes()


def test_supersedes_without_ordering_evidence_is_undirected(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'old.md', 'The widget-frob gizmo link runs at 1000 Mb/s.\n')   # no modified
    write_page(src, 'new.md', 'Correction: the 1000 Mb/s widget-frob gizmo reading was wrong.\n')
    report = mc.consolidate(src, apply=False)
    assert report['counts']['supersedes_edges'] == 0
    assert report['counts']['version_candidates_undirected'] == 1
    cand = [a for a in report['actions'] if a['kind'] == 'version_candidate_undirected'][0]
    assert cand['rule'].startswith('no reliable ordering evidence')


def test_supersedes_needs_shared_distinctive_tokens(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'old.md', 'Completely unrelated quinoa recipe at 1000 Mb/s.\n',
               '2026-08-01T00:00:00Z')
    write_page(src, 'new.md', 'Correction: the 1000 Mb/s reading was wrong.\n',
               '2026-09-01T00:00:00Z')
    report = mc.consolidate(src, apply=False)
    assert report['counts']['supersedes_edges'] == 0
    assert report['counts']['version_candidates_undirected'] == 0


# ---------------------------------------------------------------- conflicts

def test_conflict_flag_withdrawn_but_newer_page_instructs(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'old.md',
               'Routing zqx transfers via `zqx-route` was withdrawn and should not be '
               're-proposed; it bypassed the tunnel policy.\n', '2026-08-01T00:00:00Z')
    write_page(src, 'new.md',
               'For zqx transfers use `zqx-route`; it is the fast path.\n',
               '2026-09-01T00:00:00Z')
    report = mc.consolidate(src, apply=False)
    assert report['counts']['conflict_flags'] == 1
    flag = [a for a in report['actions'] if a['kind'] == 'conflict_flag'][0]
    assert flag['withdrawing_page'] == 'old.md'
    assert flag['instructing_page'] == 'new.md'
    assert 'zqx-route' in flag['fact_scope']['matched_literals']
    # conflicts never mutate bytes
    dst = tmp_path / 'dst'
    mc.consolidate(src, dst, apply=True)
    assert (dst / 'old.md').read_bytes() == (src / 'old.md').read_bytes()
    assert (dst / 'new.md').read_bytes() == (src / 'new.md').read_bytes()


def test_no_conflict_when_withdrawal_is_newer(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'old.md', 'For zqx transfers use `zqx-route`.\n', '2026-08-01T00:00:00Z')
    write_page(src, 'new.md',
               '`zqx-route` was withdrawn for zqx transfers; should not be re-proposed.\n',
               '2026-09-01T00:00:00Z')
    report = mc.consolidate(src, apply=False)
    assert report['counts']['conflict_flags'] == 0


# ------------------------------------------------------- decay / orphan arms

def test_load_bearing_pages_protected_regardless_of_age(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'hub.md', 'Ancient doctrine, still referenced everywhere.\n',
               '2026-07-01T00:00:00Z')
    for i in range(6):
        write_page(src, 'ref%d.md' % i, 'Note %d cites [[hub]].\n' % i, '2026-10-01T00:00:00Z')
    report = mc.consolidate(src, apply=False)
    klass = {r['path']: r['class'] for r in report['retention']}
    assert klass['hub.md'] == 'protected'          # oldest page, never a decay candidate
    assert report['usage_signal']['available'] is False
    assert 'never recency alone' in report['usage_signal']['note']


def test_orphan_gets_inbound_links_and_leaves_orphan_set_on_apply(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'hub.md', 'The tuplespace greeble fluxcap operator manual.\n'
               'See [[other]] for context.\n', '2026-08-01T00:00:00Z')
    write_page(src, 'other.md', 'Cites [[hub]] back.\n', '2026-08-02T00:00:00Z')
    write_page(src, 'orphan.md', 'Tuplespace greeble fluxcap measurements nobody links to.\n',
               '2026-10-01T00:00:00Z')
    report = mc.consolidate(src, apply=False)
    proposals = [a for a in report['actions'] if a['kind'] == 'orphan_inbound_link']
    assert proposals and all(p['orphan'] == 'orphan.md' for p in proposals)
    assert any(p['source'] == 'hub.md' for p in proposals)
    # apply: the SOURCE page gains the inbound link, orphan leaves the orphan set
    dst = tmp_path / 'dst'
    mc.consolidate(src, dst, apply=True)
    assert '[[orphan]]' in (dst / 'hub.md').read_text()
    pages2 = mc.load_pages(dst)
    indeg2 = mc.build_graph(pages2)
    assert indeg2.get('orphan', 0) >= 1
    report2 = mc.consolidate(dst, apply=False)
    assert report2['counts']['orphan_inbound_link_proposals'] == 0  # idempotent


def test_memory_index_page_is_never_mutated(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'MEMORY.md', '- [hub](hub.md) tuplespace greeble fluxcap index line\n')
    write_page(src, 'hub.md', 'See [[other]].\n', '2026-08-01T00:00:00Z')
    write_page(src, 'other.md', 'Cites [[hub]].\n', '2026-08-02T00:00:00Z')
    write_page(src, 'orphan.md', 'Tuplespace greeble fluxcap orphan notes.\n',
               '2026-10-01T00:00:00Z')
    dst = tmp_path / 'dst'
    report = mc.consolidate(src, dst, apply=True)
    assert (dst / 'MEMORY.md').read_bytes() == (src / 'MEMORY.md').read_bytes()
    for a in report['actions']:
        if a['kind'] == 'orphan_inbound_link':
            assert a['source'] != 'MEMORY.md'


# ------------------------------------------------------------- the pass itself

def test_dry_run_is_default_and_changes_nothing(tmp_path):
    src = tmp_path / 'src'
    body = 'Duplicate greeble paragraph.\n' * 5
    write_raw(src, 'd1.md', body)
    write_raw(src, 'd2.md', body)
    before = {p.name: p.read_bytes() for p in src.glob('*.md')}
    report = mc.consolidate(src, dst=tmp_path / 'dst', apply=False)
    assert report['dry_run'] is True
    assert not (tmp_path / 'dst').exists()
    assert report['counts']['exact_dup_groups'] == 1      # still computed and receipted
    assert {p.name: p.read_bytes() for p in src.glob('*.md')} == before
    assert report['output']['root_sha256'] == mc.corpus_root_hash(
        [pg.sha256 for pg in mc.load_pages(src)])


def test_apply_requires_separate_dst(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'a.md', 'anything\n')
    with pytest.raises(ValueError):
        mc.consolidate(src, None, apply=True)
    with pytest.raises(ValueError):
        mc.consolidate(src, src, apply=True)


def test_fact_preservation_mixed_corpus(tmp_path):
    src = tmp_path / 'src'
    body = 'Duplicated spindle log.\n' * 4
    write_raw(src, 'x1.md', body)
    write_raw(src, 'x2.md', body)
    write_page(src, 'cites.md', 'Cites [[x1]] and [[orphan2]].\n', '2026-08-01T00:00:00Z')
    write_page(src, 'orphan2.md', 'Unlinked spindle measurement page.\n', '2026-08-03T00:00:00Z')
    write_page(src, 'old.md', 'Spindle rate is 1000 Mb/s, says the old gauge.\n',
               '2026-08-01T00:00:00Z')
    write_page(src, 'new.md', 'Correction 2026-09-01: the 1000 Mb/s spindle rate was wrong.\n',
               '2026-09-01T00:00:00Z')
    in_hashes = hashes_under(src)
    dst = tmp_path / 'dst'
    report = mc.consolidate(src, dst, apply=True)
    assert report['fact_preservation']['ok'] is True
    out_hashes = hashes_under(dst)          # includes archive/
    assert in_hashes <= out_hashes          # no input byte sequence lost
    assert report['counts']['pages_archived'] == 1
    assert report['counts']['supersedes_edges'] == 1


def test_second_apply_finds_no_new_mutations(tmp_path):
    src = tmp_path / 'src'
    body = 'Same greeble content.\n' * 4
    write_raw(src, 'g1.md', body)
    write_raw(src, 'g2.md', body)
    write_page(src, 'hub.md', 'Links [[g1]]; greeble fluxcap tuplespace notes.\n',
               '2026-08-01T00:00:00Z')
    write_page(src, 'orp.md', 'greeble fluxcap tuplespace orphan.\n', '2026-09-01T00:00:00Z')
    dst1, dst2 = tmp_path / 'dst1', tmp_path / 'dst2'
    r1 = mc.consolidate(src, dst1, apply=True)
    assert r1['counts']['pages_archived'] + r1['counts']['pages_mutated'] > 0
    r2 = mc.consolidate(dst1, dst2, apply=True)
    assert r2['counts']['exact_dup_groups'] == 0
    assert r2['counts']['pages_archived'] == 0
    assert r2['counts']['pages_mutated'] == 0
    assert r2['output']['root_sha256'] == r1['output']['root_sha256']


def test_freeze_binding_verified_and_refusal_on_drift(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'a.md', 'bound page a\n', '2026-08-01T00:00:00Z')
    write_page(src, 'b.md', 'bound page b\n', '2026-08-02T00:00:00Z')
    freeze = make_freeze(src, tmp_path / 'freeze.json')
    report = mc.consolidate(src, freeze=freeze, apply=False)
    assert report['binding']['verified'] is True
    assert report['binding']['corpus_sha256'] == mc.corpus_root_hash(
        [pg.sha256 for pg in mc.load_pages(src)])
    # drift: change a page after the freeze
    write_page(src, 'a.md', 'tampered page a\n', '2026-08-01T00:00:00Z')
    with pytest.raises(ValueError):
        mc.consolidate(src, freeze=freeze, apply=False)
    with pytest.raises(ValueError):
        mc.consolidate(src, tmp_path / 'dst', freeze=freeze, apply=True)
    assert not (tmp_path / 'dst').exists()    # refused before writing anything
