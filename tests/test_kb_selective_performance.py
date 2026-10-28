"""Avoid repeated canonicalization without caching permission or source state."""
from pathlib import Path
from agent_harness.mcp.kb import discover_files


def test_regular_files_share_directory_resolution_work(tmp_path,monkeypatch):
    docs=tmp_path/'docs';docs.mkdir()
    for n in range(80):(docs/f'{n}.md').write_text('# A\nbody')
    original=Path.resolve;calls=[]
    def counted(path,*args,**kwargs):
        calls.append(path)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'resolve',counted)
    found=discover_files([docs])
    assert len(found)==80 and all(p.is_absolute() for p,_ in found)
    assert len(calls)<=3, 'canonicalization should scale with directories, not regular files'


def test_changed_symlink_targets_and_root_alias_are_resolved_each_discovery(tmp_path):
    docs=tmp_path/'docs';docs.mkdir()
    a=tmp_path/'a.md';a.write_text('# A\nfirst')
    b=tmp_path/'b.md';b.write_text('# B\nsecond')
    link=docs/'link.md';link.symlink_to(a)
    alias=tmp_path/'alias';alias.symlink_to(docs,target_is_directory=True)
    assert discover_files([alias])==[(a.resolve(),'alias/link.md')]
    link.unlink();link.symlink_to(b)
    assert discover_files([alias])==[(b.resolve(),'alias/link.md')]
