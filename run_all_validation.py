#!/usr/bin/env python3
"""Run all scientific validation, plus paper gates when embedded in the full project."""
from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path

ART=Path(__file__).resolve().parent
PROJECT=ART.parent if ART.name=='artifact' and (ART.parent/'paper').is_dir() else ART
PAPER=PROJECT/'paper'
RESULTS=ART/'results'; RESULTS.mkdir(parents=True,exist_ok=True)
commands=[]

def run(label:str, cmd:list[str], cwd:Path)->dict:
    start=time.monotonic()
    p=subprocess.run(cmd,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    elapsed=time.monotonic()-start
    log=RESULTS/f'aggregate-{label}.log'
    text=p.stdout.replace(str(PROJECT),'$PROJECT_ROOT').replace(str(ART),'$ARTIFACT_ROOT')
    log.write_text(text)
    rec={'label':label,'command':cmd,'cwd':'$PROJECT_ROOT' if cwd==PROJECT else '$ARTIFACT_ROOT','returncode':p.returncode,'wall_seconds':elapsed,'log':str(log.relative_to(ART))}
    commands.append(rec)
    if p.returncode:
        raise RuntimeError(f'{label} failed; see {log}')
    return rec

start=time.monotonic(); status='PASS'; error=None
try:
    run('core',[sys.executable,'run_all_validation_core.py'],ART)
    scientific=[
        'reviewer_metrics.py','paired_uncertainty.py','generate_reviewer_hardening.py',
        'analyze_extended_robustness.py','reviewer_assumption_gate.py','reviewer_negative_controls.py',
        'amortization_analysis.py','code_quality_gate.py','reference_integrity_gate.py',
        'environment_report.py','baseline_fairness_gate.py','query_schedule_fairness_gate.py',
        'provenance_security_gate.py','history_cutoff_diff.py','claim_language_gate.py',
    ]
    for name in scientific:
        if (ART/name).exists(): run(name.removesuffix('.py'),[sys.executable,name],ART)
    paper_included=PAPER.is_dir() and (PAPER/'main.tex').exists()
    if paper_included:
        run('paper-build',[sys.executable,'build_and_validate.py'],PAPER)
        if (PAPER/'reproducible_pdf_check.py').exists():
            run('reproducible-pdf',[sys.executable,'reproducible_pdf_check.py'],PAPER)
        for name in ['paper_hardening_check.py','pdf_visual_preflight.py']:
            if (ART/name).exists(): run(name.removesuffix('.py'),[sys.executable,name],ART)
    # Release integrity exists in both layouts; paper-specific checks are conditional.
    if (ART/'validate_release.py').exists(): run('release',[sys.executable,'validate_release.py'],ART)
    if (ART/'package_privacy_gate.py').exists(): run('package-privacy',[sys.executable,'package_privacy_gate.py'],ART)
    if paper_included and (ART/'reviewer_gate.py').exists(): run('reviewer-gate',[sys.executable,'reviewer_gate.py'],ART)
    if paper_included and (ART/'generate_final_reviewer_matrix.py').exists(): run('reviewer-matrix',[sys.executable,'generate_final_reviewer_matrix.py'],ART)
except Exception as exc:
    status='FAIL'; error=repr(exc)
summary={'status':status,'pass':status=='PASS','layout':'full-project' if PAPER.is_dir() else 'standalone-artifact','wall_seconds':time.monotonic()-start,'commands':commands,'error':error}
(RESULTS/'final-validation-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps(summary,indent=2,sort_keys=True))
raise SystemExit(0 if status=='PASS' else 1)
