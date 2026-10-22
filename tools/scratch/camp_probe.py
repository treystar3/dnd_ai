import sys,os,random; sys.path.insert(0,'.'); sys.argv=["x","warrior","2","1","1","1"]
import simbot
from llm.contracts import ActionIntent
from engine import arcs, quests, clock, checks
out=open("/tmp/camp.out","w")
def w(*a): out.write(" ".join(str(x) for x in a)+"\n"); out.flush()
b=simbot.Bot(); ws=b.ws; c=ws.player.character
c.level=20; c.coins=1000; ws.player.guild_rank="D"
m=1440*30
while not all(clock.in_hours(m+h,(9,18)) for h in (0,120,240)): m+=30
ws.store.meta.minutes=m
ws.enter("guild_house")
arcs.roll_scale=lambda *a,**k:("arc","forced")
TID=os.environ.get("TID","smuggling_ring")
def setup():
    c.level=20; ws.combat=None; ws.player.guild_rank="D"
    ws.store.save_arcs(arcs.empty()); ws.player.quests=[]; ws.store.meta.minutes+=1440*25
    while not all(clock.in_hours(ws.store.meta.minutes+h,(9,18)) for h in (0,120,240)): ws.store.meta.minutes+=30
    ws.enter('guild_house'); ws.ensure_board()
    tpl=arcs.TEMPLATES[TID]
    q=quests._quest("missing","D",tpl["board"].format(subject=tpl["victims"][0],place="X"),ws.minutes,victim=tpl["victims"][0],hall="guild_house",count=1)
    q["template"]=TID
    gs=ws.store.load_place('guild_house'); gs.board=[q]; ws.store.save_place(gs)
    ws.on_accept_quest(ActionIntent(kind="accept_quest",item="1"),"take 1")
    data,arc=ws.my_arc()
    if not arc: w('NO ARC', ws.player.quests, [x['title'] for x in ws.store.load_place('guild_house').board], ws.rank, ws.combat)
    while True:
        n=arcs.current(arc)
        if n["kind"] in("lair","boss"): break
        arcs.complete_node(arc,n["id"]); 
    ws.store.save_arcs(data)
    ws.enter(n["place"]); 
    started=ws.arc_arrival()
    return n
real_roll=checks.roll
def force(degree):
    checks.roll=lambda odds,rng=None:(degree,50)
def say(t):
    ws.handle(t)
    data,arc=ws.my_arc(); n=arcs.current(arc) if arc else None
    return n
def state(tag):
    data,arc=ws.my_arc(); n=arcs.current(arc) if arc else None
    cp=n.get("camp") if n else None
    w(tag,"combat" if ws.combat else "-", "alert",cp and cp["alert"],"edge",cp and cp["edge"],"guards",cp and [(g["name"],g["state"]) for g in cp["guards"]], "enemies",[(e.name,e.band,list(e.statuses)) for e in ws.combat.fight.enemies()] if ws.combat else None)
n=setup(); state("arrive"); w("camp_ctx",bool(ws.camp_ctx()), "events", ws.camp_events)
# scout success
force("success"); say("I scout the camp from the treeline"); state("scout ok")
say("scout again"); 
# sneak success
force("success"); say("sneak up on the first guard and knock him out"); state("sneak ok")
# non-matching text falls through?
w("passthrough", ws.camp_turn("what is the weather like"))
# partial sneak
force("partial"); say("quietly take out the second guard"); state("sneak partial")
# ambush strong
setup(); state("re-setup"); force("strong success"); say("I ambush the leader from the shadows"); state("ambush strong")
for case,deg,text in [("ambush success","success","strike from cover at the leader"),("ambush partial","partial","ambush the leader"),("ambush fail","failure","ambush the leader"),
    ("bluff success","success","I bluff my way in, claiming to be a buyer"),("bluff partial","partial","pretend I'm a smuggler"),("bluff fail","failure","bluff my way in"),
    ("scare strong","strong success","intimidate the guards"),("scare success","success","threaten the guards"),("scare partial","partial","scare the guards off"),("scare fail","failure","scare them"),
    ("sneak fail","failure","sneak up on a guard"),("charge","success","charge in")]:
    setup(); force(deg); say(text); state(case)
# scout failure raising alert, then return decay
setup(); force("failure"); say("scout the camp"); state("scout fail")
data,arc=ws.my_arc(); n=arcs.current(arc); 
# alarm via two failures -> fight; flee; then leave and return
setup(); force("failure"); say("sneak up on a guard"); state("sneak fail -> alarm")
if ws.combat:
    ws.combat.fight.over="fled"; ws.combat.finish()
state("after flee")
data,arc=ws.my_arc(); n=arcs.current(arc); ws.advance_quiet(1440*1); ws.enter("guild_house"); ws.enter(n["place"]); w("arrive again after 1 day", ws.arc_arrival()); state("return +1d")
w("events",ws.camp_events)
# ---- model-read intent and methods
w("---- LLM intent")
import io,contextlib
from ui import console as _c
notes=[]
_orig=_c.note
_c.note=lambda t,*a,**k:(notes.append(t),_orig(t,*a,**k))[1]
import scenes.camp_actions as ca
from llm.contracts import CampIntent
setup(); state("fresh")
ca.generate=lambda *a,**k: CampIntent(kind="sneak",target="smuggler 2",method=["cover","darkness","patience","distraction","disguise"],summary="crawl")
force("success"); say("I crouch through the tall grass sneaking on all fours until I'm close enough to assassinate the guard")
state("llm sneak"); w("bonus note check, events", ws.camp_events[-1])
ca.generate=lambda *a,**k: CampIntent(kind="none")
w("none falls through", ws.camp_turn("I check my pack"))
def boom(*a,**k): raise ca.LLMError("down")
ca.generate=boom
w("fallback keywords", ws.camp_turn("I scout the camp"), ws.camp_events[-1])

w("NOTES", [x for x in notes if "approach" in x or "nothing" in x.lower() or "too bright" in x or "disguise" in x.lower()])
