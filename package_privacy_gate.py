#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, stat, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'artifact'/'results'/'package-privacy-gate.json'
forbidden=['$WORK_ROOT','$HOME','BEGIN OPENSSH PRIVATE KEY','BEGIN RSA PRIVATE KEY']
text_ext={'.txt','.md','.json','.jsonl','.csv','.tsv','.tex','.bib','.py','.sh','.log','.rst','.yml','.yaml','.toml','.ini','.sty','.cfg','.out'}
hits=[]; symlinks=[]; caches=[]; nested=[]
for p in ROOT.rglob('*'):
    rel=str(p.relative_to(ROOT))
    if p.is_symlink(): symlinks.append(rel); continue
    if '__pycache__' in p.parts or p.suffix in {'.pyc','.pyo'}: caches.append(rel)
    if p.is_file() and p.suffix.lower() in {'.zip','.tar','.gz','.tgz','.7z'} and not rel.startswith('artifact/inputs/'):
        nested.append(rel)
    if p.is_file() and p.suffix.lower() in text_ext:
        try:s=p.read_text(errors='strict')
        except Exception:continue
        for needle in forbidden:
            if needle in s:hits.append({'file':rel,'needle':needle})
report={'hits':hits,'symlinks':symlinks,'cache_files':caches,'nested_archives':nested}
report['pass']=not hits and not symlinks and not caches and not nested
OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(0 if report['pass'] else 1)
