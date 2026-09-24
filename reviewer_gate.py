#!/usr/bin/env python3
from pathlib import Path
import json,re,sys
A=Path(__file__).resolve().parent;P=A.parent/'paper';R=A/'results'
errors=[];checks=[]
def ck(cond,msg):
 checks.append({'check':msg,'pass':bool(cond)})
 if not cond:errors.append(msg)
for fn in ['reviewer-metrics.json','reviewer-hardening-summary.json','paired-trace-uncertainty.json','history-cutoff-audit.json']:
 ck((R/fn).exists(),f'{fn} exists')
if (R/'reviewer-metrics.json').exists():
 m=json.loads((R/'reviewer-metrics.json').read_text())
 ck(m.get('coverage',{}).get('raw_records',0)>0,'client payload metric is derived from raw records')
 rows=m.get('merged_policy_rows',[])
 def pick(p):
  xs=[x for x in rows if x.get('policy')==p and x.get('family')=='continuation_main'] or [x for x in rows if x.get('policy')==p]
  xs=[x for x in xs if x.get('mean_end_to_end_application_bytes') is not None]
  return max(xs,key=lambda x:len(x)) if xs else None
 c,o,cc,mir=[pick(x) for x in ['continuation_certificate','exact_delta_overlay','cut_aware_cache','full_coordinator_mirror']]
 ck(all([c,o,cc,mir]),'all four safe primary policies have end-to-end application metrics')
 if all([c,o,cc,mir]):
  def src(x):
   for k,v in x.items():
    if isinstance(v,(int,float)) and 'mean' in k.lower() and 'source' in k.lower() and 'byte' in k.lower():return float(v)
  ck(src(c)<src(o),'continuation source bytes below overlay')
  ck(src(c)<src(cc),'continuation source bytes below cut-aware cache')
  ck(c['mean_end_to_end_application_bytes']<o['mean_end_to_end_application_bytes'],'continuation total bytes below overlay')
  ck(c['mean_end_to_end_application_bytes']<cc['mean_end_to_end_application_bytes'],'continuation total bytes below cut-aware cache')
  ck(mir['mean_end_to_end_application_bytes']<c['mean_end_to_end_application_bytes'],'paper-visible non-advantage: mirror total bytes below continuation')
tex='\n'.join(p.read_text(errors='replace') for p in P.rglob('*.tex'))
ck('Accounting contract.' in tex,'paper includes accounting contract')
ck('Reviewer-facing accounting and validity audit' in tex,'paper includes reviewer appendix')
ck('not a universal communication' in tex or 'not a universal' in tex,'abstract/conclusion denies universal dominance')
ck('end-to-end application bytes' in tex,'paper reports end-to-end application bytes')
# Flag dangerous unqualified claims in prose (generated tables/macros excluded).
danger=[]
for p in P.rglob('*.tex'):
 if 'generated' in p.parts:continue
 for i,line in enumerate(p.read_text(errors='replace').splitlines(),1):
  low=line.lower()
  if ('dominates' in low or 'universally superior' in low or 'always better' in low) and not any(x in low for x in ['does not','not ','no ']):danger.append(f'{p}:{i}:{line.strip()}')
ck(not danger,'no unqualified universal dominance language')
# Reference closure remains >=55.
bib=P/'references.bib';rt=P/'references.tex'
if bib.exists():
 keys=set(re.findall(r'@\w+\s*\{\s*([^,\s]+)',bib.read_text()))
 ck(len(keys)>=55,f'at least 55 BibTeX references ({len(keys)})')
if rt.exists():
 items=set(re.findall(r'\\bibitem\{([^}]+)\}',rt.read_text()))
 ck(len(items)>=55,f'at least 55 rendered references ({len(items)})')
report={'status':'PASS' if not errors else 'FAIL','checks':checks,'errors':errors,'dangerous_lines':danger}
(R/'reviewer-gate.json').write_text(json.dumps(report,indent=2,sort_keys=True))
print(json.dumps({'status':report['status'],'checks':len(checks),'errors':errors},sort_keys=True))
if errors:sys.exit(1)
