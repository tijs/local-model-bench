import ctypes, fcntl, hashlib, json, os, tempfile
from pathlib import Path
lib=ctypes.CDLL(None,use_errno=True)
lib.mmap.restype=ctypes.c_void_p
lib.mmap.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_longlong]
lib.msync.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int]
lib.mincore.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p]
lib.munmap.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
def pages(p,invalidate=False):
    with p.open('rb') as f:
        n=os.fstat(f.fileno()).st_size
        addr=lib.mmap(None,n,1,1,f.fileno(),0)
        if addr==ctypes.c_void_p(-1).value: raise OSError(ctypes.get_errno())
        try:
            if invalidate and lib.msync(addr,n,2): raise OSError(ctypes.get_errno())
            v=(ctypes.c_ubyte*((n+16383)//16384))()
            if lib.mincore(addr,n,v): raise OSError(ctypes.get_errno())
            return sum(x&1 for x in v)
        finally: lib.munmap(addr,n)
with tempfile.TemporaryDirectory() as d:
    p=Path(d)/'fixture'
    with p.open('wb') as f:
        for i in range(64): f.write(bytes(range(256))*4096)
        f.flush();os.fsync(f.fileno())
    stat=p.stat()
    with p.open('rb') as f: expected=hashlib.file_digest(f,'sha256').hexdigest()
    rows=[{'step':'regular_hash','resident_pages':pages(p)}]
    rows.append({'step':'invalidate_clean_readonly','resident_pages':pages(p,True)})
    with p.open('rb',buffering=0) as f:
        fcntl.fcntl(f.fileno(),48,1)
        actual=hashlib.file_digest(f,'sha256').hexdigest()
    rows.append({'step':'uncached_hash','resident_pages':pages(p)})
    result={'rows':rows,'sha256_same':actual==expected,'mtime_same':p.stat().st_mtime_ns==stat.st_mtime_ns,'ctime_same':p.stat().st_ctime_ns==stat.st_ctime_ns,'scope':'Disposable 64 MiB fsynced fixture, no canonical model files'}
    Path('/tmp/mei011-uncached-verify-probe-20261106.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
