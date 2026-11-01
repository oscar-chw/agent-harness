"""Paired CPU retrieval probe. No model calls; response bytes are not model tokens."""
import argparse
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]


def load(name, source, directory):
    file = directory/(name+'.py')
    file.write_text(source)
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(baseline='5bf8d32', repetitions=7):
    sha = subprocess.check_output(['git','rev-parse','--verify','--end-of-options',baseline+'^{commit}'],
                                  cwd=ROOT, text=True).strip()
    old = subprocess.check_output(['git','show',sha+':src/agent_harness/mcp/kb.py'],cwd=ROOT,text=True)
    new = (ROOT/'src/agent_harness/mcp/kb.py').read_text()
    result = {'baseline_revision':sha, 'candidate_kb_sha256':hashlib.sha256(new.encode()).hexdigest(),
              'scope':'synthetic CPU queries; no model quality or token claim','cases':{}}
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        modules = {'baseline':load('baseline',old,temp),'candidate':load('candidate',new,temp)}
        for case in ('broad','selective','changed_source'):
            docs = temp/case/'docs';docs.mkdir(parents=True)
            count = 40 if case=='changed_source' else 600
            for i in range(count):
                body = ('encryption backup rotation service config. '*20
                        if case=='broad' else 'routine deployment log. '*20)
                (docs/f'{i:04}.md').write_text('# Guide\n'+body+'\n')
            target = docs/'0000.md'
            if case!='broad': target.write_text('# Guide\nquartz staging port 5433.\n')
            query = 'backup encryption' if case=='broad' else 'quartz staging port'
            stores = {}; samples = {name:[] for name in modules}; cold = {}
            for name, module in modules.items():
                if hasattr(module,'_short_stem'): module._short_stem.cache_clear()
                start=time.perf_counter()
                stores[name]=module.KB(home=temp/(case+'-'+name),paths=[docs],fts=True)
                stores[name].search(query)
                cold[name]=(time.perf_counter()-start)*1000
            responses = {}
            try:
                for i in range(repetitions):
                    if case=='changed_source':
                        target.write_text(f'# Guide\nquartz staging port {5433+i}.\n')
                        os.utime(target,(1700000000+i,1700000000+i))
                    for name in (list(modules) if i%2==0 else list(reversed(modules))):
                        start=time.perf_counter();responses[name]=stores[name].search(query)
                        samples[name].append((time.perf_counter()-start)*1000)
                    assert responses['candidate']==responses['baseline'],case+' changed ordered hits/scores'
                    if case=='changed_source':
                        assert str(5433+i) in responses['candidate'][0]['snippet']
                result['cases'][case]={'documents':count,'repetitions':repetitions,
                    'ordered_responses_equal':True,'response_bytes':len(json.dumps(responses['candidate']).encode()),
                    'cold_ms':{n:round(v,3) for n,v in cold.items()},
                    'warm_median_ms':{n:round(statistics.median(v),3) for n,v in samples.items()},
                    'samples_ms':{n:[round(x,3) for x in v] for n,v in samples.items()}}
            finally:
                for store in stores.values(): store.close()
        candidate=modules['candidate']
        if hasattr(candidate,'_short_stem'):
            candidate._short_stem.cache_clear();gc.collect();tracemalloc.start()
            for i in range(3000): candidate._stem('\U00010400'*55+f'{i:06}'+'ing')
            gc.collect();retained,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            assert candidate._short_stem.cache_info().currsize<=1024
            assert retained < 4*1024*1024
            result['short_stem_cache']={'retained_bytes_probe':retained,'peak_bytes_probe':peak,
                'entries':candidate._short_stem.cache_info().currsize,'probe':'3000 distinct 64-character wide-Unicode terms'}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',default='5bf8d32')
    parser.add_argument('--repetitions',type=int,default=7)
    args=parser.parse_args()
    if not 3<=args.repetitions<=30: parser.error('repetitions must be from 3 to 30')
    print(json.dumps(run(args.baseline,args.repetitions),indent=2))
