import sys; sys.path.insert(0,'.')
import random
from storage.campaign import CampaignStore
from world.loader import load_world
from engine import combat
w=load_world(); cr=w.bestiary
def chars():
    for c in ("warrior","mage","summoner","bard","smith","monk","warlock","paladin"):
        p=CampaignStore.open_or_create(f"sim_{c}").load_player(); yield c,p.character
def build(char, rank, lratio, n, mratio, unaware="none", frm=1, first=3, every=2, count=2, mid="bandit", leader="bandit_captain"):
    L=char.level
    fs=[combat.fighter_from_character(char)]
    ld=combat.fighter_from_creature(cr[leader],max(1,round(L*lratio)),rank,"e0","leader","near")
    guards=[combat.fighter_from_creature(cr[mid],max(1,round(L*mratio)),"normal",f"e{i+1}",f"g{i}","near") for i in range(n)]
    fw=guards[:first]
    if unaware=="all":
        for f in fw: f.statuses["unaware"]=1
    if unaware in("all","leader"): ld.statuses["unaware"]=1
    c=combat.Combat(fighters=fs+[ld]+fw,place="x",conditions=[])
    c.reinforce_from=frm; c.reserves=guards[first:]; c.reinforce_every=every; c.reinforce_count=count
    return c
def row(rank,lr,n,mr,**kw):
    out={}
    for label,(nn,un,fr) in {"charge":(n,"none",1),"half":(max(0,n//2),"none",1),"ambush":(n,"leader",4),"strong":(n,"all",6),"thinned+amb":(max(0,n//3),"leader",4)}.items():
        v=[]
        for name,ch in chars():
            v.append(combat.danger(build(ch,rank,lr,nn,mr,unaware=un,frm=fr,**kw),runs=30,seed=1)[1])
        out[label]=v
    return out
cfgs=eval(sys.argv[1])
for name,(rank,lr,n,mr) in cfgs.items():
    o=row(rank,lr,n,mr)
    print(name, " | ".join(f"{k} {sum(v)/len(v):.2f}" for k,v in o.items()), " charge per class", [round(x,2) for x in o["charge"]])
