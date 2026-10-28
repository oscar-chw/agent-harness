"""Check a private inventory join without printing source paths or message bodies."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

COVERAGE={'BYTE_OFFSET_COVERED','PARTIAL','EVICTED','STALE','INVALID_OFFSET','UNINDEXED','READER_UNSUPPORTED','INDEX_UNKNOWN'}


def require(condition,message):
    if not condition:raise ValueError(message)


def check(inventory,report):
    entries=inventory['entries'];rows=report['entries']
    digest=hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()
    require(digest==inventory['metadata_manifest_sha256']==report['source_manifest_sha256'],'inventory binding changed')
    old={e['id']:e for e in entries};new={r['id']:r for r in rows}
    require(len(old)==len(entries)==inventory['eligible_files'],'invalid input denominator')
    require(len(new)==len(rows)==report['denominator']==len(old),'duplicate or missing source')
    require(old.keys()==new.keys(),'source set differs')
    require(report['complete_migration'] is False and report['semantic_extraction']=='NOT_VERIFIED','false semantic completion')
    for key,e in old.items():
        r=new[key]
        require(all(r[k]==e[k] for k in ('root','kind','bytes','mtime_ns','coverage')),'snapshot metadata changed')
        require(r['live_import'] is False and r['current_fact_authority'] is False,'false activation or current fact')
        require(r['source_state'] in ('UNCHANGED_METADATA','STALE_METADATA','UNREADABLE','MISSING'),'missing source state')
        require(e['coverage'] in COVERAGE,'unknown index state')
        if r['source_state']=='MISSING':expected='FAILED_MISSING'
        elif e['coverage']!='READER_UNSUPPORTED':expected='EXISTING_READER_'+e['coverage']
        else:
            info=r['format_inspection'];status=info['status'];kind=info.get('format')
            if status=='FORMAT_SUPPORTED':
                require(kind in ('claude-code','codex'),'unsupported conversation format')
                expected='CANDIDATE_COPY_ONLY'
            elif status=='DERIVED_RECORDS':
                require(kind in ('workflow-journal','native-excerpt'),'unclassified derived record')
                expected='EXCLUDED_DERIVED_RECORDS'
            else:expected='FAILED_OR_UNRESOLVED'
        require(r['admission']==expected,'admission contradicts evidence')
    counts=dict(Counter(r['admission'] for r in rows))
    require(counts==report['admission'],'aggregate differs from entries')
    return {'status':'RECONCILED_METADATA','sources':len(rows),'admission':counts,'complete_migration':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory',required=True)
    parser.add_argument('--report',required=True)
    args=parser.parse_args()
    try:
        inventory=json.loads(Path(args.inventory).read_text())
        if 'report' in inventory:inventory=inventory['report']
        result=check(inventory,json.loads(Path(args.report).read_text()))
    except (ValueError,KeyError,TypeError,OSError):
        parser.exit(1,'RECONCILIATION: FAIL (invalid, missing or contradictory evidence)\n')
    print(json.dumps(result,sort_keys=True))
