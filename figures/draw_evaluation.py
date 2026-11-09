"""Check the retained plot table and render the primary cost figure."""
import csv
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent

def read_rows(path):
    with (ROOT/path).open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    artifact=ROOT.parent/'artifact'
    sys.path.insert(0,str(artifact))
    from result_metrics import validate_primary,tradeoff_rows
    summary=json.loads((artifact/'results/continuation-summary.json').read_text(encoding='utf-8'))
    validate_primary(artifact,summary)
    if rows!=tradeoff_rows(summary):
        raise ValueError('CSV disagrees with reconstructed metrics: '+path)
    return rows

def main():
    from draw_tradeoff import render
    read_rows('figures/tradeoff.csv')
    render()

if __name__=='__main__':
    main()
