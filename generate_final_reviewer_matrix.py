#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; R=ROOT/'artifact'/'results'; out=ROOT/'artifact'/'FINAL-REVIEWER-MATRIX.md'
items=[
('Selective accounting','Source-only traffic can favor the proposed method.','reviewer-metrics.json','Report source-facing and end-to-end application bytes side by side; mirror is allowed to win end-to-end.'),
('Baseline fairness','Policies may receive different inputs or cuts.','baseline-fairness-gate.json','Shared corpus, query, target cut, ranker, oracle, and byte serializer are gated.'),
('Query schedule','Different queries could bias policies.','query-schedule-fairness.json','Semantic query-set equality is checked when raw IDs exist; otherwise the weaker aggregate check is labeled.'),
('Seed sensitivity','Two confirmatory seeds may be fragile.','extended-robustness-summary.json','A separately labeled post-hoc wider-seed run is reported without rewriting the confirmatory design.'),
('Unsafe oracle','A permissive checker might pass everything.','reviewer-negative-controls.json','Unsafe stale control must produce false completeness and invalid rows.'),
('Unexercised repair','Selective repair may be dead code.','reviewer-negative-controls.json','Repair count must be positive and unavailable-owner behavior is probed.'),
('Cold-start economics','Continuation state may hide initialization cost.','amortization-analysis.json','Cold bootstrap and recurrence break-even are modeled and labeled cross-campaign, not directly measured.'),
('Mirror trade-off','Mirror may be cheaper on the wire.','reviewer-metrics.json','Paper explicitly reports mirror end-to-end advantage and its state cost; no universal dominance claim.'),
('Proof assumptions','Completeness may depend on hidden trust.','reviewer-assumption-gate.json','Claim-to-assumption registry makes source honesty, ordering, epochs, rank locality, and cut semantics explicit.'),
('History realism','Generated churn may not represent repositories.','history-cutoff-diff.json','Public commit projection and post-freeze v7.2.0 cutoff audit are preserved, with scope limits.'),
('Reproducibility','Results may depend on the build host.','reproducible-pdf-check.json','Deterministic PDF rebuild plus exact-ZIP rerun is required.'),
('Reference padding','A large bibliography may be decorative.','reference-integrity-report.json','All keys must close across BibTeX, rendered references, audit ledger, and in-text citations.'),
('Artifact hygiene','Packages may leak local paths or secrets.','package-privacy-gate.json','Full-tree scan rejects build-host paths, keys, symlinks, caches, and nested release archives.'),
('PDF validity','A source build may still yield a malformed paper.','pdf-visual-preflight.json','All pages are rendered at 200 DPI; clipping, page size, fonts, and empty pages are gated.'),
]
lines=['# Final reviewer-objection matrix','', 'This is an internal red-team ledger, not a prediction of acceptance. Each item states what was actually mitigated and the evidence file that must exist in the artifact.', '', '| Concern | Why it matters | Mitigation | Evidence | Status |','|---|---|---|---|---|']
all_pass=True
for c,w,e,m in items:
    p=R/e; status='MISSING'
    if p.exists():
        try:
            d=json.loads(p.read_text()); ok=bool(d.get('pass',d.get('status') in {'PASS','pass'}))
            status='PASS' if ok else 'CHECK'; all_pass &= ok
        except Exception: status='CHECK'; all_pass=False
    else: all_pass=False
    lines.append(f'| {c} | {w} | {m} | `artifact/results/{e}` | {status} |')
lines += ['', '## Residual external-validity boundaries', '',
          'The artifact does not turn a single-host loopback prototype into a WAN deployment, does not replace deterministic queries with private production logs, does not certify a Byzantine source, and does not mechanically prove all executions. Those are disclosed scope boundaries rather than silently claimed accomplishments.', '',
          f'Overall executable-evidence closure: **{"PASS" if all_pass else "INCOMPLETE"}**.']
out.write_text('\n'.join(lines)+'\n')
print(out)
raise SystemExit(0 if all_pass else 1)
