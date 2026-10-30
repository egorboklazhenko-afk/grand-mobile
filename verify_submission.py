"""Reproducible local acceptance: unit tests, HTTP/CLI, citations, synthetic triage.
No external LLM requests are made. Official competition data stays local.
"""
import concurrent.futures
import importlib.util
import json
import math
import os
import re
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent

def main():
    os.chdir(ROOT)
    # Never accidentally bill a provider during acceptance verification.
    env=dict(os.environ)
    for key in ['COPILOT_PROVIDER','OLLAMA_MODEL','GROQ_API_KEY']:env.pop(key,None)
    test=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],env=env,capture_output=True,text=True)
    if test.returncode:raise RuntimeError(test.stderr)
    from copilot.engine import Engine
    for key in ['COPILOT_PROVIDER','OLLAMA_MODEL','GROQ_API_KEY']:os.environ.pop(key,None)
    engine=Engine('data/rules.json')
    # Import the hand-authored matrix without invoking any tests a second time.
    sys.path.insert(0,str(ROOT/'tests'))
    import test_submission
    pairs=[];language_correct=0
    for kind,text,expected,priority,lang in test_submission.CASES:
        r=engine.triage({'kind':kind,'messages':[{'role':'player','text':text}]})
        pairs.append((expected,r['category'],priority,r['priority']))
        language_correct+=r['lang']==lang
    labels={p[2] for p in pairs}|{p[3] for p in pairs}
    f1=[]
    for label in labels:
        tp=sum(a==b==label for _,_,a,b in pairs);fp=sum(a!=label and b==label for _,_,a,b in pairs);fn=sum(a==label and b!=label for _,_,a,b in pairs)
        f1.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    child=subprocess.Popen([sys.executable,'-m','copilot.server','--port',str(port)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    base=f'http://127.0.0.1:{port}'
    def post(path,payload,origin=None):
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        req=urllib.request.Request(base+path,data=json.dumps(payload).encode(),headers=headers)
        start=time.perf_counter()
        with urllib.request.urlopen(req,timeout=5) as response:result=json.load(response)
        return result,(time.perf_counter()-start)*1000
    try:
        deadline=time.monotonic()+8
        while True:
            try:
                with urllib.request.urlopen(base+'/health',timeout=.3) as r:assert json.load(r)['status']=='ok'
                break
            except OSError:
                if time.monotonic()>deadline:raise
                time.sleep(.1)
        ticket={'kind':'complaint','messages':[{'role':'player','text':'Demo_Player оскорбил меня на сервере 17','attachments':2}]}
        required={'lang','category','priority','is_spam_or_duplicate','extracted','draft_reply','needs_human','confidence','reasons'}
        reply,_=post('/triage',ticket)
        assert required<=reply.keys()
        assert reply['category']=='complaint.insult' and reply['draft_reply']['cited']==['2.1']
        assert reply['extracted']['server']=='17' and reply['extracted']['has_evidence']
        assert reply['needs_human'] and not reply['audit']['attachments']['inspected']
        for payload,status in [([],400),({'kind':'invalid'},400)]:
            try:post('/triage',payload);raise AssertionError('invalid body accepted')
            except urllib.error.HTTPError as exc:assert exc.code==status
        try:post('/triage',ticket,'https://foreign.example');raise AssertionError('foreign origin accepted')
        except urllib.error.HTTPError as exc:assert exc.code==403
        feedback,_=post('/feedback',{'action':'edit','edited_text':'Синтетическая проверка сохранения'})
        assert feedback['saved'] and not feedback['delivered_to_player']
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            timings=list(pool.map(lambda _:post('/triage',ticket)[1],range(80)))
        http_p95=sorted(timings)[math.ceil(.95*len(timings))-1]
        assert http_p95<5000
    finally:child.terminate();child.wait(timeout=5)
    output=ROOT/'runtime'/'acceptance-predictions.jsonl'
    subprocess.run([sys.executable,'-m','copilot.cli','--input','examples/demo.jsonl','--output',str(output)],env=env,check=True)
    actual=[json.loads(s) for s in output.read_text(encoding='utf-8').splitlines()]
    assert len(actual)==10 and actual[5]['audit']['duplicate']
    points={p['id']:p for p in engine.index.points if p.get('citation_type')!='section'}
    checked=0
    with open('data/tickets_valid.jsonl',encoding='utf-8') as f:
        for line in f:
            r=engine.triage(json.loads(line));checked+=1
            assert all(s['id'] in points for s in r['audit']['rule_sources'])
    report={'unit_tests':int(re.search(r'Ran (\d+) tests',test.stderr).group(1)),'unit_test_status':'passed','http_contract':'passed','http_invalid_input':'passed',
        'http_cross_origin_write_block':'passed','feedback_persistence':'passed','cli_output_count':len(actual),
        'cli_duplicate_scenario':'passed','real_validation_citation_check_tickets':checked,
        'all_citations_are_real_numbered_points':True,'http_requests':80,'http_concurrency':4,'offline_http_p95_ms':round(http_p95,3),
        'synthetic_cases':len(pairs),'synthetic_category_accuracy':sum(a==b for a,b,_,_ in pairs)/len(pairs),
        'synthetic_priority_macro_f1':sum(f1)/len(f1),'synthetic_language_accuracy':language_correct/len(pairs),
        'synthetic_benchmark_note':'Hand-authored regression scenarios, not an independent or hidden competition evaluation.',
        'groq_connection':'User reports successful operation; external API re-test intentionally skipped.',
        'llm_quality_and_latency':'Not measured by this verification script.'}
    Path('reports/acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
