#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifact'; OUT=ART/'results'/'release-sanitization.json'
repls={str(ROOT):'$PROJECT_ROOT','$WORK_ROOT':'$WORK_ROOT','$HOME':'$HOME'}
text_ext={'.txt','.md','.json','.jsonl','.csv','.tsv','.tex','.bib','.py','.sh','.log','.rst','.yml','.yaml','.toml','.ini','.sty','.cfg','.out'}
changed=[]; scanned=0
for p in ROOT.rglob('*'):
    if p.is_dir() and p.name=='__pycache__': shutil.rmtree(p,ignore_errors=True); continue
    if not p.is_file() or p.suffix.lower() not in text_ext: continue
    try: s=p.read_text(errors='strict')
    except Exception: continue
    scanned+=1; t=s
    for a,b in repls.items(): t=t.replace(a,b)
    t=re.sub(r'/mnt/data/[A-Za-z0-9_.\-/]+',lambda m: '$MNT_DATA/'+m.group(0).split('/')[-1] if 'reviewer-final-work' in m.group(0) else m.group(0),t)
    if t!=s:
        p.write_text(t); changed.append(str(p.relative_to(ROOT)))
report={'scanned_text_files':scanned,'changed_files':changed,'changed_count':len(changed)}
# Re-scan for forbidden build-host paths.
hits=[]
for p in ROOT.rglob('*'):
    if not p.is_file() or p.suffix.lower() not in text_ext: continue
    try: s=p.read_text(errors='strict')
    except Exception: continue
    for needle in ['$WORK_ROOT','$HOME']:
        if needle in s: hits.append({'file':str(p.relative_to(ROOT)),'needle':needle})
report['forbidden_hits']=hits; report['pass']=not hits
OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(0 if report['pass'] else 1)
