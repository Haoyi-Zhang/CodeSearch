#!/usr/bin/env python3
"""Compute reviewer-facing traffic metrics from frozen raw result records.

This analyzer deliberately separates source-facing RPC bytes from the
coordinator-to-client application payload.  It never substitutes logical state
bytes for wire bytes.  The payload metric is the exact length of canonical
UTF-8 JSON for the fields returned to the client, excluding oracle/debug and
measurement fields.  The script records its extraction rule and coverage.
"""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import csv, json, math, statistics, hashlib, re, gzip

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
RESULTS=ROOT/'results'
OUT=RESULTS/'reviewer-metrics.json'
CSV=RESULTS/'reviewer-metrics.csv'

POLICY_KEYS=('policy','strategy','mode','baseline','method')
ID_KEYS=('trace_id','scenario','seed','tick','query_id','query','plan_id','request_id','sequence')
CLIENT_KEYS={
 'status','complete','claimed_complete','justified_complete','partial','reason','failure','error',
 'target','target_cut','cut','rows','results','answer','answers','items','topk','top_k','certificate',
 'returned','returned_rows','response_rows','result_rows','hits','docs','claim','certified','completeness',
 'receipt','receipts','token','proof','blocking_shards','blocked_shards','missing_shards','epoch'
}
DROP_RE=re.compile(r'(?:oracle|exact|valid|sound|latency|elapsed|duration|cpu|rss|debug|trace|source_?bytes|rpc_?bytes|message|logical_?state|instrument|timing)',re.I)


def load_any(p:Path):
    if p.name.endswith('.json.gz'):
        return json.loads(gzip.open(p,'rt').read())
    if p.name.endswith(('.jsonl.gz','.ndjson.gz')):
        out=[]
        for n,line in enumerate(gzip.open(p,'rt'),1):
            if line.strip(): out.append(json.loads(line))
        return out
    if p.suffix=='.json':
        return json.loads(p.read_text())
    if p.suffix in {'.jsonl','.ndjson'}:
        out=[]
        for n,line in enumerate(p.read_text().splitlines(),1):
            if line.strip():
                try: out.append(json.loads(line))
                except Exception as e: raise ValueError(f'{p}:{n}: {e}')
        return out
    return None

def walk(v,path=()):
    if isinstance(v,dict):
        yield path,v
        for k,z in v.items(): yield from walk(z,path+(str(k),))
    elif isinstance(v,list):
        for i,z in enumerate(v): yield from walk(z,path+(str(i),))

def policy_of(d:dict, path):
    for k in POLICY_KEYS:
        v=d.get(k)
        if isinstance(v,str) and 1<=len(v)<=80: return v
    # policy may be encoded as a parent key
    for x in reversed(path):
        if re.search(r'continu|certificate|overlay|delta|mirror|snapshot|cache|stale|unverified|prefix|repair',x,re.I): return x
    return None

def looks_query(d:dict):
    ks={str(k).lower() for k in d}
    return bool(ks & {k.lower() for k in CLIENT_KEYS}) and bool(ks & {'query','query_id','plan_id','tick','rows','results','answer','answers','status','complete','claimed_complete','returned','returned_rows','hits','docs','certified','claim'})

def normalize(v):
    if isinstance(v,dict): return {str(k):normalize(v[k]) for k in sorted(v,key=lambda x:str(x))}
    if isinstance(v,list): return [normalize(x) for x in v]
    if isinstance(v,tuple): return [normalize(x) for x in v]
    if isinstance(v,set): return sorted(normalize(x) for x in v)
    if isinstance(v,(str,int,float,bool)) or v is None: return v
    return repr(v)

def client_payload(d:dict):
    payload={}
    for k,v in d.items():
        kl=str(k).lower()
        if kl in CLIENT_KEYS or (not DROP_RE.search(kl) and kl in {'qid','request','response'}):
            payload[str(k)]=normalize(v)
    # Some traces wrap the result.
    for k in ('response','result','output'):
        if k in d and isinstance(d[k],dict):
            payload[k]={str(a):normalize(b) for a,b in d[k].items() if str(a).lower() in CLIENT_KEYS or not DROP_RE.search(str(a))}
    if not payload:
        payload={str(k):normalize(v) for k,v in d.items() if not DROP_RE.search(str(k)) and str(k).lower() not in {x.lower() for x in POLICY_KEYS+ID_KEYS}}
    if not payload: return None
    blob=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    return len(blob),payload

def identity(d:dict, policy:str, path, file_rel):
    vals=[]
    for k in ID_KEYS:
        if k in d and isinstance(d[k],(str,int,float,bool)): vals.append((k,d[k]))
    return (file_rel,policy,tuple(vals),tuple(path[-3:]))

records=[]
files=[]
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or p.name in {OUT.name,CSV.name}: continue
    if not (p.suffix in {'.json','.jsonl','.ndjson'} or p.name.endswith(('.json.gz','.jsonl.gz','.ndjson.gz'))): continue
    try: obj=load_any(p)
    except Exception: continue
    if obj is None: continue
    frel=str(p.relative_to(ROOT))
    file_count=0
    for path,d in walk(obj):
        if not looks_query(d): continue
        pol=policy_of(d,path)
        if not pol: continue
        cp=client_payload(d)
        if not cp: continue
        n,payload=cp
        source=None
        for k,v in d.items():
            if isinstance(v,(int,float)) and re.fullmatch(r'(?:mean_)?(?:source|rpc)(?:_|-)?bytes(?:_per_query)?',str(k),re.I): source=float(v)
        records.append({'file':frel,'path':'/'.join(path),'policy':pol,'client_bytes':n,'source_bytes':source,'id':identity(d,pol,path,frel),'payload_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()})
        file_count+=1
    if file_count: files.append({'file':frel,'records':file_count})

# Deduplicate exact repeated serialization of the same record location/id.
seen=set(); dedup=[]
for r in records:
    key=(r['id'],r['payload_sha256'])
    if key in seen: continue
    seen.add(key); dedup.append(r)
records=dedup

def canon_policy(p):
    s=re.sub(r'[^a-z0-9]+','_',p.lower()).strip('_')
    aliases=[
      ('continu','continuation_certificate'),('delta','exact_delta_overlay'),('overlay','exact_delta_overlay'),
      ('cut','cut_aware_cache'),('mirror','full_coordinator_mirror'),('stale','unsafe_stale'),
      ('prefix','prefix_repair')]
    for a,b in aliases:
        if a in s:return b
    return s
for r in records:r['policy']=canon_policy(r['policy'])

def family_of(path):
    s=str(path).lower()
    if 'real' in s or 'history' in s: return 'real_history'
    if 'continu' in s or 'primary' in s or 'main' in s: return 'continuation_main'
    if 'cold' in s or 'oneshot' in s or 'one-shot' in s or 'prefix' in s: return 'cold_query'
    return 'unclassified'
for r in records:r['family']=family_of(r['file'])

by=defaultdict(list)
for r in records: by[r['policy']].append(r['client_bytes'])
by_family=defaultdict(list)
for r in records: by_family[(r['family'],r['policy'])].append(r['client_bytes'])
summary={}
for pol,vals in sorted(by.items()):
    vals=sorted(vals)
    def q(frac): return vals[min(len(vals)-1,max(0,math.ceil(frac*len(vals))-1))]
    summary[pol]={'records':len(vals),'mean_client_payload_bytes':statistics.fmean(vals),'median_client_payload_bytes':statistics.median(vals),'p95_client_payload_bytes':q(.95),'min_client_payload_bytes':vals[0],'max_client_payload_bytes':vals[-1]}
family_summary={}
for (fam,pol),vals0 in sorted(by_family.items()):
    vals=sorted(vals0)
    def qf(frac): return vals[min(len(vals)-1,max(0,math.ceil(frac*len(vals))-1))]
    family_summary.setdefault(fam,{})[pol]={'records':len(vals),'mean_client_payload_bytes':statistics.fmean(vals),'median_client_payload_bytes':statistics.median(vals),'p95_client_payload_bytes':qf(.95),'min_client_payload_bytes':vals[0],'max_client_payload_bytes':vals[-1]}

# Locate policy summaries and merge source/state/query metrics without guessing.
summary_candidates=[]
for p in sorted(RESULTS.rglob('*.json')):
    if p.name==OUT.name: continue
    try:o=json.loads(p.read_text())
    except:continue
    if isinstance(o,dict) and isinstance(o.get('policies'),dict): summary_candidates.append((p,o))
merged=[]
for p,o in summary_candidates:
    for raw,m in o['policies'].items():
        if not isinstance(m,dict):continue
        pol=canon_policy(raw)
        fam=family_of(str(p.relative_to(ROOT)))
        row={'summary_file':str(p.relative_to(ROOT)),'family':fam,'policy':pol}
        for k,v in m.items():
            if isinstance(v,(int,float)) and ('byte' in k.lower() or 'message' in k.lower() or 'state' in k.lower() or 'quer' in k.lower()): row[k]=v
        payload_metrics=family_summary.get(fam,{}).get(pol) or summary.get(pol)
        if payload_metrics: row.update(payload_metrics)
        # Compute the transparent combined metric only when source mean exists.
        src=None
        for k,v in row.items():
            if isinstance(v,(int,float)) and re.fullmatch(r'mean_(?:source|rpc)_bytes(?:_per_query)?',k,re.I):src=float(v)
        if src is None:
            for k,v in row.items():
                if isinstance(v,(int,float)) and 'source' in k.lower() and 'byte' in k.lower() and 'mean' in k.lower():src=float(v)
        if src is not None and payload_metrics:
            row['mean_end_to_end_application_bytes']=src+payload_metrics['mean_client_payload_bytes']
        merged.append(row)

out={
 'schema_version':1,
 'definition':{
   'source_facing_bytes':'application-layer request plus response bytes recorded by the source RPC instrumentation',
   'client_payload_bytes':'exact UTF-8 byte length of canonical compact JSON containing client-visible result/status/certificate fields found in frozen raw records; oracle, debug, timing, and measurement fields are excluded',
   'end_to_end_application_bytes':'source-facing bytes plus coordinator-to-client canonical payload bytes; excludes TCP/IP/TLS headers and one-time process startup',
   'state_bytes':'reported separately; never added to traffic'
 },
 'coverage':{'raw_records':len(records),'files':files,'policies':summary,'families':family_summary},
 'merged_policy_rows':merged,
 'warnings':[]
}
if not records: out['warnings'].append('No client-visible raw records were extracted; no end-to-end claim is permitted.')
OUT.write_text(json.dumps(out,indent=2,sort_keys=True))
keys=sorted({k for r in merged for k in r})
with CSV.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(merged)
print(json.dumps({'out':str(OUT),'records':len(records),'policies':{k:v['records'] for k,v in summary.items()},'merged_rows':len(merged)},sort_keys=True))
