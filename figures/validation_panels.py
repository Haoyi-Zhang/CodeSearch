"""Editable manuscript panels."""
import numpy as np
from visual_grammar import *


def search_protocol(out):
    d=Diagram(h=180)
    d.title(7,168,'A','Shard continuation')
    d.title(8,78,'B','Global check and replay')
    d.line((6,89),(420,89),c=GRID)
    for x,s,c in [(38,'Old token',BLUE),(126,'Ordered receipts',BLUE),(239,'Advance',TEAL),(329,'New token',TEAL)]:
        d.doc(x,126,c,GREEN if c==TEAL else PALE)
        d.text(x,106,s,9,c,bold=True)
    d.arrow((38,137),(38,150),(218,150),(218,133),(229,133),c=BLUE)
    d.arrow((136,126),(229,126),c=BLUE)
    d.arrow((249,126),(315,126),c=TEAL)
    d.arrow((339,126),(401,126),(401,66),(141,66),(141,50),c=TEAL)
    d.token(141,38,'k',BLUE)
    d.text(112,38,'Merge',9.2,BLUE,'right',True)
    d.arrow((151,38),(195,38),c=BLUE)
    d.check(204,38)
    d.text(215,38,'Complete if certified',8.9,TEAL,'left',True)
    d.arrow((141,27),(141,14),(200,14),c=RED)
    d.text(207,14,'Refill eligible blockers only',8.7,RED,'left')
    d.text(352,53,'Evidence + claim',8.6,PURPLE,bold=True)
    d.arrow((352,46),(352,38),c=PURPLE,dash=True)
    d.token(352,26,'C',PURPLE)
    d.text(367,26,'Replay',8.7,PURPLE,'left',True)
    d.finish(out)


def search_cut(out):
    d=Diagram(h=153)
    cuts=[118,161,204,247,290,333,376]
    a,m,b=cuts[0],cuts[3],cuts[-1]
    d.rect(a,39,b-a,89,PALE)
    for x in cuts:
        d.line((x,44),(x,124),c=GRID,lw=.6)
    for y,name,c,end in [(111,'Writer cut',BLUE,b),(76,'Receive proof',TEAL,b),(42,'Ranked index',RED,m)]:
        d.text(7,y,name,9.6,c,'left',True)
        d.line((90,y),(end,y),c=c,lw=1.1,dash=y==42)
        d.dot(end,y,4,c,'white')
    for i,x in enumerate(cuts):
        d.dot(x,76,2.7,TEAL,'white' if not i else TEAL)
    d.text(a,141,'Token cut',9.5,BLUE,bold=True)
    d.text(b,141,'Target cut',9.5,BLUE,bold=True)
    d.text(247,61,'Complete ordered suffix',8.8,TEAL,bold=True)
    d.text(m,24,'Index may lag',8.8,RED)
    d.text(7,12,'Schematic, not to scale',8.6,MUTED,'left')
    d.finish(out)


def search_cost(traffic,state,labels,out):
    fig=new(412,157)
    for i,(values,x,lim,ticks,title) in enumerate(zip((traffic,state),(.24,.643),(2840,2250),
            ((0,1000,2000),(0,750,1500)),('(a) Source bytes/query','(b) Peak logical state (KiB)'))):
        ax=plot_area(fig,(x,.20,.31,.65),'x')
        ax.set(xlim=(-.025*lim,lim),ylim=(3.55,-.55),yticks=range(4),xticks=ticks)
        ax.set_title(title,loc='left',fontweight='bold',fontsize=9.5)
        ax.tick_params(axis='y',length=0,labelsize=9.55)
        ax.tick_params(axis='x',labelsize=9.55)
        ax.set_yticklabels(labels if i==0 else ['']*4)
        ax.spines['left'].set_visible(False)
        for y,v in enumerate(values):
            c=TEAL if y==0 else BLUE
            ax.hlines(y,0,v,color=c,lw=1.4,alpha=.66)
            marker='D' if y==0 else 'o' if v else 's'
            ax.scatter(v,y,s=27 if y==0 else 21,edgecolor=c,zorder=4,marker=marker,facecolor=c if v else 'white')
            ax.text(v+lim*.042,y,'0' if not v else f'{v:,.0f}' if i==0 else f'{v:,.1f}',
                    va='center',fontsize=9.65,color=INK,weight='bold' if y==0 else 'normal')
    save(fig,out)
