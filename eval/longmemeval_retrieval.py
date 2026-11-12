"""LongMemEval retrieval adapter, not a QA judge or official end-to-end score.

The released scorer's binary DCG formula is preserved. This adapter indexes both
conversation roles as pinned shared notes, unlike upstream's user-only flat
index. Session IDs containing gold markers are made opaque before indexing.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import time

from agent_harness.vault_retrieval import search_shared_documents


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _identifier(value):
    if (not isinstance(value,str) or not value or len(value)>256
            or any(ord(c)<32 or ord(c)==127 for c in value)):
        raise ValueError('invalid session identity')
    return 'd-'+_sha(value.encode())[:32]


def split_case(record):
    """Project only message content into actor data; retain all labels at root."""
    if not isinstance(record,dict):raise ValueError('case must be an object')
    for key in ('question_id','question_type','question','question_date'):
        if not isinstance(record.get(key),str) or not record[key].strip():
            raise ValueError('case field missing: '+key)
    if len(record['question'])>512:raise ValueError('question exceeds shipped query scope')
    ids,dates,sessions=(record.get(k) for k in ('haystack_session_ids','haystack_dates','haystack_sessions'))
    if (not isinstance(ids,list) or not 1<=len(ids)<=100
            or any(not isinstance(x,str) for x in ids)
            or not isinstance(dates,list) or not isinstance(sessions,list)
            or len(ids)!=len(dates) or len(ids)!=len(sessions)):
        raise ValueError('session arrays must align within the 100-document scope')
    identities={identity:_identifier(identity) for identity in ids}
    gold=record.get('answer_session_ids')
    if (not isinstance(gold,list) or any(not isinstance(x,str) or x not in identities for x in gold)
            or len(set(gold))!=len(gold) or not gold and '_abs' not in record['question_id']):
        raise ValueError('gold session labels are missing or outside the corpus')
    documents=[];gold_turns={};canonical_ids={}
    for position,(identity,date,session) in enumerate(zip(ids,dates,sessions)):
        if not isinstance(date,str) or not date or not isinstance(session,list) or not session:
            raise ValueError('session needs a timestamp and message list')
        messages=[];marked=[]
        for index,turn in enumerate(session):
            if (not isinstance(turn,dict) or turn.get('role') not in ('user','assistant')
                    or not isinstance(turn.get('content'),str)
                    or 'has_answer' in turn and type(turn['has_answer']) is not bool):
                raise ValueError('invalid message or evidence label')
            messages.append({'role':turn['role'],'content':turn['content']})
            if turn.get('has_answer') is True:marked.append(index+4)
        # Released histories can repeat a source ID at different timestamps.
        # Preserve occurrences, but use the original identity only at grading.
        opaque='d-'+_sha(json.dumps([position,identity]).encode())[:32]
        canonical_ids[opaque]=identities[identity]
        documents.append({'id':opaque,'date':date,'messages':messages})
        if marked:gold_turns[opaque]=marked
    actor={'question':record['question'],'question_date':record['question_date'],'documents':documents}
    if len(json.dumps(actor,ensure_ascii=False).encode())>4*1024*1024:
        raise ValueError('case exceeds the shipped 4 MiB source scope')
    return actor,{'question_id':record['question_id'],'question_type':record['question_type'],
        'abstention':'_abs' in record['question_id'],
        'gold_sessions':[identities[x] for x in gold],'gold_turns':gold_turns,
        'canonical_ids':canonical_ids,'duplicate_source_occurrences':len(ids)-len(set(ids))}


def materialize(root,actor,*,revision):
    """Write a fresh explicit corpus; never use labels or input IDs as titles."""
    if not isinstance(actor,dict) or set(actor)!={'question','question_date','documents'}:
        raise ValueError('actor schema contains unexpected fields')
    if (not isinstance(actor['question'],str) or not 1<=len(actor['question'])<=512
            or not isinstance(actor['question_date'],str) or not isinstance(actor['documents'],list)
            or not 1<=len(actor['documents'])<=100):
        raise ValueError('invalid actor field values')
    if not isinstance(revision,str) or not revision:raise ValueError('dataset revision is required')
    seen=set()
    for d in actor['documents']:
        if (not isinstance(d,dict) or set(d)!={'id','date','messages'}
                or not isinstance(d['id'],str) or not re.fullmatch('d-[0-9a-f]{32}',d['id'])
                or d['id'] in seen or not isinstance(d['date'],str)
                or not isinstance(d['messages'],list) or not d['messages']
                or any(not isinstance(m,dict) or set(m)!={'role','content'}
                       or m['role'] not in ('user','assistant') or not isinstance(m['content'],str)
                       for m in d['messages'])):
            raise ValueError('actor document fields contain labels or unknown metadata')
        seen.add(d['id'])
    root=Path(root);root.mkdir(mode=0o700)
    documents=[];total=0
    for index,d in enumerate(actor['documents']):
        title='Conversation session '+str(index+1)
        # One JSON-escaped message per source line gives exact, stable turn spans.
        text='id: '+d['id']+'\ntitle: '+title+'\ndate: '+json.dumps(d['date'])+'\n'
        text+=''.join(json.dumps(m,ensure_ascii=False)+'\n' for m in d['messages'])
        raw=text.encode();total+=len(raw)
        if len(raw)>1024*1024 or total>4*1024*1024:
            raise ValueError('rendered sources exceed the shipped search scope')
        name=f'session-{index:03d}.md'
        (root/name).write_bytes(raw)
        documents.append({'id':d['id'],'title':title,'path':name,'sha256':_sha(raw),
            'document_type':'method_note','rights':{'redistribution':'public','license':'MIT',
              'basis':'Publisher dataset card declares MIT; local benchmark adaptation, not legal certification.'},
            'source_refs':[{'uri':'urn:longmemeval:'+d['id'],'kind':'benchmark_conversation','revision':revision}]})
    raw=json.dumps({'schema':'quant-shared-notes/v1','revision':revision,'documents':documents},ensure_ascii=False).encode()
    (root/'manifest.json').write_bytes(raw)
    return {'manifest_sha256':_sha(raw),'source_bytes':total,'allowed_ids':[d['id'] for d in documents]}


def rank_metrics(ranked,gold,*,k,canonical=None,corpus_ids=None):
    """Match eval_utils.py's recall-any/all and original binary DCG discount."""
    if (not isinstance(ranked,list) or len(set(ranked))!=len(ranked)
            or type(k) is not int or k<1 or not gold):
        raise ValueError('retrieval metrics need unique ranks, nonempty gold and positive k')
    gold=set(gold);ranked=ranked[:k]
    if canonical is not None:
        if (not isinstance(canonical,dict) or not isinstance(corpus_ids,list)
                or len(set(corpus_ids))!=len(corpus_ids) or set(corpus_ids)!=set(canonical)
                or any(x not in canonical for x in ranked)):
            raise ValueError('complete occurrence-to-source grading map required')
        recalled={canonical[x] for x in ranked}
        relevant=[int(canonical[x] in gold) for x in ranked]
        ideal_count=min(k,sum(canonical[x] in gold for x in corpus_ids))
    else:
        recalled=set(ranked);relevant=[int(x in gold) for x in ranked]
        ideal_count=min(k,len(gold))
    def dcg(values):
        return sum(v if i==0 else v/math.log2(i+1) for i,v in enumerate(values))
    ideal=dcg([1]*ideal_count)
    if not ideal:raise ValueError('gold has no corpus occurrence')
    return {'recall_any':float(bool(recalled&gold)),
            'recall_all':float(gold<=recalled),'ndcg':dcg(relevant)/ideal}


def evaluate_case(record,root,*,revision,backend='lexical',k=5,max_bytes=8192):
    start=time.perf_counter();actor,oracle=split_case(record)
    result={'question_id':oracle['question_id'],'question_type':oracle['question_type'],
        'actor_sha256':_sha(json.dumps(actor,sort_keys=True,ensure_ascii=False).encode()),
        'sessions':len(actor['documents']),'model_calls':0,'backend':backend,
        'duplicate_source_occurrences':oracle['duplicate_source_occurrences'],
        'metric_scope':'adapted both-role shared-note retrieval; no answer generation'}
    if oracle['abstention']:
        return {**result,'status':'NOT_SCORED_ABSTENTION','candidate':None,'baseline':None}
    scope=materialize(root,actor,revision=revision)
    packet=search_shared_documents(root,vault_id='longmemeval-local',manifest='manifest.json',
        manifest_sha256=scope['manifest_sha256'],allowed_ids=scope['allowed_ids'],
        query=actor['question'],backend=backend,max_results=k,max_bytes=max_bytes,context_lines=0)
    ranked=[h['document_id'] for h in packet['hits']]
    total=sum(len(v) for v in oracle['gold_turns'].values());found=0
    for h in packet['hits']:
        found+=sum(h['citation']['start_line']<=line<=h['citation']['end_line']
                   for line in oracle['gold_turns'].get(h['document_id'],[]))
    metric_args={'k':k,'canonical':oracle['canonical_ids'],'corpus_ids':scope['allowed_ids']}
    return {**result,'status':'GRADED_RETRIEVAL_ONLY',
        'candidate':rank_metrics(ranked,oracle['gold_sessions'],**metric_args),
        'baseline':rank_metrics(list(reversed(scope['allowed_ids']))[:k],oracle['gold_sessions'],**metric_args),
        'excerpt_evidence_turn_recall':found/total if total else None,
        'returned_bytes':len(json.dumps(packet,ensure_ascii=False).encode()),
        'source_bytes':scope['source_bytes'],'retrieval':packet,
        'elapsed_seconds':time.perf_counter()-start}
