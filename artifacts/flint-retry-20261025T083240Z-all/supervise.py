import datetime, hashlib, json, os, pathlib, re, shutil, signal, subprocess, sys, time
repo = pathlib.Path('/Users/tijs/projects/local-model-bench-flint-gate-20261022')
stage = sys.argv[1] if len(sys.argv)>1 else 'all'
root = repo/'artifacts'/('flint-retry-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+stage)
root.mkdir()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def command(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=15)
    return p.stdout.strip()
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def sample():
    pressure=command(['memory_pressure','-Q'])
    swap=command(['sysctl','vm.swapusage'])
    return dict(time=now(), free_percent=int(re.search(r'free percentage: (\d+)',pressure)[1]), pressure_level=int(command(['sysctl','-n','kern.memorystatus_vm_pressure_level'])), swap_used_mib=float(re.search(r'used = ([\d.]+)M',swap)[1]), disk_free_bytes=shutil.disk_usage(repo).free)
def record(name,data): (root/name).write_text(json.dumps(data,indent=2)+'\n')
print('Evidence:',root,flush=True)
config=repo/'configs/Flint-mixed-3-4bit-full-20261024/mei.yaml'
assert sha(config).startswith('c754cda7b797')
assert command(['git','-C',str(repo),'status','--porcelain','--',str(config)])==''
assert command(['git','-C','/Users/tijs/projects/mei-flint-20261023','rev-parse','HEAD'])=='c9b6013958cbc838b156b717f3b49a0045f84064'
assert command(['git','-C','/Users/tijs/projects/mei-flint-20261023','status','--porcelain'])==''
binary=pathlib.Path('/Users/tijs/.local/share/local-model-bench/mei-build-flint-full-20261024/release/mei')
assert sha(binary)=='c6dea15433512b9c488eab026858946a1d9d3347055848c4faeefd1086ee54bd'
assert command(['git','-C','/Users/tijs/.local/share/local-model-bench/mei-build-flint-full-20261024/checkouts/vmlx-swift','rev-parse','HEAD'])=='633fe166630ef04310aea7d5a1795555ab32970d'
manifest=json.loads((repo/'artifacts/flint-mei-gate-20261024/staging/staging-verification-20261024.json').read_text())
verified=[]
for row in manifest['files']:
    path=pathlib.Path(manifest['target'])/row['path']
    digest=sha(path)
    assert digest==row['sha256'] and path.stat().st_size==row['bytes'],str(path)
    verified.append(dict(path=row['path'],bytes=path.stat().st_size,sha256=digest))
record('model-hashes.json',verified)
print('Pinned model hashes: 16/16 matched',flush=True)
preflight=[]
for i in range(3):
    s=sample(); preflight.append(s); print('Preflight:',json.dumps(s),flush=True)
    assert s['free_percent']>=70 and s['pressure_level']==1 and s['disk_free_bytes']>=10*1024**3
    assert s['swap_used_mib']<=preflight[0]['swap_used_mib']+128
    assert not command(['lsof','-nP','-iTCP:8024','-iTCP:8017','-sTCP:LISTEN'])
    if i<2: time.sleep(15)
log=repo/'results/log.jsonl'
meta=dict(time=now(),stage=stage,runner_sha=command(['git','-C',str(repo),'rev-parse','HEAD']),config_sha256=sha(config),results_initial_bytes=log.stat().st_size,results_initial_sha256=sha(log),preflight=preflight,stop_policy={'sustained_free_percent':10,'consecutive_samples':2,'swap_mib':16384,'critical_pressure_level':4,'disk_floor_bytes':10*1024**3})
shutil.copyfile(config,root/'config.yaml')
record('preflight.json',meta)
env=os.environ.copy(); env['MEI_RUNTIME_BASE']='/Users/tijs/.local/share/local-model-bench/mei-runtime/flint-full-20261024'; env['PYTHONUNBUFFERED']='1'
argv=['uv','run','--locked','python','runner/run_bench.py','--config',str(config.relative_to(repo)),'--stage',stage]
record('invocation.json',dict(argv=argv,cwd=str(repo),environment_overrides={'MEI_RUNTIME_BASE':env['MEI_RUNTIME_BASE'],'PYTHONUNBUFFERED':'1'}))
with (root/'runner.log').open('w') as out, (root/'resources.jsonl').open('a',buffering=1) as telemetry:
    proc=subprocess.Popen(argv,cwd=repo,env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
    record('process.json',dict(supervisor_pid=os.getpid(),runner_pid=proc.pid,pgid=proc.pid))
    print('Started runner',proc.pid,flush=True)
    low=0; reason=None; n=0
    while proc.poll() is None:
        try:
            s=sample(); telemetry.write(json.dumps(s)+'\n'); low=low+1 if s['free_percent']<=10 else 0
            if n%3==0: print('Resource:',json.dumps(s),flush=True)
            n+=1
            if s['pressure_level']>=4: reason='critical kernel memory pressure'
            elif low>=2: reason='sustained memory free <=10%'
            elif s['swap_used_mib']>=16384: reason='swap use reached 16 GiB'
            elif s['disk_free_bytes']<10*1024**3: reason='disk below 10 GiB'
        except Exception as e: reason='resource monitor failure: '+str(e)
        if reason:
            print('SAFETY STOP:',reason,flush=True)
            os.killpg(proc.pid,signal.SIGTERM)
            try: proc.wait(timeout=15)
            except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL); proc.wait()
            subprocess.run(['bash','runner/stop_mei_server.sh','--runtime-base',env['MEI_RUNTIME_BASE']],cwd=repo,env=env,timeout=45)
            break
        time.sleep(10)
    rc=proc.wait()
# Reap descendants even if runner returned abnormally and check isolated server cleanup.
subprocess.run(['bash','runner/stop_mei_server.sh','--runtime-base',env['MEI_RUNTIME_BASE']],cwd=repo,env=env,timeout=45)
record('outcome.json',dict(time=now(),runner_returncode=rc,safety_stop=reason,final_resources=sample(),results_final_bytes=log.stat().st_size))
print('Finished:',rc,'safety_stop=',reason,'evidence=',root,flush=True)
