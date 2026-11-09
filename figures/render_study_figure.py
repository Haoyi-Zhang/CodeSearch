"""Render the manuscript example as a vector PDF."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "artifact/figures"))

def codesearch(output):
    from validation_panels import search_cut as panel
    return panel(output)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path(__file__).with_name('continuation-cut.pdf'))
    a=p.parse_args()
    codesearch(a.output)
