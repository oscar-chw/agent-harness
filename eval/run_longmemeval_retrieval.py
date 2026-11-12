"""Reproducible, no-model retrieval component run on an explicitly pinned dataset."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import re
import stat
import tempfile
import time

import agent_harness
from agent_harness import vault_retrieval, vault_sources
from agent_harness.mcp import kb
from . import longmemeval_retrieval as A

MIB=1024*1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read_dataset(path,pin,count):
    if not re.fullmatch('[0-9a-f]{64}',pin):raise ValueError('dataset SHA-256 is required')
    path=Path(path)
    if path.is_symlink() or path.name.startswith('.env') or path.name in ('auth.json','id_rsa','id_ed25519'):
        raise ValueError('dataset cannot be redirected or credential storage')
    flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
    with os.fdopen(os.open(path,flags),'rb') as f:
        info=os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size>512*MIB:
            raise ValueError('dataset must be a regular file within 512 MiB')
        raw=f.read(512*MIB+1)
    if len(raw)>512*MIB or sha(raw)!=pin:raise ValueError('dataset hash or byte limit mismatch')
    def bad_constant(_):raise ValueError('non-finite JSON is not benchmark data')
    rows=json.loads(raw,object_pairs_hook=vault_sources._unique_object,parse_constant=bad_constant)
    if not isinstance(rows,list) or len(rows)!=count or not rows:
        raise ValueError('dataset row count does not match the frozen positive count')
    ids=[r.get('question_id') if isinstance(r,dict) else None for r in rows]
    if any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids):
        raise ValueError('dataset question identities are invalid or repeated')
    return rows,len(raw)


def summary(rows,planned):
    graded=[r for r in rows if r['status']=='GRADED_RETRIEVAL_ONLY']
    excluded=sum(r['status']=='NOT_SCORED_ABSTENTION' for r in rows)
    errors=sum(r['status']=='INPUT_SCOPE_OR_EXECUTION_ERROR' for r in rows)
    unrun=sum(r['status']=='NOT_RUN' for r in rows)
    metrics=None
    if graded:
        metrics={arm:{key:sum(r[arm][key] for r in graded)/len(graded)
                      for key in ('recall_any','recall_all','ndcg')} for arm in ('candidate','baseline')}
        diff=[r['candidate']['recall_all']-r['baseline']['recall_all'] for r in graded]
        randomizer=random.Random(20261106)
        samples=sorted(sum(randomizer.choice(diff) for _ in diff)/len(diff) for _ in range(1000))
        metrics['paired_recall_all_delta']={'mean':sum(diff)/len(diff),
            'bootstrap_95_percentile':[samples[24],samples[974]],'resamples':1000,'seed':20261106,
            'limit':'conditional on graded cases; questions may be dependent'}
    observed_excerpts=[r['excerpt_evidence_turn_recall'] for r in graded
                       if r.get('excerpt_evidence_turn_recall') is not None]
    planned_nonabstention=planned-sum('_abs' in r['question_id'] for r in rows)
    return {'planned':planned,'attempted':planned-unrun,'graded':len(graded),
        'abstention_excluded':excluded,'errors':errors,'not_run':unrun,'metrics':metrics,
        'status':'NO_SCORABLE_RECORDS' if not graded else 'PARTIAL_RETRIEVAL_COMPONENT' if errors or unrun
                 else 'COMPLETED_RETRIEVAL_COMPONENT',
        'model_calls':0,'full_v2':'NOT_QUALIFIED','promotion':'NOT_GRANTED',
        'excerpt_evidence_turn_recall':{'n':len(observed_excerpts),
            'mean':sum(observed_excerpts)/len(observed_excerpts) if observed_excerpts else None,
            'scope':'additional evidence-turn-occurrence coverage, not answer correctness'},
        'coverage_adjusted_recall_all_lower_bound':{
            arm:sum(r[arm]['recall_all'] for r in graded)/planned_nonabstention if planned_nonabstention else None
            for arm in ('candidate','baseline')},
        'token_efficiency':'NOT_MEASURED; no model was used',
        'scope':'adapted both-role shared-note retrieval and declared session labels; no QA or leaderboard claim'}


def run(args):
    if (not 1<=args.expected_count<=5000 or not 1<=args.timeout_seconds<=600
            or not 1<=args.max_output_mib<=128 or not re.fullmatch('[0-9a-f]{40}',args.revision)):
        raise ValueError('invalid dataset count, runtime, output budget or revision')
    rows,source_bytes=_read_dataset(args.dataset,args.sha256,args.expected_count)
    out=Path(args.output)
    if out.exists() or out.is_symlink():raise ValueError('output exists; preserve the old attempt')
    out.mkdir(mode=0o700);scratch=out/'scratch';scratch.mkdir()
    modules={'agent_harness':agent_harness,'vault_retrieval':vault_retrieval,
             'vault_sources':vault_sources,'kb':kb,'adapter':A}
    pins={name:sha(Path(module.__file__).read_bytes()) for name,module in modules.items()}
    freeze={'schema':'harness.longmemeval-retrieval-run/v1','dataset_sha256':args.sha256,
        'dataset_revision':args.revision,'source_bytes':source_bytes,'expected_count':args.expected_count,
        'package_version':agent_harness.__version__,'module_sha256':pins,
        'runner_sha256':sha(Path(__file__).read_bytes()),'backend':args.backend,'top_k':5,
        'retrieval_budget_bytes':8192,'context_lines':0,'timeout_seconds':args.timeout_seconds,
        'max_output_mib':args.max_output_mib,'models_called':0,
        'environment':{'python':platform.python_version(),'system':platform.system(),'machine':platform.machine()},
        'artifact_policy':'retain exact input pin, derivative manifests and observed packets; clean only owned temporary generated corpora'}
    (out/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    (out/'consumed.json').write_text(json.dumps({'attempt':1,'planned':len(rows),'automatic_retry':False})+'\n')
    results=[];started=time.perf_counter();written=0;stop=False
    with (out/'results.jsonl').open('x') as sink,(out/'attempts.jsonl').open('x') as attempts:
        for index,record in enumerate(rows):
            if time.perf_counter()-started>args.timeout_seconds or written>args.max_output_mib*MIB:
                stop=True
            if stop:
                result={'index':index,'question_id':record['question_id'],'status':'NOT_RUN',
                        'question_type':record.get('question_type','UNKNOWN'),
                        'reason':'wall-time or retained-output budget reached','model_calls':0}
            else:
                attempts.write(json.dumps({'index':index,'question_id':record['question_id'],'status':'STARTED'})+'\n');attempts.flush()
                try:
                    with tempfile.TemporaryDirectory(prefix='case-',dir=scratch) as directory:
                        case_root=Path(directory)/'vault'
                        result=A.evaluate_case(record,case_root,revision=args.revision,backend=args.backend)
                        if case_root.exists():
                            result['source_manifest']=json.loads((case_root/'manifest.json').read_text())
                    result['index']=index
                except (ValueError,TypeError,KeyError,OSError) as error:
                    result={'index':index,'question_id':record['question_id'],'status':'INPUT_SCOPE_OR_EXECUTION_ERROR',
                            'question_type':record.get('question_type','UNKNOWN'),
                            'error_type':type(error).__name__,'error':str(error)[:256],'model_calls':0}
            raw=json.dumps(result,ensure_ascii=False)+'\n';sink.write(raw);sink.flush();written+=len(raw.encode())
            results.append(result)
            if (index+1)%25==0 or index+1==len(rows):
                print(json.dumps({'processed':index+1,'planned':len(rows),'elapsed_seconds':round(time.perf_counter()-started,2)}),flush=True)
    if any(sha(Path(modules[n].__file__).read_bytes())!=h for n,h in pins.items()):
        raise ValueError('benchmark implementation changed during the run')
    report=summary(results,len(rows));report.update({'elapsed_seconds':time.perf_counter()-started,
        'dataset_sha256':args.sha256,'dataset_revision':args.revision,
        'results_sha256':sha((out/'results.jsonl').read_bytes()),'freeze_sha256':sha((out/'freeze.json').read_bytes()),
        'source_bytes':source_bytes,'retained_result_bytes':written,
        'development_first20':summary(results[:20],min(20,len(rows))),
        'remaining_cases':summary(results[20:],max(0,len(rows)-20))})
    report['by_question_type']={kind:summary([r for r in results if r.get('question_type')==kind],
                                           sum(r.get('question_type')==kind for r in results))
                                for kind in sorted({r.get('question_type','UNKNOWN') for r in results})}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','planned','attempted','graded','errors','abstention_excluded','elapsed_seconds')}))
    return 0 if report['status']=='COMPLETED_RETRIEVAL_COMPONENT' else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',required=True)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--revision',required=True)
    parser.add_argument('--expected-count',type=int,required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--backend',choices=('lexical','fts5'),default='lexical')
    parser.add_argument('--timeout-seconds',type=int,default=180)
    parser.add_argument('--max-output-mib',type=int,default=64)
    args=parser.parse_args()
    try:return run(args)
    except (OSError,ValueError,TypeError,KeyError) as error:
        print(json.dumps({'status':'REFUSED_OR_FAILED','reason':str(error)[:256],'model_calls':0}))
        return 2


if __name__=='__main__':raise SystemExit(main())
