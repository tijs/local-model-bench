import pathlib,json,urllib.request,hashlib,shutil,concurrent.futures,datetime
root=pathlib.Path('/Users/tijs/.local/share/local-model-bench/mei-models/Flint-40B-A2.5B-JANGH2')
meta=json.loads(pathlib.Path('/Users/tijs/projects/local-model-bench-flint-gate-20261022/artifacts/flint-jangh2-contract-20261025/metadata.json').read_text())
assert meta['sha']=='8bfb25587388c6a235e58338a6c926da000bded9'
assert shutil.disk_usage(root.parent).free>sum(x['size'] for x in meta['siblings'])+10*1024**3
root.mkdir(exist_ok=False)
def get(row):
 name=row['rfilename'];assert pathlib.Path(name).name==name
 url='https://huggingface.co/'+meta['id']+'/resolve/'+meta['sha']+'/'+name
 temp=root/(name+'.incomplete');h=hashlib.sha256();size=0
 with urllib.request.urlopen(url,timeout=90) as r,temp.open('xb') as f:
  while chunk:=r.read(4*1024*1024):
   assert shutil.disk_usage(root).free>10*1024**3
   f.write(chunk);h.update(chunk);size+=len(chunk)
 assert size==row['size'],(name,size,row['size'])
 if row.get('lfs'):assert h.hexdigest()==row['lfs']['sha256']
 else:
  blob=hashlib.sha1(b'blob '+str(size).encode()+b'\0'+temp.read_bytes()).hexdigest();assert blob==row['blobId']
 temp.rename(root/name)
 print('Verified',name,size,flush=True)
 return {'path':name,'bytes':size,'sha256':h.hexdigest()}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:files=list(pool.map(get,meta['siblings']))
manifest={'repo':meta['id'],'revision':meta['sha'],'staged_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'all_sizes_and_remote_digests_match':True}
path=root.parent/(root.name+'.provenance.json');path.write_text(json.dumps(manifest,indent=2)+'\n');print('COMPLETE',path,flush=True)
