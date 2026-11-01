"""Retrieve official sources with pinned checksums; source drift fails closed."""
from pathlib import Path
import hashlib,json,urllib.request,os

def sha256(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()

def fetch_sources(root):
 manifest=[]
 for item in json.loads((root/'docs/source_lock.json').read_text()):
  p=root/'data/raw'/item['file'];p.parent.mkdir(parents=True,exist_ok=True)
  if not p.exists():
   tmp=p.with_suffix(p.suffix+'.part')
   try:
    req=urllib.request.Request(item['url'],headers={'User-Agent':'Official-source-research-portfolio/2.0'})
    with urllib.request.urlopen(req,timeout=120) as res, tmp.open('wb') as f:
     while block:=res.read(1048576):f.write(block)
    if sha256(tmp)!=item['sha256']:raise ValueError('Official source changed; review and update source lock: '+item['file'])
    os.replace(tmp,p)
   finally:tmp.unlink(missing_ok=True)
  observed=sha256(p)
  if observed!=item['sha256']:raise ValueError('Checksum mismatch: '+item['file'])
  manifest.append({**item,'sha256_verified':True,'observed_bytes':p.stat().st_size})
 (root/'evidence/source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 return {row['file']:root/'data/raw'/row['file'] for row in manifest}
