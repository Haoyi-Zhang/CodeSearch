"""Render the manuscript schematics as vector PDFs."""
import argparse
from pathlib import Path

def draw(out):
    from validation_panels import search_protocol as panel
    return panel(out/'protocol.pdf')


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path(__file__).resolve().parent)
    output=parser.parse_args().output
    output.mkdir(parents=True,exist_ok=True)
    draw(output)
