"""Render the safe-policy cost comparison directly from retained primary results."""
import csv
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "artifact/figures"))
import matplotlib as mpl
mpl.use('Agg')
from matplotlib import pyplot as plt

HERE=Path(__file__).resolve().parent

def render(output=HERE/'tradeoff.pdf'):
    from validation_panels import search_cost
    data=HERE.parents[1]/'artifact/results/continuation-main.csv'
    with data.open(encoding='utf-8',newline='') as f:
        rows={r['policy']:r for r in csv.DictReader(f)}
    names=('continuation','overlay','cut-cache','mirror')
    labels=('Continuation','Overlay','Cut-aware cache','Full mirror')
    for name in names:
        row=rows[name]
        assert (row['queries'],row['claimed_complete'],row['false_complete'],row['unsound_rows'])==('4536','4248','0','0')
    assert rows['overlay']['max_logical_state_bytes']==''
    traffic=[float(rows[n]['mean_source_bytes']) for n in names]
    state=[float(rows[n]['max_logical_state_bytes'] or 0)/1024 for n in names]
    return search_cost(traffic,state,labels,output)

if __name__=='__main__':
    render()
