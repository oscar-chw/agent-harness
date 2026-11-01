"""Query equivalence through real harness readers around disposable index compaction."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from agent_harness.index_copy import compact_copy  # noqa: E402
from agent_harness.mcp.kb import KB  # noqa: E402
from agent_harness.mcp.sessions import Sessions  # noqa: E402


def query(home,docs,index):
    kb=KB(home=home/'harness',paths=[docs],db_path=index,fts=True)
    sessions=Sessions(home=home/'harness',user_home=home,db_path=index,fts=True)
    try:
        return kb.search('quartz'),sessions.search('quartz',project='fixture-project')
    finally:
        sessions.close();kb.close()


def run(base):
    home=Path(base)/'home';docs=home/'docs';docs.mkdir(parents=True)
    (docs/'policy.md').write_text('# Quartz\nQuartz service uses port 7082.\n')
    history=home/'.claude/projects/fixture/thread.jsonl';history.parent.mkdir(parents=True)
    history.write_text(json.dumps({'type':'user','cwd':'fixture-project','timestamp':'2026-01-01T00:00:00Z',
                                  'message':{'content':'Quartz correction: use port 7082.'}})+'\n')
    before_sources={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (docs/'policy.md',history)}
    index=home/'harness/index.sqlite'
    expected=query(home,docs,index)
    assert expected[0] and expected[1]['results']
    con=sqlite3.connect(index)
    try:
        con.execute('CREATE TABLE fixture_padding (id INTEGER PRIMARY KEY, payload TEXT)')
        con.executemany('INSERT INTO fixture_padding(payload) VALUES (?)',[('x'*2048,)]*512)
        con.execute('DELETE FROM fixture_padding')
        con.commit()
    finally:con.close()
    raw=index.read_bytes()
    output=home/'compacted.sqlite'
    receipt=compact_copy(index,output,offline=True)
    assert index.read_bytes()==raw
    assert output.stat().st_size<index.stat().st_size
    observed=query(home,docs,output)
    assert observed==expected,'actual KB/session query changed after compaction'
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==sha for p,sha in before_sources.items())
    return {'status':'COPY_QUERY_EQUIVALENCE_PASS','source_index_unchanged_during_compaction':True,
            'source_documents_unchanged':True,'kb_hits':len(observed[0]),'session_hits':len(observed[1]['results']),
            'receipt':receipt,'live_index_maintenance':False,'model_evidence':'NOT_RUN'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='index-maintenance-canary-') as directory:report=run(directory)
    data=json.dumps(report,indent=2)
    if args.output:
        with args.output.open('x') as f:f.write(data+'\n')
    print(data)
