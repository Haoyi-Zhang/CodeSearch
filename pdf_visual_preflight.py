#!/usr/bin/env python3
from __future__ import annotations
import json, math, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; PAPER=ROOT/'paper'; ART=ROOT/'artifact'; OUT=ART/'results'/'pdf-visual-preflight.json'
pdf=PAPER/'main.pdf'; render=ART/'results'/'pdf-render-200dpi'
if render.exists(): shutil.rmtree(render)
render.mkdir(parents=True)
checks={'pdf':str(pdf.relative_to(ROOT))}
try:
    import fitz
    doc=fitz.open(pdf)
    checks['pages']=len(doc)
    dims=[]; clipping=[]; empties=[]; image_counts=[]
    for i,page in enumerate(doc):
        rect=page.rect; dims.append([round(rect.width,3),round(rect.height,3)])
        words=page.get_text('words')
        if not words: empties.append(i+1)
        for w in words:
            x0,y0,x1,y1=w[:4]
            if x0 < rect.x0-1.5 or y0 < rect.y0-1.5 or x1 > rect.x1+1.5 or y1 > rect.y1+1.5:
                clipping.append({'page':i+1,'word':w[4],'bbox':[x0,y0,x1,y1]})
        image_counts.append(len(page.get_images(full=True)))
    checks['dimensions']=dims
    checks['all_letter']=all(abs(w-612)<1 and abs(h-792)<1 for w,h in dims)
    checks['empty_pages']=empties
    checks['clipped_words']=clipping[:50]
    checks['clipped_word_count']=len(clipping)
    checks['image_counts']=image_counts
except Exception as e:
    checks['fitz_error']=repr(e); checks['pages']=0; checks['all_letter']=False; checks['empty_pages']=['error']; checks['clipped_word_count']=-1
# Render all pages at 200 DPI.
subprocess.run(['pdftoppm','-png','-r','200',str(pdf),str(render/'page')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
pngs=sorted(render.glob('page-*.png'))
checks['rendered_pages']=len(pngs)
try:
    from PIL import Image, ImageOps, ImageDraw
    thumbs=[]
    for p in pngs:
        im=Image.open(p).convert('RGB'); im.thumbnail((330,430)); thumbs.append((p.name,im.copy()))
    cols=4; margin=18; label=22; rows=math.ceil(len(thumbs)/cols)
    sheet=Image.new('RGB',(cols*(330+margin)+margin,rows*(430+label+margin)+margin),'white')
    d=ImageDraw.Draw(sheet)
    for j,(name,im) in enumerate(thumbs):
        x=margin+(j%cols)*(330+margin); y=margin+(j//cols)*(430+label+margin)
        sheet.paste(im,(x,y+label)); d.text((x,y),name,fill='black')
    sheet.save(ART/'results'/'paper-contact-sheet.png')
    checks['contact_sheet']='artifact/results/paper-contact-sheet.png'
except Exception as e:
    checks['contact_sheet_error']=repr(e)
checks['pass']=checks.get('pages',0)>=13 and checks.get('rendered_pages')==checks.get('pages') and checks.get('all_letter') and not checks.get('empty_pages') and checks.get('clipped_word_count')==0
OUT.write_text(json.dumps(checks,indent=2,sort_keys=True)+'\n')
print(json.dumps(checks,indent=2,sort_keys=True))
raise SystemExit(0 if checks['pass'] else 1)
