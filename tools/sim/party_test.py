import sys,os,random; sys.path.insert(0,'.'); sys.argv=["x","warrior","2","1","1","1"]
import simbot
from llm.contracts import ActionIntent
from engine import arcs, quests, clock, checks
from ui import console as _c
out=open("/tmp/party.out","w")
def w(*a): out.write(" ".join(str(x) for x in a)+"\n"); out.flush()
notes=[]; _o=_c.note
_c.note=lambda t,*a,**k:(notes.append(t),_o(t,*a,**k))[1]
b=simbot.Bot(); ws=b.ws; c=ws.player.character
c.level=20; c.coins=50000; ws.player.guild_rank="D"
m=1440*30
while not all(clock.in_hours(m+h,(9,18)) for h in (0,120,240)): m+=30
ws.store.meta.minutes=m
ws.enter("guild_house"); ws.ensure_board()
arcs.roll_scale=lambda *a,**k:("arc","forced")
tpl=arcs.TEMPLATES["smuggling_ring"]
q=quests._quest("missing","D",tpl["board"].format(subject=tpl["victims"][0],place="X"),ws.minutes,victim=tpl["victims"][0],hall="guild_house",count=1); q["template"]="smuggling_ring"
gs=ws.store.load_place('guild_house'); gs.board=[q]; ws.store.save_place(gs)
w("no arc: list ->", ws.party_turn("who can I hire? any adventurers for hire"), notes[-1:])
notes.clear(); ws.on_accept_quest(ActionIntent(kind="accept_quest",item="1"),"take 1"); w("accept notes", notes, ws.rank, [x["title"] for x in ws.store.load_place("guild_house").board], ws.clerk_here())
data,arc=ws.my_arc()
w("arc nodes", [(n["kind"]) for n in arc["nodes"]])
w("contact stage: list ->", ws.party_turn("recruit some adventurers"), notes[-1:])
while True:
    n=arcs.current(arc)
    if n["kind"] in("lair","boss"): break
    arcs.complete_node(arc,n["id"])
ws.store.save_arcs(data)
notes.clear(); ws.enter("guild_house"); w("notice:", notes)
notes.clear(); w("list ->", ws.party_turn("Who are the adventurers available for hire?"), notes)
r=ws.party_roster(); w("roster", [(x["name"],x["role"],x["level"],x["fee"]) for x in r])
coins0=c.coins
notes.clear(); w("typed hire does nothing (f309) ->", ws.party_turn("I'd like to hire the first one, 1"), [m["name"] for m in ws.player.party])
for x in r[:3]:
    notes.clear(); ws.board_click(f"#boardhire {x['id']}"); w("pane hire ->", x["name"], notes[-1:] if notes else "")
w("party",ws.player.party, "mode", ws.player.party_mode)
w("roster after (no dupes)", [(x["name"]) for x in ws.party_roster()])
notes.clear(); ws.command("#party"); w("#party", notes)
# go to camp
n=arcs.current(ws.my_arc()[1]); ws.enter(n["place"]); ws.arc_arrival()
camp=arcs.current(ws.my_arc()[1])["camp"]; w("camp guards", len(camp["guards"]))
real=checks.roll
checks.roll=lambda odds,rng=None,c=None:("success",50)
notes.clear(); ws.handle("scout the camp"); w("scout with party notes", notes[-4:])
# stealth penalty visible via debug? compute
import scenes.camp_actions as ca
w("mods with", ws.camp_party_mod("sneak"), ws.camp_party_mod("bluff"), ws.camp_party_mod("scare"), ws.camp_party_mod("scout"))
ws.party_turn("have the party hold back and wait outside"); w("mode", ws.player.party_mode, ws.camp_party_mod("sneak"))
# fight: charge with party on hold
checks.roll=real
ws.handle("charge in")
f=ws.combat.fight
w("fight start allies", [(a.name,a.ally_role) for a in f.allies()], "ally reserves", [a.name for a in f.ally_reserves], "reserves", len(f.reserves))
rounds=0
simbot.LAST_DANGER[0]=('even',0.5)
while ws.combat and rounds<80:
    rounds+=1
    try: ws.handle("fight")
    except Exception as e: w("ERR",e); break
w("rounds",rounds, "combat left", bool(ws.combat), "party left", [(m["name"]) for m in ws.player.party], "hp", c.deaths)
w([x for x in notes if "fallen" in x or "arrive" in x or "burst" in x][:5])
# disband at end
data,arc=ws.my_arc(); w("arc state", arc and arc["state"], "party after", len(ws.player.party))
w("notes tail", notes[-6:])
w("---- casualties and disband")
from engine import party as pr, combat
ws.player.party=[{"id":"9-1","name":"Test Fighter","role":"fighter","level":10,"blurb":"x","arc":"zzz"},{"id":"9-2","name":"Test Priest","role":"priest","level":10,"blurb":"x","arc":arc["id"] if arc else "q"}]
f1=pr.fighter(ws.player.party[0]); f1.hp=0
notes.clear(); ws.party_after_fight([f1]); w("after fallen", [m["name"] for m in ws.player.party], notes)
# priest heal in a simulated fight
pl=combat.fighter_from_character(c); pl.hp=pl.max_hp*0.3
pr1=pr.fighter(ws.player.party[0])
cb=combat.Combat(fighters=[pl,pr1]+[combat.fighter_from_creature(ws.world.bestiary["bandit"],8,"normal","e1","b","near")],place="x",conditions=[])
import random
rng=random.Random(1)
combat.finish_round(cb,rng); w("heal log", [l for l in cb.log if "heals" in l])
data,arc=ws.my_arc()
if arc and arc["state"]=="active":
    ws.player.party=[{"id":"9-3","name":"Test Rogue","role":"rogue","level":10,"blurb":"x","arc":arc["id"]}]
    notes.clear(); ws.finish_arc(data,arc,None,yielded=True); w("finish_arc party", ws.player.party, [n for n in notes if "leave" in n])
ws.player.party=[{"id":"9-4","name":"T","role":"archer","level":10,"blurb":"x","arc":"a"}]
ws.party_disband(None,"you fell"); w("death disband", ws.player.party)
