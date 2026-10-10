import sys; sys.path.insert(0,'.')
exec(open("/tmp/tune4.py").read().split("cfgs=")[0])
from engine import party as pr
def build2(char, rank, lratio, n, mratio, roles, share=0.5, hold=False, unaware="none", frm=1):
    c=build(char,rank,lratio,n,mratio,unaware=unaware,frm=frm)
    L=char.level
    members=[pr.fighter({"id":f"m{i}","name":f"M{i}","role":r,"level":max(1,round(L*share))}) for i,r in enumerate(roles)]
    if hold: c.ally_reserves=members; c.ally_arrive=3
    else: c.fighters+=members
    return c
cfg=eval(sys.argv[1])
combat.RULES['ally_heal'].update(eval(sys.argv[2]))
for name,(rank,lr,n,mr) in cfg.items():
    for roles in ([],["fighter"],["archer"],["fighter","priest"],["fighter","priest","archer"],["fighter","fighter","archer"]):
        for hold in ((False,) if roles else (False,)):
            v=[combat.danger(build2(ch,rank,lr,n,mr,roles,hold=hold),runs=30,seed=1)[1] for _,ch in chars()]
            print(f"{name:22s} {'+'.join(r[:3] for r in roles) or 'solo':16s} {'hold' if hold else 'with'}  mean {sum(v)/len(v):.2f} {[round(x,2) for x in v]}")
