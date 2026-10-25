"""Additional serialized exact-pack native admission probes; no benchmark grading."""
import sys,json,time,pathlib,argparse
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'runner'))
from probe_mei import request_json,exact_prompt
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['behavior','context','cacheoff','repeat','capped'],required=True);a=p.parse_args()
root=pathlib.Path(__file__).parent;base='http://127.0.0.1:8024/v1';model='OsaurusAI/Flint-40B-A2.5B-JANGH2'
results={};dest=root/('extended-'+a.phase+'.json')
def run(name,payload,validate=lambda r:None):
 r=None
 try:
  r,t=request_json(base+'/chat/completions' if 'messages' in payload else base+'/completions',dict(model=model,temperature=0,stream=False,**payload),timeout=1800)
  validate(r);results[name]={'status':'passed','seconds':t,'response':r};print(name,'passed',round(t,2),flush=True)
 except Exception as e:results[name]={'status':'failed','error':str(e),'response':r};print(name,'FAILED',str(e)[:200],flush=True)
 dest.write_text(json.dumps(results,indent=2)+'\n');return results[name].get('response')
def answer(r):
 m=r['choices'][0]['message'];assert m.get('content','').strip(),m
 assert r['choices'][0]['finish_reason']=='stop',r['choices'][0]
 assert not any(s in m.get('content','') for s in ['<think>','</think>','<tool_call>','<|']),m
 return m['content']
if a.phase=='behavior':
 short=json.load(open(root/'probe-short.json'));raw=short['probes']['tool_nonstreaming']['raw_response'];assistant=raw['choices'][0]['message'];call=assistant['tool_calls'][0]
 msgs=[{'role':'system','content':'You are a helpful assistant with access to one tool.'},{'role':'user','content':'What is 15 + 27? You must use add_numbers to compute it.'},assistant,{'role':'tool','tool_call_id':call['id'],'content':'42'}]
 r=run('tool_result_continuation',{'messages':msgs,'max_tokens':1024},lambda r: (answer(r), (_ for _ in ()).throw(AssertionError('missing 42')) if '42' not in answer(r) else None))
 prefix='You are concise. '+('Stable cache prefix. '*160)
 for name,word in [('diverge_a','ORANGE'),('diverge_b','PURPLE'),('diverge_a_repeat','ORANGE')]:
  run(name,{'messages':[{'role':'system','content':prefix},{'role':'user','content':'Reply with exactly: '+word}],'max_tokens':1024},lambda r,w=word: (answer(r), (_ for _ in ()).throw(AssertionError('wrong answer')) if w not in answer(r) else None))
 run('cache_on_comparison',{'messages':[{'role':'user','content':'Reply with exactly: cache-parity'}],'max_tokens':1024},answer)
elif a.phase in ('repeat','capped'):
 prefix='You are concise. '+('Stable cache prefix. '*160)
 for name,word in [('warm_a','ORANGE'),('warm_b','PURPLE'),('warm_a_repeat','ORANGE')]:
  def validate(r,w=word):
   assert answer(r)==w,answer(r)
  run(name,{'messages':[{'role':'system','content':prefix},{'role':'user','content':'Reply with exactly: '+word}],'max_tokens':1024},validate)
elif a.phase=='cacheoff':
 original=json.load(open(root/'extended-behavior.json'))['cache_on_comparison']['response']
 def compare(r):
  assert answer(r)==answer(original),(r,original)
  assert r['usage']['completion_tokens']==original['usage']['completion_tokens']
  assert (r['usage'].get('prompt_tokens_details') or {}).get('cached_tokens',0)==0
 run('cache_off_comparison',{'messages':[{'role':'user','content':'Reply with exactly: cache-parity'}],'max_tokens':1024},compare)
 prefix='You are concise. '+('Stable cache prefix. '*160)
 for name,word in [('cold_a','ORANGE'),('cold_b','PURPLE'),('cold_a_repeat','ORANGE')]:
  def validate(r,w=word):
   assert answer(r)==w,answer(r)
   assert (r['usage'].get('prompt_tokens_details') or {}).get('cached_tokens',0)==0
  run(name,{'messages':[{'role':'system','content':prefix},{'role':'user','content':'Reply with exactly: '+word}],'max_tokens':1024},validate)

else:
 tokenizer=pathlib.Path('/Users/tijs/.local/share/local-model-bench/mei-models/Flint-40B-A2.5B-JANGH2')
 def validate(r,n):
  assert r['usage']['prompt_tokens']==n,r
  assert r['usage']['completion_tokens']==1,r
 for n in [65535,65536]:
  run('context_'+str(n),{'prompt':exact_prompt(tokenizer,n),'max_tokens':1},lambda r,n=n:validate(r,n))
 try:
  r,t=request_json(base+'/completions',dict(model=model,prompt=exact_prompt(tokenizer,65537),max_tokens=1,temperature=0),timeout=30)
  results['context_overflow']={'status':'failed','response':r}
 except RuntimeError as e:results['context_overflow']={'status':'passed' if 'HTTP 400' in str(e) else 'failed','error':str(e)}
 dest.write_text(json.dumps(results,indent=2)+'\n')
status,_=request_json(base+'/mei/status');(root/('status-'+a.phase+'.json')).write_text(json.dumps(status,indent=2)+'\n')
sys.exit(0 if all(v['status']=='passed' for v in results.values()) else 1)
