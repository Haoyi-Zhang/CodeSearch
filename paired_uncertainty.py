#!/usr/bin/env python3
"""Descriptive paired uncertainty for frozen traces; no iid significance claim."""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import csv,json,random,statistics,re,math
ROOT=Path(__file__).resolve().parent; RES=ROOT/'results'
OUT=RES/'paired-trace-uncertainty.json'; CSVOUT=RES/'paired-trace-uncertainty.csv'

def canon(s):
 s=re.sub(r'[^a-z0-9]+','_',str(s).lower()).strip('_')
 for a,b in [('continu','continuation_certificate'),('overlay','exact_delta_overlay'),('delta','exact_delta_overlay'),('cut','cut_aware_cache'),('mirror','full_coordinator_mirror'),('stale','unsafe_stale')]:
  if a in s:return b
 return s

def num(v):
 try:return float(v)
 except:return None
rows=[]
# CSV first: accept common names.
for p in sorted(RES.rglob('*.csv')):
 if p.name==CSVOUT.name:continue
 try:
  with p.open(newline='') as f: rr=list(csv.DictReader(f))
 except:continue
 if not rr:continue
 heads={h.lower():h for h in rr[0]}
 pk=next((heads[x] for x in heads if x in {'policy','strategy','method','baseline'}),None)
 bk=next((h for l,h in heads.items() if 'source' in l and 'byte' in l),None)
 if not pk or not bk:continue
 tk=next((h for l,h in heads.items() if l in {'trace','trace_id','scenario_seed','schedule'} or 'trace' in l),None)
 sk=next((h for l,h in heads.items() if l=='scenario'),None); seedk=next((h for l,h in heads.items() if l=='seed'),None)
 for i,r in enumerate(rr):
  b=num(r.get(bk));
  if b is None:continue
  tid=r.get(tk) if tk else None
  if not tid:tid='|'.join(str(r.get(k,'')) for k in (sk,seedk) if k) or f'{p.name}:{i}'
  rows.append({'file':str(p.relative_to(ROOT)),'trace':tid,'policy':canon(r[pk]),'source_bytes':b})
# JSON recursive fallback.
def walk(v,path=()):
 if isinstance(v,dict):
  yield path,v
  for k,z in v.items():yield from walk(z,path+(str(k),))
 elif isinstance(v,list):
  for i,z in enumerate(v):yield from walk(z,path+(str(i),))
for p in sorted(RES.rglob('*.json')):
 if p.name in {OUT.name,'reviewer-metrics.json'}:continue
 try:o=json.loads(p.read_text())
 except:continue
 for path,d in walk(o):
  pol=next((d.get(k) for k in ('policy','strategy','method') if isinstance(d.get(k),str)),None)
  if not pol:continue
  bk=next((k for k,v in d.items() if isinstance(v,(int,float)) and 'source' in str(k).lower() and 'byte' in str(k).lower()),None)
  if not bk:continue
  tid=d.get('trace_id') or d.get('trace') or ('|'.join(map(str,[d.get('scenario',''),d.get('seed','')])).strip('|')) or '/'.join(path[-3:])
  rows.append({'file':str(p.relative_to(ROOT)),'trace':str(tid),'policy':canon(pol),'source_bytes':float(d[bk])})
# Pick one observation per file/trace/policy, preferring mean-looking values by taking final duplicate.
uniq={}
for r in rows:uniq[(r['file'],r['trace'],r['policy'])]=r
rows=list(uniq.values())
# Group within each file, since different experiments have overlapping trace ids.
byfile=defaultdict(lambda:defaultdict(dict))
for r in rows:byfile[r['file']][r['trace']][r['policy']]=r['source_bytes']
comparisons=[]
rng=random.Random(20260920)
for file,traces in sorted(byfile.items()):
 for base in ('exact_delta_overlay','cut_aware_cache','full_coordinator_mirror'):
  diffs=[]; ratios=[]
  for tid,vals in traces.items():
   if 'continuation_certificate' in vals and base in vals:
    c=vals['continuation_certificate'];b=vals[base];diffs.append(c-b)
    if b:ratios.append(c/b)
  if len(diffs)<2:continue
  boots=[]
  for _ in range(20000):
   sample=[diffs[rng.randrange(len(diffs))] for _ in diffs]
   boots.append(statistics.fmean(sample))
  boots.sort()
  lo=boots[int(.025*len(boots))];hi=boots[min(len(boots)-1,int(.975*len(boots)))]
  comparisons.append({'file':file,'baseline':base,'paired_traces':len(diffs),'mean_difference_bytes':statistics.fmean(diffs),'median_difference_bytes':statistics.median(diffs),'min_difference_bytes':min(diffs),'max_difference_bytes':max(diffs),'bootstrap_95_interval_for_mean_difference':[lo,hi],'mean_ratio':statistics.fmean(ratios) if ratios else None,'interpretation':'descriptive over the frozen trace set; not an iid population confidence interval'})
out={'schema_version':1,'method':'20,000 deterministic paired bootstrap resamples over frozen trace-level differences','seed':20260920,'raw_rows':len(rows),'comparisons':comparisons,'warning':'Intervals summarize sensitivity to the finite trace set. They are not p-values and do not imply an iid workload population.'}
OUT.write_text(json.dumps(out,indent=2,sort_keys=True))
with CSVOUT.open('w',newline='') as f:
 keys=sorted({k for r in comparisons for k in r if k!='bootstrap_95_interval_for_mean_difference'})+['ci_low','ci_high']
 w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
 for r in comparisons:
  z={k:v for k,v in r.items() if k!='bootstrap_95_interval_for_mean_difference'};z['ci_low'],z['ci_high']=r['bootstrap_95_interval_for_mean_difference'];w.writerow(z)
print(json.dumps({'comparisons':len(comparisons),'raw_rows':len(rows)},sort_keys=True))
