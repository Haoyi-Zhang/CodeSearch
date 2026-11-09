"""Rebuild the paper's mechanism schematics at their intended physical size."""
from pathlib import Path
from diagram_core import Figure, BLUE, GRAY, INK, RED

def feed_frontier(f):
    f.t(28,12,'Received',align='left',bold=True)
    for x,tag in [(123,'n'),(197,'n+1'),(270,'n+2')]:
        f.knot(x,36,RED if x==197 else BLUE,solid=x!=197)
        f.t(x,53,tag)
    f.line((123,36),(197,36),color=GRAY,dash=True)
    f.line((197,36),(270,36),color=GRAY,dash=True)
    f.t(197,72,'missing',color=RED)
    f.node(337,36,'lock','Frontier stays at n',side='below')
    f.t(28,84,'Checkpoint before pruning',align='left',color=GRAY,style='italic')
    f.route((283,36),(322,36),dash=True,color=RED)

FIGURES = [('feed_frontier', 420, 75)]

if __name__ == '__main__':
    for name,w,h in FIGURES:
        f=Figure(dict(media=(w,h),trim=(0,0,0,0),width=w))
        globals()[name](f)
        f.finish(Path(__file__).parent/(name.replace('_','-')+'.pdf'))
