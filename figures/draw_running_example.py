"""Draw the published token-buffer example. The keys are illustrative, not measurements."""
from pathlib import Path
import argparse

from visual_grammar import Diagram, INK, MUTED, TEAL, GRID


def render(out):
    initial={1,3,7}
    first=(initial-{3})|{2}
    later=first-{1,2}
    states=(initial,first,later)
    assert tuple(tuple(sorted(s)) for s in states)==((1,3,7),(1,2,7),(7,))
    tail=9
    d=Diagram(w=360,h=107)
    offset=lambda k: 125+(k-1)*23.8
    x_tail=offset(tail)
    d.text(x_tail,98,'Tail bound',9.0,MUTED,bold=True)
    d.line((x_tail,17),(x_tail,90),c=MUTED,dash=True,lw=.65)
    for y,name,state in zip((76,49,22),('Initial token','After fold','After deletions'),states):
        d.text(10,y,name,9.6,INK,'left',True)
        d.line((109,y),(x_tail-10,y),c=GRID,lw=.55)
        for k in sorted(state):
            x=offset(k)
            d.dot(x,y,6.6,TEAL,'white')
            d.text(x,y,str(k),8.9,INK,bold=True)
        d.text(x_tail+13,y,'9',9.1,INK,'left')
    d.finish(out)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    render(p.parse_args().output)
