"""Explicit-root, copy-only archive qualification. Never registers or changes a live index."""
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from .mcp.sessions import claude_messages, codex_messages, MSG_CHARS
from .redact import redact


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _read(path, root, limit):
    """Read a bounded owned regular file, refusing symlinks in its declared boundary."""
    path, root = Path(path).absolute(), Path(root).absolute()
    # Path.absolute/relative_to are lexical: root/../outside is not contained.
    if '..' in path.parts or '..' in root.parts:
        return 'EXCLUDED_SCOPE', None, None
    if path.suffix != '.jsonl':
        return 'EXCLUDED_TYPE', None, None
    try:
        rel = path.relative_to(root)
    except ValueError:
        return 'EXCLUDED_SCOPE', None, None
    try:
        for part in [root]+list(reversed(path.parents)) + [path]:
            if part == root or root in part.parents:
                if part.is_symlink():
                    return 'EXCLUDED_SYMLINK', None, None
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode):
            return 'EXCLUDED_TYPE', None, None
        if hasattr(os, 'getuid') and st.st_uid != os.getuid():
            return 'EXCLUDED_OWNER', None, None
        if not os.access(path, os.R_OK):
            return 'EXCLUDED_ACCESS', None, None
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'rb') as f:
            opened = os.fstat(f.fileno())
            if (opened.st_dev, opened.st_ino) != (st.st_dev, st.st_ino):
                return 'SOURCE_CHANGED', None, None
            data = f.read(limit+1)
            after = os.fstat(f.fileno())
        final = path.stat()
        identity = lambda s: (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if identity(st) != identity(after) or identity(st) != identity(final):
            return 'SOURCE_CHANGED', None, None
        return 'READ', data, {'source_id':_hash(str(path).encode()),'bytes':st.st_size,
                              'mtime_ns':st.st_mtime_ns,'relative_id':_hash(str(rel).encode())}
    except PermissionError:
        return 'EXCLUDED_ACCESS', None, None
    except FileNotFoundError:
        return 'MISSING', None, None
    except OSError:
        return 'READ_FAILED', None, None


def _format(e):
    if not isinstance(e, dict):
        return None
    if e.get('type') in ('user','assistant') and isinstance(e.get('message'),dict):
        return 'claude-code'
    p=e.get('payload')
    if e.get('type')=='session_meta' and isinstance(p,dict) and ('cwd' in p or 'id' in p):
        return 'codex'
    if (e.get('type')=='response_item' and isinstance(p,dict) and p.get('type')=='message'
            and p.get('role') in ('user','assistant')):
        return 'codex'
    if e.get('type') in ('started','result','launched') and 'agentId' in e and 'key' in e:
        return 'workflow-journal'
    if all(k in e for k in ('native_item_id','phase','role','text')):
        return 'native-excerpt'
    return None


def _events(data):
    offset=0
    for number, raw in enumerate(data.splitlines(keepends=True),1):
        end=offset+len(raw)
        if raw.strip():
            yield number,offset,end,raw,json.loads(raw)
        offset=end


def inspect_source(path, root, max_bytes=131072):
    """Envelope recognition only; no source text/path or inferred fact is returned."""
    if type(max_bytes) is not int or not 1<=max_bytes<=8*1024*1024:
        raise ValueError('max_bytes must be from 1 to 8388608')
    status,data,meta=_read(path,root,max_bytes)
    out={'status':status,'format':None,'semantic_extraction':'NOT_RUN'}
    if meta is None:
        return out
    out.update(meta)
    complete=len(data)<=max_bytes
    prefix=data if complete else data[:max_bytes]
    end=prefix.rfind(b'\n')+1
    out['inspection']='WHOLE_ENVELOPES' if complete and end==len(prefix) else 'PREFIX_ONLY'
    formats=set();count=0
    try:
        for _,_,_,_,e in _events(prefix[:end]):
            count+=1
            kind=_format(e)
            if kind:formats.add(kind)
    except (ValueError,UnicodeError,RecursionError):
        out['status']='MALFORMED';return out
    out['envelopes_inspected']=count
    out['status']='MIXED_FORMAT' if len(formats)>1 else ('FORMAT_SUPPORTED' if formats else 'UNRECOGNIZED')
    if len(formats)==1:
        out['format']=next(iter(formats))
        if out['format'] in ('workflow-journal','native-excerpt'):
            out['status']='DERIVED_RECORDS'
    return out


def extract_copy(path, root, expected_project, destination, max_bytes=8*1024*1024):
    """Stage a complete bounded source revision, preserving all selected history as history.

    Project identity must match the source's explicit cwd. Corrections are retained in
    order, never automatically resolved into current facts. Output is private and inert.
    """
    if not isinstance(expected_project,str) or not expected_project:
        raise ValueError('explicit expected project required')
    if type(max_bytes) is not int or not 1<=max_bytes<=64*1024*1024:
        raise ValueError('max_bytes must be from 1 to 67108864')
    status,data,meta=_read(path,root,max_bytes)
    result={'status':status,'live_index_changed':False,'semantic_extraction':'NOT_VERIFIED'}
    if meta is None:return result
    result.update(meta)
    if len(data)>max_bytes:
        result['status']='LIMIT';return result
    if data and not data.endswith(b'\n'):
        result['status']='INCOMPLETE_LINE';return result
    try:
        events=list(_events(data))
    except (ValueError,UnicodeError,RecursionError):
        result['status']='MALFORMED';return result
    formats={_format(e) for *_,e in events}-{None}
    if len(formats)!=1:
        result['status']='MIXED_FORMAT' if formats else 'UNSUPPORTED_FORMAT';return result
    kind=next(iter(formats));projects=set();records=[];excluded=0
    if kind not in ('claude-code','codex'):
        result['status']='UNSUPPORTED_FORMAT';return result
    revision=_hash(data)
    try:
        for number,start,end,raw,e in events:
            if not isinstance(e,dict):
                raise ValueError('invalid event')
            p=e.get('payload')
            scope=e.get('cwd') if kind=='claude-code' else (p.get('cwd') if e.get('type')=='session_meta' and isinstance(p,dict) else None)
            if scope is not None:
                if not isinstance(scope,str) or not scope:raise ValueError('invalid scope')
                projects.add(scope)
            selected=list(claude_messages(e) if kind=='claude-code' else codex_messages(e))
            if not selected:excluded+=1
            for part,(role,text) in enumerate(selected):
                clean=redact(text)
                records.append({'source_id':meta['source_id'],'source_revision':revision,
                    'record_id':_hash((revision+':'+str(start)+':'+str(part)).encode()),
                    'line':number,'byte_start':start,'byte_end':end,'record_sha256':_hash(raw),
                    'role':role,'text':clean[:MSG_CHARS],'truncated':len(clean)>MSG_CHARS,
                    'timestamp':redact(str(e.get('timestamp') or ''))[:128],'current_fact':False})
    except (AttributeError,TypeError,ValueError,RecursionError):
        result['status']='MALFORMED';return result
    if projects!={expected_project}:
        result['status']='SCOPE_UNRESOLVED';return result
    if not records:
        result['status']='NO_CONVERSATION';return result
    packet={'schema':'harness.archive-copy/v1','source_id':meta['source_id'],'revision':revision,
        'format':kind,'project_id':_hash(expected_project.encode()),'privacy':'private-project',
        'authority':'source-data','correction_resolution':'NOT_INFERRED','records':records,
        'excluded_records':excluded,'source_bytes':len(data),'semantic_extraction':'NOT_VERIFIED'}
    destination=Path(destination).absolute()
    if any(p.is_symlink() for p in [destination]+list(destination.parents)):
        result['status']='EXCLUDED_DESTINATION';return result
    if destination.exists():
        result['status']='DESTINATION_EXISTS';return result
    temp=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=destination.parent,
                                         prefix='.archive-copy-',delete=False) as f:
            temp=Path(f.name)
            json.dump(packet,f,ensure_ascii=False)
            f.flush();os.fsync(f.fileno())
        os.link(temp,destination)  # atomic, no replacing an earlier evidence packet
    except FileExistsError:
        result['status']='DESTINATION_EXISTS';return result
    except OSError:
        result['status']='WRITE_FAILED';return result
    finally:
        if temp is not None:temp.unlink(missing_ok=True)
    result.update(status='STAGED_COPY',revision=revision,records=len(records),excluded_records=excluded)
    return result
