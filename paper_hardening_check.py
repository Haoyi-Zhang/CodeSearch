#!/usr/bin/env python3
from __future__ import annotations
import json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAPER=ROOT/'paper'
ART=ROOT/'artifact'
OUT=ART/'results'/'paper-hardening-check.json'
pdf=PAPER/'main.pdf'; tex=PAPER/'main.tex'; log=PAPER/'main.log'
checks={}
checks['pdf_exists']=pdf.is_file() and pdf.stat().st_size>10000
checks['tex_exists']=tex.is_file()
if checks['pdf_exists']:
    info=subprocess.run(['pdfinfo',str(pdf)],capture_output=True,text=True,check=True).stdout
    m=re.search(r'^Pages:\s+(\d+)',info,re.M); pages=int(m.group(1)) if m else 0
    checks['page_count']=pages
    checks['letter_pages']=bool(re.search(r'Page size:\s+612 x 792 pts',info))
    txt=subprocess.run(['pdftotext','-layout',str(pdf),'-'],capture_output=True,text=True,check=True).stdout
    page_text=txt.split('\f')
    ref_pages=[i+1 for i,p in enumerate(page_text) if re.search(r'(?m)^\s*References\s*$',p)]
    checks['references_first_page']=ref_pages[0] if ref_pages else None
    checks['body_pages_ok']=checks['references_first_page']==13
    low=txt.lower()
    checks['has_end_to_end_accounting']='end-to-end application bytes' in low or 'end-to-end bytes' in low
    checks['has_source_accounting']='source-facing' in low or 'source rpc' in low or 'source bytes' in low
    checks['has_pareto']='pareto' in low
    checks['has_cutoff_audit']='v7.2.0' in txt and 'v7.1.8' in txt
    checks['has_cold_negative']='cold' in low and ('2.15' in txt or 'prefix' in low)
    checks['has_limitations']='limitation' in low or 'boundary' in low or 'boundaries' in low
else:
    checks.update(page_count=0,letter_pages=False,references_first_page=None,body_pages_ok=False,
                  has_end_to_end_accounting=False,has_source_accounting=False,has_pareto=False,
                  has_cutoff_audit=False,has_cold_negative=False,has_limitations=False)
textext=tex.read_text(errors='replace') if tex.exists() else ''
checks['loads_reviewer_macros']='reviewer_metrics_macros' in textext
checks['loads_reviewer_appendix']='reviewer_hardening_appendix' in textext
rendered=PAPER/'references.tex'
if rendered.exists():
    keys=re.findall(r'\\bibitem\{([^}]+)\}',rendered.read_text(errors='replace'))
else: keys=[]
checks['reference_count']=len(keys)
checks['reference_count_ok']=len(keys)>=55 and len(keys)==len(set(keys))
logtext=log.read_text(errors='replace') if log.exists() else ''
bad=[r'undefined references',r'undefined citations',r'Citation .* undefined',r'Reference .* undefined',r'Overfull \\hbox',r'Overfull \\vbox']
checks['latex_diagnostics']={p:bool(re.search(p,logtext,re.I)) for p in bad}
checks['latex_clean']=not any(checks['latex_diagnostics'].values())
# Metadata and font embedding
if pdf.exists():
    info=subprocess.run(['pdfinfo',str(pdf)],capture_output=True,text=True,check=True).stdout
    auth=re.search(r'^Author:\s*(.*)$',info,re.M)
    checks['anonymous_pdf_metadata']=not auth or not auth.group(1).strip()
    fonts=subprocess.run(['pdffonts',str(pdf)],capture_output=True,text=True,check=True).stdout.splitlines()
    rows=[]
    for line in fonts[2:]:
        parts=line.split()
        if len(parts)>=8: rows.append(parts)
    checks['font_rows']=len(rows)
    checks['fonts_embedded']=bool(rows) and all(r[-4].lower()=='yes' for r in rows)
else:
    checks['anonymous_pdf_metadata']=False; checks['font_rows']=0; checks['fonts_embedded']=False
required=['pdf_exists','tex_exists','letter_pages','body_pages_ok','has_end_to_end_accounting','has_source_accounting',
          'has_pareto','has_cutoff_audit','has_cold_negative','has_limitations','loads_reviewer_macros',
          'loads_reviewer_appendix','reference_count_ok','latex_clean','anonymous_pdf_metadata','fonts_embedded']
checks['required']=required
checks['pass']=all(bool(checks.get(k)) for k in required)
OUT.write_text(json.dumps(checks,indent=2,sort_keys=True)+'\n')
print(json.dumps(checks,indent=2,sort_keys=True))
raise SystemExit(0 if checks['pass'] else 1)
