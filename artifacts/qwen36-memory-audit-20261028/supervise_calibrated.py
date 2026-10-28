from memory_gate import MIN_FREE_PERCENT, resource_gate_reason
import sys,pathlib,json,subprocess,time,os,signal,datetime,re,shutil,ctypes,struct
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True);limit=int(sys.argv[2]);assert sys.argv[3]=='--';argv=sys.argv[4:]
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def cmd(args):return subprocess.run(args,capture_output=True,text=True,timeout=10).stdout
lib=ctypes.CDLL('/usr/lib/libproc.dylib')
def sample(pid):
 pressure_text=cmd(['memory_pressure','-Q']);s=cmd(['sysctl','vm.swapusage']);buf=ctypes.create_string_buffer(4096)
 ok=lib.proc_pid_rusage(pid,0,ctypes.byref(buf))==0
 tree=[]
 rows=[]
 for line in cmd(['ps','-axo','pid=,ppid=,comm=']).splitlines():
  fields=line.strip().split(None,2)
  if len(fields)==3:rows.append((int(fields[0]),int(fields[1]),fields[2]))
 owned={pid}
 for _ in range(10):
  new=owned|{p for p,parent,_ in rows if parent in owned}
  if new==owned:break
  owned=new
 for p,_,name in rows:
  if p in owned:
   usage=ctypes.create_string_buffer(4096)
   if lib.proc_pid_rusage(p,0,ctypes.byref(usage))==0:tree.append({'pid':p,'comm':name,'phys_footprint_bytes':struct.unpack_from('Q',usage,72)[0],'resident_bytes':struct.unpack_from('Q',usage,64)[0]})
 return {'time':now(),'free_percent':int(re.search(r'free percentage: (\d+)',pressure_text)[1]),'kernel_pressure_level':int(cmd(['sysctl','-n','kern.memorystatus_vm_pressure_level'])),'swap_used_mib':float(re.search(r'used = ([\d.]+)',s)[1]),'disk_free_bytes':shutil.disk_usage(out).free,'owned_processes':tree,'phys_footprint_bytes':struct.unpack_from('Q',buf,72)[0] if ok else None,'resident_bytes':struct.unpack_from('Q',buf,64)[0] if ok else None}
initial=sample(os.getpid());assert initial['free_percent']>=70 and initial['kernel_pressure_level']==1 and initial['disk_free_bytes']>10*1024**3,initial
(out/'invocation.json').write_text(json.dumps({'argv':argv,'cwd':os.getcwd(),'initial':initial,'deadline_seconds':limit,'resource_policy':{'min_free_percent':MIN_FREE_PERCENT,'kernel_warning_samples':2,'critical_pressure_immediate':True,'swap_growth_mib':2048,'swap_absolute_mib':16384}},indent=2))
with (out/'child.log').open('w') as log,(out/'resources.jsonl').open('a',buffering=1) as telemetry:
 proc=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 (out/'process.json').write_text(json.dumps({'pid':proc.pid,'supervisor_pid':os.getpid(),'pgid':proc.pid,'started':now()}))
 print('START',proc.pid,flush=True);deadline=time.monotonic()+limit;low=0;warning=0;reason=None;i=0
 try:
  while proc.poll() is None:
   s=sample(proc.pid);telemetry.write(json.dumps(s)+'\n');low=low+1 if s['free_percent']<=MIN_FREE_PERCENT else 0;warning=warning+1 if s['kernel_pressure_level']>=2 else 0
   if i%6==0:print(json.dumps(s),flush=True)
   i+=1
   reason=resource_gate_reason(s,initial,low,warning)
   if reason:pass
   elif time.monotonic()>deadline:reason='deadline'
   elif (out/'stop.request').exists():reason='requested normal teardown'
   if reason:break
   time.sleep(5)
 finally:
  if proc.poll() is None:
   os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=15)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
  (out/'outcome.json').write_text(json.dumps({'time':now(),'returncode':proc.returncode,'stop_reason':reason},indent=2))
 print('DONE',proc.returncode,reason,flush=True)
