"""Copy-only archive qualification: metadata is not semantic/current-fact authority."""
import hashlib
import json


def api():
    from agent_harness import archive_sources
    return archive_sources


def transcript(root, name, events):
    path = root/name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b''.join(json.dumps(e).encode()+b'\n' for e in events))
    return path


def claude(text, project='project-a'):
    return {'type':'user','cwd':project,'sessionId':'session-a','message':{'content':text}}


def test_prefix_recognizes_format_but_never_claims_full_extraction(tmp_path):
    source = transcript(tmp_path, 'a.jsonl', [claude('old fact'),claude('x'*2000)])
    result = api().inspect_source(source,tmp_path,max_bytes=256)
    assert result['format']=='claude-code' and result['status']=='FORMAT_SUPPORTED'
    assert result['inspection']=='PREFIX_ONLY' and result['semantic_extraction']=='NOT_RUN'
    assert 'old fact' not in json.dumps(result) and str(tmp_path) not in json.dumps(result)


def test_extraction_preserves_correction_sequence_provenance_and_redacts_before_cut(tmp_path):
    source = transcript(tmp_path,'a.jsonl',[claude('cutoff Tuesday'),claude('Correction: cutoff Friday ghp_'+'X'*36)])
    original=source.read_bytes(); dest=tmp_path/'copy.json'
    result=api().extract_copy(source,tmp_path,'project-a',dest)
    assert result['status']=='STAGED_COPY' and source.read_bytes()==original
    packet=json.loads(dest.read_text())
    assert packet['revision']==hashlib.sha256(original).hexdigest()
    assert [r['text'].split()[1] for r in packet['records']]==['Tuesday','cutoff']
    assert 'Friday' in packet['records'][1]['text'] and 'ghp_' not in dest.read_text()
    assert all(r['current_fact'] is False for r in packet['records'])
    for r in packet['records']:
        raw=original[r['byte_start']:r['byte_end']]
        assert hashlib.sha256(raw).hexdigest()==r['record_sha256']
    assert packet['correction_resolution']=='NOT_INFERRED'
    assert result['live_index_changed'] is False


def test_codex_metadata_scope_and_messages_share_one_adapter(tmp_path):
    source=transcript(tmp_path,'arbitrary-export.jsonl',[
        {'type':'session_meta','payload':{'cwd':'project-a','id':'session-a'}},
        {'type':'response_item','payload':{'type':'message','role':'assistant','content':[{'type':'output_text','text':'A result'}]}},
        {'type':'event_msg','payload':{'type':'token_count'}}])
    dest=tmp_path/'copy.json'
    result=api().extract_copy(source,tmp_path,'project-a',dest)
    assert result['status']=='STAGED_COPY'
    packet=json.loads(dest.read_text())
    assert packet['format']=='codex' and len(packet['records'])==1
    assert packet['excluded_records']==2


def test_scope_missing_or_mixed_fails_without_writing(tmp_path):
    for index,events in enumerate(([{'type':'assistant','message':{'content':'unknown'}}],
                                   [claude('a'),claude('b','project-b')])):
        source=transcript(tmp_path,f'{index}.jsonl',events);dest=tmp_path/f'{index}.json'
        result=api().extract_copy(source,tmp_path,'project-a',dest)
        assert result['status']=='SCOPE_UNRESOLVED'
        assert not dest.exists()


def test_malformed_unknown_and_mixed_formats_do_not_silently_pass(tmp_path):
    sources=[transcript(tmp_path,'unknown.jsonl',[{'other':'PRIVATE'}]),
             transcript(tmp_path,'mixed.jsonl',[claude('a'),{'type':'session_meta','payload':{'cwd':'project-a'}}])]
    malformed=tmp_path/'bad.jsonl';malformed.write_bytes(b'{bad}\n');sources.append(malformed)
    for i,source in enumerate(sources):
        dest=tmp_path/f'{i}.json'
        result=api().extract_copy(source,tmp_path,'project-a',dest)
        assert result['status'] in ('UNSUPPORTED_FORMAT','MIXED_FORMAT','MALFORMED')
        assert not dest.exists() and 'PRIVATE' not in json.dumps(result)


def test_symlink_outside_and_access_denial_are_never_followed(tmp_path,monkeypatch):
    root=tmp_path/'root';root.mkdir()
    outside=transcript(tmp_path,'outside.jsonl',[claude('secret')])
    link=root/'link.jsonl';link.symlink_to(outside)
    assert api().inspect_source(link,root)['status']=='EXCLUDED_SYMLINK'
    assert api().inspect_source(outside,root)['status']=='EXCLUDED_SCOPE'
    source=transcript(root,'source.jsonl',[claude('secret')])
    monkeypatch.setattr(api().os,'access',lambda *a:False)
    assert api().inspect_source(source,root)['status']=='EXCLUDED_ACCESS'


def test_limits_partial_lines_and_existing_destination_preserve_originals(tmp_path):
    source=transcript(tmp_path,'a.jsonl',[claude('x'*2000)])
    dest=tmp_path/'copy.json';dest.write_text('precious')
    assert api().extract_copy(source,tmp_path,'project-a',dest,max_bytes=100)['status']=='LIMIT'
    assert api().extract_copy(source,tmp_path,'project-a',dest)['status']=='DESTINATION_EXISTS'
    assert dest.read_text()=='precious'
    source.write_bytes(source.read_bytes().rstrip(b'\n'))
    assert api().extract_copy(source,tmp_path,'project-a',tmp_path/'new.json')['status']=='INCOMPLETE_LINE'


def test_sidechain_excluded_and_revisions_do_not_overwrite_prior_evidence(tmp_path):
    source=transcript(tmp_path,'a.jsonl',[claude('old'),dict(claude('worker'),isSidechain=True)])
    first=tmp_path/'first.json';second=tmp_path/'second.json'
    api().extract_copy(source,tmp_path,'project-a',first)
    one=json.loads(first.read_text());assert len(one['records'])==1
    source.write_bytes(source.read_bytes().replace(b'old',b'new'))
    api().extract_copy(source,tmp_path,'project-a',second)
    two=json.loads(second.read_text())
    assert one['source_id']==two['source_id'] and one['revision']!=two['revision']
    assert one['records'][0]['text']=='old' and two['records'][0]['text']=='new'
    assert first.read_text()!=second.read_text()


def test_non_transcript_files_are_rejected_before_read(tmp_path):
    source=tmp_path/'settings.env';source.write_text('PRIVATE')
    assert api().inspect_source(source,tmp_path)['status']=='EXCLUDED_TYPE'


def test_destination_is_private_and_never_follows_a_link(tmp_path):
    source=transcript(tmp_path,'a.jsonl',[claude('a')])
    dest=tmp_path/'copy.json'
    assert api().extract_copy(source,tmp_path,'project-a',dest)['status']=='STAGED_COPY'
    assert dest.stat().st_mode & 0o777 == 0o600
    link=tmp_path/'link';link.symlink_to(tmp_path,target_is_directory=True)
    assert api().extract_copy(source,tmp_path,'project-a',link/'other.json')['status']=='EXCLUDED_DESTINATION'


def test_source_change_during_read_fails_closed(tmp_path,monkeypatch):
    source=transcript(tmp_path,'a.jsonl',[claude('a')])
    original=api().os.fstat;calls=[]
    def changed(fd):
        calls.append(1)
        if len(calls)==2:
            with source.open('ab') as f:f.write(b'{}\n')
        return original(fd)
    monkeypatch.setattr(api().os,'fstat',changed)
    assert api().inspect_source(source,tmp_path)['status']=='SOURCE_CHANGED'


def test_derived_records_are_classified_but_not_promoted_to_conversation(tmp_path):
    fixtures=[('workflow-journal',{'type':'result','agentId':'a','key':'k','result':{'text':'tool claim'}}),
              ('native-excerpt',{'native_item_id':'n','phase':'final','role':'assistant','text':'derived claim'})]
    for index,(kind,event) in enumerate(fixtures):
        source=transcript(tmp_path,f'{index}.jsonl',[event])
        info=api().inspect_source(source,tmp_path)
        assert info['format']==kind and info['status']=='DERIVED_RECORDS'
        out=tmp_path/f'{index}.json'
        assert api().extract_copy(source,tmp_path,'project-a',out)['status']=='UNSUPPORTED_FORMAT'
        assert not out.exists()


def test_parent_traversal_never_crosses_declared_root(tmp_path,monkeypatch):
    root=tmp_path/'root';root.mkdir()
    outside=transcript(tmp_path,'outside.jsonl',[claude('outside')])
    path=root/'..'/outside.name
    dest=tmp_path/'copy.json'
    assert api().inspect_source(path,root)['status']=='EXCLUDED_SCOPE'
    assert api().extract_copy(path,root,'project-a',dest)['status']=='EXCLUDED_SCOPE'
    assert not dest.exists()


def test_arbitrary_timestamp_text_does_not_bypass_redaction(tmp_path):
    secret='ghp_'+'X'*36  # secret-scan: allow
    event=claude('A normal message');event['timestamp']=secret
    source=transcript(tmp_path,'a.jsonl',[event]);dest=tmp_path/'copy.json'
    assert api().extract_copy(source,tmp_path,'project-a',dest)['status']=='STAGED_COPY'
    assert secret not in dest.read_text()
