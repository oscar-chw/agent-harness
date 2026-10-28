"""An inventory join must not hide a source or mislabel a recognized adapter."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest


def load():
    path=Path(__file__).resolve().parents[1]/'eval/check_source_reconciliation.py'
    spec=importlib.util.spec_from_file_location('reconcile_gate',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.check


def fixture():
    entry={'id':'a','root':'r','kind':'archive-jsonl','bytes':7,'mtime_ns':2,'coverage':'READER_UNSUPPORTED'}
    base={'eligible_files':1,'entries':[entry]}
    base['metadata_manifest_sha256']=hashlib.sha256(json.dumps(base['entries'],sort_keys=True).encode()).hexdigest()
    row={**entry,'live_import':False,'current_fact_authority':False,'source_state':'UNCHANGED_METADATA',
         'admission':'CANDIDATE_COPY_ONLY','format_inspection':{'status':'FORMAT_SUPPORTED','format':'claude-code'}}
    report={'denominator':1,'source_manifest_sha256':base['metadata_manifest_sha256'],'entries':[row],
            'admission':{'CANDIDATE_COPY_ONLY':1},'complete_migration':False,'semantic_extraction':'NOT_VERIFIED'}
    return base,report


def test_valid_candidate_join_is_not_a_migration_verdict():
    base,report=fixture()
    result=load()(base,report)
    assert result['sources']==1 and result['complete_migration'] is False


@pytest.mark.parametrize('mutation',['missing','duplicate','changed-baseline','wrong-admission','false-migration','wrong-count'])
def test_false_completion_and_wrong_denominator_fail(mutation):
    base,report=fixture();report=copy.deepcopy(report)
    if mutation=='missing':report['entries']=[]
    elif mutation=='duplicate':report['entries']*=2
    elif mutation=='changed-baseline':base['entries'][0]['bytes']=9
    elif mutation=='wrong-admission':report['entries'][0]['admission']='FAILED_OR_UNRESOLVED'
    elif mutation=='false-migration':report['complete_migration']=True
    elif mutation=='wrong-count':report['admission']={'CANDIDATE_COPY_ONLY':2}
    with pytest.raises(ValueError):load()(base,report)
