"""Public retrieval adapter: gold stays with the grader, not the searchable corpus."""
import copy
import importlib
import importlib.util
import json
import math
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture
def adapter():
    assert importlib.util.find_spec('eval.longmemeval_retrieval') is not None, 'bounded LongMemEval retrieval adapter is required'
    return importlib.import_module('eval.longmemeval_retrieval')


@pytest.fixture
def record():
    return {'question_id':'fixture-1','question_type':'single-session-user',
        'question':'Which orchid cultivar did I prefer?', 'question_date':'2026/01/03',
        'answer':'GRADER_ONLY_CANARY','answer_session_ids':['answer_fixture'],
        'haystack_session_ids':['answer_fixture','unrelated_fixture'],
        'haystack_dates':['2026/01/01','2026/01/02'],
        'haystack_sessions':[
            [{'role':'user','content':'I saw an orchid yesterday.','has_answer':False},
             {'role':'user','content':'The orchid cultivar I prefer is cobalt.','has_answer':True}],
            [{'role':'user','content':'I went running near the river.'}]]}


def test_gold_and_gold_revealing_original_ids_are_not_in_actor_data(adapter,record):
    before=copy.deepcopy(record)
    actor,oracle=adapter.split_case(record)
    text=json.dumps(actor)
    assert all(s not in text for s in ('GRADER_ONLY_CANARY','answer_session_ids','has_answer','answer_fixture'))
    assert len(oracle['gold_sessions'])==1 and len(oracle['gold_turns'])==1
    assert record==before


def test_metrics_match_pinned_upstream_discount_and_distinguish_any_from_all(adapter):
    r=adapter.rank_metrics(['a','c','b'],{'a','b'},k=3)
    assert r['recall_any']==r['recall_all']==1
    assert r['ndcg']==pytest.approx((1+1/math.log2(3))/2)
    r=adapter.rank_metrics(['a','c'],{'a','b'},k=2)
    assert r['recall_any']==1 and r['recall_all']==0 and r['ndcg']==.5
    assert adapter.rank_metrics(['c'],{'a'},k=1)=={'recall_any':0.,'recall_all':0.,'ndcg':0.}


@pytest.mark.parametrize('fault',['bad-id-type','missing-gold','mismatched-arrays','label-type','too-many','bad-role','query-too-long'])
def test_malformed_or_out_of_scope_cases_fail_loudly(adapter,record,fault):
    if fault=='bad-id-type':record['haystack_session_ids'][1]={'not':'an identity'}
    elif fault=='missing-gold':record['answer_session_ids']=['missing-source']
    elif fault=='mismatched-arrays':record['haystack_dates'].pop()
    elif fault=='label-type':record['haystack_sessions'][0][0]['has_answer']='yes'
    elif fault=='too-many':
        record['haystack_session_ids']=[str(i) for i in range(101)]
        record['haystack_dates']=['2026/01/01']*101
        record['haystack_sessions']=[[{'role':'user','content':'note'}]]*101
    elif fault=='bad-role':record['haystack_sessions'][0][0]['role']='system'
    else:record['question']='q'*513
    with pytest.raises(ValueError):adapter.split_case(record)


@pytest.mark.parametrize('backend',['lexical','fts5'])
def test_real_retriever_session_hit_does_not_imply_excerpt_has_answer(adapter,record,tmp_path,backend):
    r=adapter.evaluate_case(record,tmp_path/'vault',revision='fixture',backend=backend,k=1)
    assert r['status']=='GRADED_RETRIEVAL_ONLY' and r['model_calls']==0
    assert r['candidate']['recall_all']==1 and r['baseline']['recall_all']==0
    # The shipped reader selects the first matching line, which lacks the answer.
    assert r['excerpt_evidence_turn_recall']==0
    assert r['returned_bytes']<=8192
    assert 'GRADER_ONLY_CANARY' not in ''.join(p.read_text() for p in (tmp_path/'vault').rglob('*.md'))


def test_abstention_keeps_case_without_inventing_retrieval_success(adapter,record,tmp_path):
    record['question_id']='fixture_abs';record['answer_session_ids']=[]
    r=adapter.evaluate_case(record,tmp_path/'vault',revision='fixture')
    assert r['status']=='NOT_SCORED_ABSTENTION' and r['candidate'] is None and r['baseline'] is None
    assert r['question_id']=='fixture_abs' and r['model_calls']==0


def test_empty_or_duplicate_gold_does_not_vacuously_pass(adapter):
    with pytest.raises(ValueError):adapter.rank_metrics(['a'],set(),k=1)
    with pytest.raises(ValueError):adapter.rank_metrics(['a','a'],{'a'},k=2)


def test_repeated_source_id_preserves_occurrences_dates_and_upstream_metric_identity(adapter,record,tmp_path):
    record['haystack_session_ids'].append(record['haystack_session_ids'][0])
    record['haystack_sessions'].append(copy.deepcopy(record['haystack_sessions'][0]))
    record['haystack_dates'].append('2026/01/03')
    actor,oracle=adapter.split_case(record)
    ids=[d['id'] for d in actor['documents']]
    assert len(set(ids))==3 and actor['documents'][0]['date']!=actor['documents'][2]['date']
    assert oracle['canonical_ids'][ids[0]]==oracle['canonical_ids'][ids[2]]
    r=adapter.rank_metrics([ids[2]],oracle['gold_sessions'],k=1,
                           canonical=oracle['canonical_ids'],corpus_ids=ids)
    assert r['recall_all']==r['recall_any']==r['ndcg']==1
    result=adapter.evaluate_case(record,tmp_path/'vault',revision='fixture')
    assert result['duplicate_source_occurrences']==1 and result['sessions']==3


def test_a_repeated_searchable_occurrence_cannot_inflate_recall(adapter,record,tmp_path):
    actor,_=adapter.split_case(record)
    actor['documents'][1]['id']=actor['documents'][0]['id']
    with pytest.raises(ValueError):adapter.materialize(tmp_path/'vault',actor,revision='fixture')


def test_actor_whitelist_refuses_later_gold_injection(adapter,record,tmp_path):
    actor,_=adapter.split_case(record)
    actor['documents'][0]['has_answer']=True
    with pytest.raises(ValueError,match='actor|field|schema'):
        adapter.materialize(tmp_path/'vault',actor,revision='fixture')


@pytest.mark.parametrize('fault',['gold-id','bad-role','bad-content'])
def test_actor_writer_revalidates_sanitized_field_values(adapter,record,tmp_path,fault):
    actor,_=adapter.split_case(record)
    if fault=='gold-id':actor['documents'][0]['id']='answer_fixture'
    elif fault=='bad-role':actor['documents'][0]['messages'][0]['role']='system'
    else:actor['documents'][0]['messages'][0]['content']={'has_answer':True}
    with pytest.raises(ValueError):adapter.materialize(tmp_path/'vault',actor,revision='fixture')
    assert not (tmp_path/'vault').exists()


def test_budget_failure_is_not_replaced_with_an_empty_success(adapter,record,tmp_path):
    with pytest.raises(ValueError,match='budget'):
        adapter.evaluate_case(record,tmp_path/'vault',revision='fixture',max_bytes=1)


def run_cli(tmp_path,rows,*,pin=None):
    raw=json.dumps(rows).encode();data=tmp_path/'dataset.json';data.write_bytes(raw)
    out=tmp_path/'results'
    cmd=[sys.executable,'-m','eval.run_longmemeval_retrieval','--dataset',str(data),
         '--sha256',pin or hashlib.sha256(raw).hexdigest(),'--revision','0'*40,
         '--expected-count','1','--output',str(out),'--timeout-seconds','10']
    run=subprocess.run(cmd,cwd=Path(__file__).resolve().parents[1],
        env={**os.environ,'PYTHONPATH':'src','HOME':str(tmp_path/'home'),'HARNESS_HOME':str(tmp_path/'hh')},
        capture_output=True,text=True,timeout=20)
    return run,out


def test_cli_grades_real_retrieval_and_retains_manifests_without_residual_corpus(record,tmp_path):
    # CLI's frozen top-5 policy needs more than five sessions for recency to miss.
    for n in range(5):
        record['haystack_session_ids'].append('recent-'+str(n))
        record['haystack_dates'].append('2026/01/0'+str(n+3))
        record['haystack_sessions'].append([{'role':'user','content':'I went running near the river.'}])
    run,out=run_cli(tmp_path,[record])
    assert run.returncode==0,run.stdout+run.stderr
    r=json.loads((out/'report.json').read_text())
    assert r['planned']==r['attempted']==r['graded']==1 and r['model_calls']==0
    assert r['metrics']['candidate']['recall_all']==1 and r['metrics']['baseline']['recall_all']==0
    assert r['full_v2']=='NOT_QUALIFIED' and r['promotion']=='NOT_GRANTED'
    assert r['by_question_type']['single-session-user']['graded']==1
    assert r['coverage_adjusted_recall_all_lower_bound']['candidate']==1
    assert not list(out.rglob('session-*.md')) and not list((out/'scratch').iterdir())
    row=json.loads((out/'results.jsonl').read_text())
    assert row['source_manifest']['documents'] and row['retrieval']['hits']
    assert 'GRADER_ONLY_CANARY' not in (out/'results.jsonl').read_text()


def test_last_five_baseline_includes_every_source_when_only_two_exist(adapter,record,tmp_path):
    r=adapter.evaluate_case(record,tmp_path/'vault',revision='fixture')
    assert r['baseline']['recall_all']==1


def test_cli_refuses_a_wrong_dataset_pin_before_creating_output(record,tmp_path):
    run,out=run_cli(tmp_path,[record],pin='f'*64)
    assert run.returncode==2 and 'hash' in run.stdout.lower()
    assert not out.exists()


def test_cli_cannot_report_an_empty_or_abstention_only_dataset_as_a_score(record,tmp_path):
    empty=tmp_path/'empty';empty.mkdir();run,out=run_cli(empty,[])
    assert run.returncode==2 and not out.exists()
    record['question_id']='fixture_abs';record['answer_session_ids']=[]
    abstain=tmp_path/'abstain';abstain.mkdir();run,out=run_cli(abstain,[record])
    assert run.returncode==1
    r=json.loads((out/'report.json').read_text())
    assert r['graded']==0 and r['metrics'] is None and r['abstention_excluded']==1
