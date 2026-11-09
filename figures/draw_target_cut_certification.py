"""Build the vector diagram used in the main manuscript."""
from pathlib import Path
from visual_grammar import Diagram, BLUE, RED, MUTED, PALE, GRID

def draw(out):
    d=Diagram(w=408,h=118)
    # Token update, coverage mask, and rank bound use distinct visual forms.
    for j,y in enumerate((91,101,111)):
        d.line((42,y),(95,y),c=GRID)
        d.dot(50+j*4,y,2.3,BLUE,'white')
        d.arrow((64+j*4,y),(91,y),c=BLUE)
    for j,y in enumerate((91,101,111)):
        d.rect(180,y-3,49,6,PALE,GRID,.7)
        d.check(218,y,BLUE)
    d.line((300,99),(374,99),c=GRID)
    for x in (307,319,330):d.dot(x,99,2.5,BLUE)
    d.line((343,92),(343,110),c=BLUE,lw=.85)
    d.rect(351,96,21,6,'white',MUTED,.85,dash=True)
    for x,tag,detail in ((68,'Advance tokens','Ordered source receipts'),
                         (205,'Check coverage','Target cut and epoch'),
                         (338,'Check unseen tail','Compare with global kth row')):
        d.text(x,78,tag,10,BLUE,bold=True)
        d.text(x,65,detail,9)
    d.arrow((110,101),(163,101),c=BLUE)
    d.arrow((245,101),(284,101),c=BLUE)
    d.arrow((205,56),(205,46),(95,46),(95,33),c=MUTED,dash=True)
    d.arrow((338,56),(338,43),(235,43),(235,33),c=RED)
    d.arrow((338,43),(360,43),(360,33),c=BLUE)
    d.text(158,53,'Gap',8.8,MUTED)
    d.text(277,51,'Blocker',8.8,RED)
    d.text(381,50,'No blocker',8.8,BLUE)
    d.text(95,23,'Partial: missing evidence',9.5,MUTED,bold=True)
    d.text(235,23,'Refill if possible',9.5,RED,bold=True)
    d.text(360,23,'Certify exact result',9.5,BLUE,bold=True)
    d.ax.set_ylim(13,118)
    d.fig.set_size_inches(408/72,105/72)
    d.finish(out)

if __name__ == '__main__':
    draw(Path(__file__).with_name('target-cut-certification.pdf'))
