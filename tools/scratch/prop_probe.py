import sys; sys.path.insert(0,'.'); sys.argv=["x","ranger","2","1","1","1"]
import simbot
from llm.contracts import ActionIntent
out=open("/tmp/p.out","w")
def w(*a): out.write(" ".join(str(x) for x in a)+"\n"); out.flush()
b=simbot.Bot(); ws=b.ws
c=ws.player.character; c.coins=30_000_000
from engine import clock
m=0
while not all(clock.in_hours(m+h,(9,18)) for h in (0,120,240)): m+=30
ws.store.meta.minutes=m
for town in ["lethoria","parth"]:
    ws.enter(town); w(town,ws.minutes,[n.role for n in ws.residents],[n.role for n in ws.present],[ (n.role,n.away_until) for n in ws.residents if n not in ws.present])
    ws.on_buy(ActionIntent(kind="buy",ware="a house"),"buy a house"); w("coins",c.coins, ws.player.homes.keys())
    if town=="lethoria":
        ws.show_shop()
        ws.on_buy(ActionIntent(kind="buy",ware="Kingsfall"),"buy Kingsfall"); w("pack",[i.name for i in ws.pack], ws.player.relics_bought)
        ws.show_shop()
ws.enter("home_lethoria"); w("at",ws.place.name,ws.place.type, ws.can_store(), ws.has_room())
for u in ["garden","strongroom","workshop","hearth"]:
    ws.on_buy(ActionIntent(kind="buy",ware=u),f"buy a {u}")
w(ws.player.homes, ws.stash_cap(), ws.place.stations)
ws.enter("lethoria"); ws.enter("home_lethoria"); w("pack",len(ws.pack))
ws.show_home()
# reload
from scenes.world import WorldScene
from storage.campaign import CampaignStore
ws.store.save_player(ws.player)
p2=ws.store.load_player(); w("reload homes",p2.homes, p2.relics_bought, p2.location)
