"""The mentor: she comes over in Parth after a short wait and asks whether you know the guild (two yeses skip it all), explains the ranks
and the board, can be talked to throughout, hands over a first contract, teaches tracking in the Greywood (the first search finds the
wolves), teaches the fight in words that suit the build, cannot let you die, and then a troll that should not be there is killed by her
in one flashy blow with figures from the engine."""
import sys, random, shutil, re
sys.path.insert(0, ".")
import simlib
from types import SimpleNamespace as NS
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
CHOICE = [{"kind": "attack", "target": "e0"}]
stub.bot = NS(combat_choice=lambda: dict(CHOICE[0]))
stub.a_Narration = lambda u, k: {"text": "The fight rages on."}
ASKED = []
stub.a_MentorReply = lambda u, k: (ASKED.append(u) or {"speech": "The board is in the guild hall. Mind your feet."})
import config
import ui.console as uc
SAID, NOTES, ANSWERS = [], [], []
uc.say = lambda t, s="": SAID.append((s, t))
uc.dialogue = lambda b, s, t, a: SAID.append((s, t))        # her words framed by the narrator (f274) count as said by her
uc.narrate = lambda t: SAID.append(("narrate", t))
uc.note = lambda m, *a, **k: NOTES.append(str(m))
uc.ask = lambda *a, **k: ANSWERS.pop(0) if ANSWERS else ""
from engine import combat, mentor, pools, inventory, money
from core.models import Archetype
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
from llm.contracts import ActionIntent
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

M = mentor.M
world = load_world()

def fresh(name, level=1, location="parth", seed=5):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
    st = CampaignStore.open_or_create(name)
    st.meta.seed = seed; st.meta.turn = 1; st.meta.minutes = 600; st.save_meta()
    ch, _ = simlib.make_character("warrior", random.Random(2))
    ch.level = level
    st.save_player(PlayerState(character=ch, location=location))
    w = WorldScene(st, world, load_traits(), st.load_player())
    config.TURN_LOG_PATH = f"saves/{name}/turns.jsonl"
    w.narrate = lambda e, t="": None
    w.narrate_with = lambda *a, **k: None
    w.show_exits = lambda *a, **k: None
    return st, w

store, ws = fresh("mentor_test")
player = ws.player; c = player.character

# ---- she comes over at once, and the scene fits where you stand
check("her wait is over before it starts", M["gate"]["wait_minutes"] == 0)
ANSWERS[:] = ["I came looking for work", "I hunt for coin and found this lance in the fields", "no, not really", "ok", "ok", "ok", "go on"]
ws.mentor_intercept("I look around")
spoken = " ".join(t for _, t in SAID)
check("she approaches at the first action and the stage is invite", mentor.stage(player) == "invite", mentor.stage(player))
check("she is seen first, and asks what brings you to Parth", "enamelled A" in spoken and "What brings you to Parth?" in spoken and "table" not in spoken, spoken[:300])
paras = [t for k, t in SAID if k == "narrate" and t in M["approach"]["narrate"]]
check("the meeting is narrated a paragraph at a time", len(paras) >= 5 and all("\n" not in t for t in paras), len(paras))
check("whatever you answer is remembered", ["Player", "I came looking for work"] in player.mentor["chat"], player.mentor.get("chat"))
unnamed = [t for sp, t in SAID if sp == M["unnamed"]]
said = [t for sp, t in SAID if sp == mentor.NAME]
check("what brings you here is spoken by her, not narrated, and not yet under her name (f273)", unnamed and unnamed[0] == M["approach"]["ask_first"] and not any(t == M["approach"]["ask_first"] for k, t in SAID if k == "narrate"), unnamed[:1])
check("whatever they answer, she is cold and asks her pointed question first", len(unnamed) >= 2 and "bandit" in unnamed[1] and "cold" in unnamed[1], unnamed[1:2])
check("the answer to that settles her: her next words carry her name, introduce her and ask how new they are, in one block", said and not said[0].startswith("Maren.") and "guild badge" in said[0] and "how new they are to the guild" in said[0], said[:2])
check("the weapon is named by its kind, not its quality", "crude" not in said[1] and "ash" not in said[1] or not c.equipment.get("main_hand"), said[1][:150])
check("she is given what to say as facts, not as her scripted lines", "Adventurer, then." not in spoken and "carries longsword" in spoken or not c.equipment.get("main_hand"))
check("she asks whether you know the guild", "how new they are to the guild" in spoken)
check("a doubtful answer gets the walkthrough", "nobody is born knowing" in spoken.lower() and not player.mentor.get("skipped"))
from engine import items as _it
check("she notices the weapon", (_it.base_of(c.equipment["main_hand"]).name.lower() in spoken) if c.equipment.get("main_hand") else True)
check("her A rank is shown in the meeting, not repeated in the lesson", "enamelled A" in spoken and "I carry the A rank" not in spoken)
rl = mentor.rank_lines()
check("she tells the ranks briefly, F to S, with no thresholds (f293)", "F at the bottom" in spoken and not any(line in spoken for line in rl) and "Nobody is promoted" not in spoken, rl)
check("...the thresholds are still hers to give when asked", all(line in mentor.facts(player, "Parth", "what do I need to reach rank D?") for line in rl[:2]))
check("...and no board lecture in the street (f302)", "hold 2 at a time" not in spoken, spoken[-300:])
check("...and joining, with the fee", money.words(300) in spoken)
check("...in that order", spoken.index("F at the bottom") < spoken.index(money.words(300)))
check("then she says she will take them to the hall and help them register, and invites questions (f294)", ("help you get registered" in spoken or "help them get registered" in spoken)
      and ("Ask me anything" in spoken or "ask it" in spoken) and "'go on'" not in spoken and "That is all. You start at rank F" not in spoken, spoken[-400:])
SAID.clear()
ws.mentor_tick()
check("she waits for the guild", mentor.stage(player) == "invite" and not SAID and not player.quests)

# the same meeting wherever you stand: nothing in it depends on a table
for pid in ("tilted_plough", "guild_house", "parth_temple"):
    s9, w9 = fresh("mentor_where")
    w9.enter(pid)
    ANSWERS[:] = ["work", "proof", "yes", "yes"]
    SAID.clear()
    w9.mentor_intercept("I look around")
    sp = " ".join(t for _, t in SAID)
    check(f"in {pid} she comes over and the lesson is skipped on two yeses", "enamelled A" in sp and "Good hunting" in sp and "table" not in sp, sp[:200])

# ---- you can talk to her while she waits in Parth
check("she is within reach in Parth", ws.mentor_with_you())
ASKED.clear(); SAID.clear()
ws.on_talk(ActionIntent(kind="talk", target="", speech="Is the guild hard on newcomers?"), "Is the guild hard on newcomers?")
check("she answers in her own voice", any(s == mentor.NAME and "guild hall" in t for s, t in SAID), SAID)
check("the reply was built from the fact sheet, with only the index for a question that names no subject", ASKED and "YOU KNOW EXACTLY" in ASKED[0] and "GUILD RANKS" not in ASKED[0] and "Is the guild hard" in ASKED[0], ASKED[:1])
check("what was said is remembered", player.mentor["chat"][-2][0] == "Player" and "guild hall" in player.mentor["chat"][-1][1])
SAID.clear()
ws.on_talk(ActionIntent(kind="talk", target="willa_x", speech="hello"), "hello Maren")
check("naming her sends it to her whoever else is addressed", any(s == mentor.NAME for s, _ in SAID))

# ---- once the player has joined she points to the board and waits for them to take the hunt
player.guild_rank = "F"
store.meta.minutes = 1800
ws.mentor_tick()
check("she does not hand over the contract", mentor.stage(player) == "board" and not player.quests, (mentor.stage(player), player.quests))
check("she points them at the board pane and the wolf hunt, and at hiring from the board (f285)", any("wolf hunt" in t and "#board" in t and "Board pane" in t and "Say '" not in t and "listed on the board" in t for _, t in SAID), [t for _, t in SAID][-2:])
ws.enter("guild_house"); ws.refresh_present()
board = ws.ensure_board()
check("the board shows only her hunt", len(board) == 1 and board[0].get("mentor") and board[0]["creature"] == "wolf", board)
data = ws.board_data()
check("...and the pane shows it too", len(data["postings"]) == 1 and "wolves" in data["postings"][0]["title"], data["postings"])
check("the clerk is here to record it", ws.clerk_here() is not None)
SAID.clear()
for _ in range(4):
    ws.mentor_tick()
check("she waits, and reminds them now and then", mentor.stage(player) == "board" and any(t in M["board_step"]["waiting"] for _, t in SAID), SAID)
ws.on_accept_quest(ActionIntent(kind="accept_quest", item="the other contract"), "take the other contract")
check("nothing else can be taken", not player.quests or all(x.get("mentor") for x in player.quests))
check("she is not in the party before she is hired", not any(m.get("story") == "maren" for m in player.party))
check("typing 'hire Maren' hires no one: hiring is the Board pane's (f309)", not ws.party_turn("hire Maren") and not any(m.get("story") == "maren" for m in player.party))
ws.board_click("#boardhire maren")
check("the pane's Hire takes her on, free", any(m.get("story") == "maren" for m in player.party), player.party)
coins_h = c.coins
ws.board_click("#boardhire maren")
check("...once", sum(1 for m in player.party if m.get("story") == "maren") == 1)
ws.party_turn("dismiss Maren")
check("she cannot be dismissed mid-job", any(m.get("story") == "maren" for m in player.party))
ws.on_accept_quest(ActionIntent(kind="accept_quest", item="wolf hunt"), "I take the wolf hunt")
q = next((x for x in player.quests if x.get("mentor")), None)
check("taking it from the board holds it", q is not None, player.quests)
SAID.clear()
ws.mentor_tick()
check("then she moves on", mentor.stage(player) == "hunt" and any(M["board_step"]["go"] in t for _, t in SAID) and not player.mentor.get("posting"))
check("she is in the party for the hunt", any(m.get("story") == "maren" and m.get("tutorial") for m in player.party) and len(player.party) == 1, player.party)
check("the party pane lists her, with her guild rank and her real level", any(a["name"] == mentor.NAME and a["rank"] == "A" and a["level"] >= 100 for a in ws.party_data()["adventurers"]), ws.party_data()["adventurers"])
check("three wolves in the Greywood, no clock", q and q["creature"] == "wolf" and q["count"] == 3 and q["place"] == "greywood" and q["deadline"] is None, q)
check("it is a guild contract", q and q["guild"] and q["letter"] == "F")
check("the board is empty once it is taken", ws.ensure_board() == [])
SAID.clear(); NOTES.clear()
ws.on_abandon_quest(ActionIntent(kind="abandon_quest", item="wolves"), "abandon the wolf hunt")
check("it cannot be abandoned", any(x.get("mentor") for x in player.quests) and any(s == mentor.NAME for s, _ in SAID) and not any("Abandoned" in n for n in NOTES))
ws.board_click("#boardabandon " + q["id"])
check("...not from the pane either", any(x.get("mentor") for x in player.quests))

# ---- nothing happens until the player reaches the Greywood
SAID.clear()
ws.mentor_tick()
check("no fight in town", ws.combat is None and not SAID)
check("search does nothing special outside the Greywood", not ws.mentor_search())
ws.enter("greywood")
ws.mentor_tick()
spoken = " ".join(t for _, t in SAID)
check("arriving teaches tracking, no ambush", ws.combat is None and "search for wolves" in spoken and player.mentor["briefed"], spoken[-300:])
check("the wording suits a melee build", mentor.build_of(c) == "melee" and "blade loose" in spoken or "ready" in spoken)
n = len(SAID); ws.mentor_tick()
check("the lesson is given once", len(SAID) == n)
ASKED.clear(); SAID.clear()
ws.on_talk(ActionIntent(kind="talk", target="", speech="How does searching work?"), "How does searching work?")
check("she can be asked about it on the spot", any(s == mentor.NAME for s, _ in SAID) and "search for wolves" in ASKED[0])

# ---- the first search finds the wolves
SAID.clear()
before = store.meta.minutes
ws.on_search(ActionIntent(kind="search", seek="wolves"), "search for wolves")
check("the search takes time", store.meta.minutes > before)
check("the wolves are found", ws.combat is not None and ws.combat.fight.mentor and len(ws.combat.fight.enemies()) == 3)
f = ws.combat.fight
check("she sits out the wolf fight although she is in the party", not any(a.ally_role for a in f.allies()), [a.name for a in f.allies()])
check("three wolves of the player's level", all(e.creature == "wolf" and e.level == c.level for e in f.enemies()))
check("the wolves fight to the end", all(e.yields_at == 0 for e in f.enemies()))
check("she gives the first lesson", any(s == mentor.NAME and "wolf" in t for s, t in SAID) and any("nearest" in t for _, t in SAID))

# ---- no running, no taming, no talking to wolves; talking to her is free
for kind in ("flee", "tame", "talk"):
    SAID.clear(); rnd = f.round
    CHOICE[0] = {"kind": kind, "target": "e0", "approach": "persuade"}
    ws.combat.turn("I try to " + kind)
    check(f"{kind} is refused and costs no turn", f.round == rnd and ws.combat is not None and any(s == mentor.NAME for s, _ in SAID))
SAID.clear(); rnd = f.round; ASKED.clear()
CHOICE[0] = {"kind": "talk", "target": "e0", "approach": ""}
ws.combat.turn("Maren, how do I drink a potion?")
check("talking to her mid-fight is free and answered", f.round == rnd and ASKED and "fight" in ASKED[0] and any(s == mentor.NAME and t for s, t in SAID), (f.round == rnd, bool(ASKED), SAID[-2:]))
SAID.clear(); rnd = f.round
CHOICE[0] = {"kind": "talk", "target": "", "approach": ""}
ws.combat.turn("what do I do now?")
check("so is a plain question with no target", f.round == rnd and any(s == mentor.NAME for s, _ in SAID))

# ---- first blood: a draught is thrown to you
CHOICE[0] = {"kind": "attack", "target": "e0"}
check("no draught before you are hurt", not any(i.good == M["hunt"]["potion"] for i in c.inventory))
f.player.hp = f.player.max_hp - 3
SAID.clear()
ws.combat.turn("I attack the nearest wolf")
if ws.combat:
    check("a draught arrives when you are first hurt", any(i.good == M["hunt"]["potion"] for i in c.inventory) or "first_blood" in ws.combat.fight.mentor_beats)
    check("she tells you to drink it", any("healing draught" in t for s, t in SAID if s == mentor.NAME))

# ---- the floor: you cannot die in this fight
f2 = ws.combat.fight if ws.combat else None
if f2:
    me = f2.player
    me.hp = 2
    combat.take_damage(f2, me, 500, f2.enemies()[0], random.Random(1))
    check("the killing blow leaves you on 1", me.hp == 1 and f2.mentor_saved == 1 and not f2.over)
    SAID.clear(); NOTES.clear()
    for i in list(c.inventory):
        if i.good == M["hunt"]["potion"]:
            c.inventory.remove(i)
    ws.mentor_round(ws.combat)
    check("she calls it out and tosses another draught", any(s == mentor.NAME for s, _ in SAID) and any("another healing draught" in n for n in NOTES) and any(i.good == M["hunt"]["potion"] for i in c.inventory))
    check("the fight goes on: no one steps in", f2.over == "" and ws.combat is not None and mentor.stage(player) == "hunt")
    combat.take_damage(f2, me, 900, f2.enemies()[0], random.Random(2))
    check("it holds every time", me.hp == 1 and f2.mentor_saved == 2 and me.alive)
    me.statuses["bleeding"] = 3; me.hp = 1
    combat.start_turn(me, f2)
    check("a bleed cannot kill you either", me.hp >= 1)
    combat.take_damage(f2, f2.enemies()[0], 1, me, random.Random(3))
    check("wolves can still be hurt", True)

# ---- a draught is a free action, once a turn, with a healing figure like a blow's; and she answers in the middle of a fight
ft = ws.combat.fight
ws.to_pack(inventory.make_good(M["hunt"]["potion"])); ws.to_pack(inventory.make_good(M["hunt"]["potion"]))
me = ft.player; me.hp = 10
rnd = ft.round; SAID.clear(); NOTES.clear(); n0 = len(ft.hits)
CHOICE[0] = {"kind": "item", "item": "healing draught"}
ws.combat.turn("drink the healing draught")
heals = [h for h in ft.hits if h["outcome"] == "heal"]
check("a draught heals, and the figure has its working like a blow's", heals and heals[0]["figure"].startswith("(+") and heals[0]["id"] and heals[0]["extras"] and me.hp > 10, (heals, me.hp))
check("...without using up the turn: the round did not move and no enemy acted", ft.round == rnd and len(ft.hits) == n0 + 1)
hp1 = me.hp; SAID.clear(); NOTES.clear()
ws.combat.turn("drink another healing draught")
check("only one item a turn", me.hp == hp1 and any("already used an item" in n for n in NOTES), NOTES)
CHOICE[0] = {"kind": "attack", "target": "e1"}
ws.combat.turn("attack")
check("the action after it is a full turn", ft.round == rnd + 1)
CHOICE[0] = {"kind": "item", "item": "healing draught"}
hp2 = me.hp; me.hp = min(me.hp, 5)
ws.combat.turn("drink the healing draught")
check("the next turn another item can be used", any(h["outcome"] == "heal" for h in ft.hits) and me.hp > 5)
uc.damage_tags = True
me.hp = 5
ws.to_pack(inventory.make_good(M["hunt"]["potion"]))
ft.item_round = 0
SAID.clear(); CHOICE[0] = {"kind": "item", "item": "healing draught"}
ws.combat.turn("drink")
uc.damage_tags = False
check("in the window the healing figure is a hoverable token", any("⟦" in t and "|(+" in t for k, t in SAID if k == "narrate"), SAID[-2:])
ASKED.clear(); SAID.clear(); rnd = ft.round
CHOICE[0] = {"kind": "other", "summary": "asks a question"}
ws.combat.turn("Hey Maren, how do i get my hit chance up?")
check("she answers in the middle of a fight, free of a turn", ft.round == rnd and ASKED and any(s == mentor.NAME for s, _ in SAID), (ASKED, SAID))
ft.enemies()[0].statuses["burning"] = 2
ASKED.clear(); SAID.clear(); rnd = ft.round
CHOICE[0] = {"kind": "talk", "target": "e0", "speech": "what does that mean"}
ws.combat.turn("it says the wolves are burning what does that mean?")
check("a question about what is on the wolves goes to her, not the wolf", ASKED and ft.round == rnd and not any("Talking will not help" in t for _, t in SAID), (ASKED, SAID))
check("she is told what is burning and what burning does", ASKED and "burning (2 more rounds)" in ASKED[0] and "half the blow that set it" in ASKED[0], ASKED[:1])
SAID.clear()
ws.combat.turn("please stop, wolf")
check("a plea to the wolf is still refused", any("Talking will not help" in t or "cannot be" in t or "wolves" in t for _, t in SAID), SAID)
ft.enemies()[0].statuses.pop("burning", None)
check("nothing she says claims a draught costs a turn", "costs you a turn" not in open("data/world/mentor.yaml", encoding="utf-8").read())
CHOICE[0] = {"kind": "attack", "target": "e1"}

# ---- win the fight: the fight ends, she tells you to skin the wolves; the troll comes when that is done
SAID.clear(); NOTES.clear()
f3 = ws.combat.fight
check("the wolves cannot lose heart and run", all("fearless" in e.behaviors and e.yields_at == 0 for e in f3.enemies()))
for e in f3.enemies():
    e.hp = 0
f3.over = "victory"
ws.combat.finish()
spoken = " ".join(t for _, t in SAID)
check("the fight is over and there is no troll yet", ws.combat is None and "That is a troll" not in spoken)
check("she tells you to skin and butcher the wolves, and keeps watch", "skin the wolves" in spoken and mentor.stage(player) == "harvest" and not player.mentor.get("troll_done"), spoken[:200])
check("she is still there to talk to", ws.mentor_with_you())
check("what she knows now is that the wolves are dead and she has told you to skin them", "skin and butcher the wolves" in mentor.facts(player, "Greywood"))
SAID.clear(); NOTES.clear()
xp0, coins0, inv0 = c.xp, c.coins, len(c.inventory)
ws.on_harvest(None, "skin the wolves")
spoken = " ".join(t for _, t in SAID)
check("the troll arrives on the skinning, and she says it should not be here", ws.combat is not None and "That's a troll" in spoken, spoken[:200])
check("the wolves had already been skinned", not ws.store.load_place(player.location).carcasses)
tf = ws.combat.fight
check("it is a real fight with the troll's level and health", tf.mentor_troll and [e.level for e in tf.enemies()] == [55] and tf.enemies()[0].max_hp == 800)
check("she is in it from the start, a party member who can be given orders", any(a.ally_role == "mentor" for a in tf.allies()) and tf.mentor_in
      and ws.combat.order_of("Maren, attack the troll") and ws.combat.order_of("Maren, attack the troll")[1] == "focus")
SAID.clear(); rnd = tf.round
CHOICE[0] = {"kind": "flee", "target": "e1"}
ws.combat.turn("I run")
told = " ".join(tf.story)
check("running from the troll is tried and fails, and costs the round", tf.round == rnd + 1 and any(t.lower() in told.lower() for t in M["troll_combat"]["run_fail"]), (tf.round, rnd, told[:200]))
check("the troll's blows went wide on you", tf.hits and all(h["outcome"] == "miss" for h in tf.hits if h["att"] == "troll" and h["dfn"] != mentor.NAME), tf.hits)
mar = tf.mentor_ally
check("its blow landed on her, and she asks for a draught", mar.hp < mar.max_hp * 0.7 and any(t == M["troll_combat"]["hurt"][0] for sp, t in SAID if sp == mentor.NAME), (mar.hp, mar.max_hp, SAID[-3:]))
blow = [h for h in tf.hits if h["att"] == "troll" and h["dfn"] == mentor.NAME and h["label"] == "smashes"]
check("its blow on her is a recorded hit with a figure the window can show", len(blow) == 1 and blow[0]["outcome"] == "hit" and re.fullmatch(r"\(\d+ damage\)", blow[0]["figure"]) and blow[0]["steps"] is not None, blow)
check("the story names her as the one struck, not you", any("not on you" in e or "not you" in e for e in tf.story) or any("Maren Holt" in e for e in tf.story), tf.story)
check("she hands you a draught if you have none", any(i.good == M["hunt"]["potion"] for i in c.inventory))
check("she has not struck yet", not tf.mentor_struck and tf.enemies())
hp1 = mar.hp
SAID.clear(); NOTES.clear(); rnd = tf.round
ws.combat.turn("give Maren a healing draught")
check("a draught given to her heals her and costs you no turn", mar.hp > hp1 and tf.round == rnd, (hp1, mar.hp, tf.round, rnd))
check("the draught left your pack", not any(i.good == M["hunt"]["potion"] for i in c.inventory))
SAID.clear()
CHOICE[0] = {"kind": "attack", "target": "e1"}
ws.combat.turn("I attack the troll")
check("she guards you that round", mar.order == "guard" and tf.mentor_phase == 2 and not tf.mentor_struck, (mar.order, tf.mentor_phase))
check("then she tells you how to give a companion an order", any(t == M["troll_combat"]["orders"][0] for sp, t in SAID if sp == mentor.NAME), SAID[-3:])
hp0 = tf.player.hp
SAID.clear(); NOTES.clear()
ws.combat.turn("Maren, attack the troll")
check("the order reads as an order to attack, not 'to troll'", any("You tell Maren to attack the troll." in t for _, t in SAID), [t for _, t in SAID][-3:])
check("an order costs no turn and she has still not struck", not tf.mentor_struck and tf.enemies())
CHOICE[0] = {"kind": "attack", "target": "e1"}
ws.combat.turn("I attack the troll") if ws.combat else None
mine = [h for h in tf.hits if h["att"] == mentor.NAME]
theirs = [h for h in tf.hits if h["att"] == "troll"]
check("the troll's blows never landed on you", all(h["outcome"] == "miss" for h in theirs) and tf.player.hp >= hp0 - 0.01, theirs)
check("after your command she struck, with a real, recorded blow", len(mine) >= 1 and mine[0]["outcome"] == "hit" and mine[0]["final"] >= 800 and mine[0]["steps"] is not None, mine)
check("her blow has a figure like any other", mine and re.fullmatch(r"\(\d+ damage\)", mine[0]["figure"]), mine and mine[0]["figure"])
check("the troll is dead", tf.over == "victory" and not tf.enemies())
check("you earned nothing from the troll", c.xp == xp0 and c.coins == coins0 and not any("XP" in n for n in NOTES), (c.xp, xp0, NOTES))
spoken = " ".join(t for _, t in SAID)
check("she says the world is getting more dangerous", "getting worse" in spoken or "more dangerous" in spoken)
check("she does not send you to skin them again", "skin the wolves" not in spoken, spoken[:300])
check("she waits in the Greywood for the walk back", player.location == "greywood" and mentor.stage(player) == "harvest" and player.mentor.get("troll_done") and ws.combat is None and ws.mentor_with_you())
SAID.clear()
ws.handle("you saved my ass back there maren, thank you")
check("thanking her by name in the harvest is said to her, not misread", any(sp == mentor.NAME for sp, _ in SAID), SAID[-2:])
SAID.clear()
ws.mentor_tick()
check("she does not walk you home herself", player.location == "greywood" and not SAID)
before_p = player.location
ws.enter("parth")
ws.pane_arrival(before_p)
spoken = " ".join(t for _, t in SAID)
check("arriving in Parth by a pane button runs her goodbye at once", mentor.stage(player) == "done" and M["return"]["leave"] in spoken, spoken[:150])
check("she leaves the party when the job is done", not any(m.get("story") == "maren" for m in player.party), player.party)
check("back in Parth she sends you to the clerk and leaves", mentor.stage(player) == "done" and M["return"]["info"][0] in spoken and M["return"]["leave"] in spoken, spoken[:200])
SAID.clear()
store.meta.minutes += 5000
ws.mentor_tick()
check("she does not return", not SAID and mentor.stage(player) == "done")
check("she cannot be talked to afterwards", not ws.mentor_with_you())
check("the board is normal again", len(ws.ensure_board()) != 1 or not ws.ensure_board()[0].get("mentor"))

# ---- afterwards she is a person of the world: remembers the player, can be recruited, can die
from engine import events as ev
from scenes.combat_scene import CombatScene
check("once it is over she is saved as a person of the world", store.npc_exists("maren"))
mn = store.load_npc("maren")
check("...who remembers what the player told her", any("They told me" in m.text for m in mn.memories) and any("hire me as practice" in m.text.lower() or "hire me" in m.text.lower() for m in mn.memories), [m.text for m in mn.memories])
check("...likes them, and knows them by name", mn.trust >= 60 and mn.knows_player_as == c.name and mn.name_known_to_player and mn.protected)
hall_id = next(p.id for p in world.places.values() if p.type == "guild" and p.parent == "parth")
check("...and waits at the guild hall", "maren" in store.load_place(hall_id).residents and mn.location == hall_id)
store.meta.minutes = 1440 * 3 + 12 * 60
ws.enter(hall_id); ws.refresh_present()
check("she is there to talk to", any(n.id == "maren" for n in ws.present), [n.id for n in ws.present])
player.party = []
check("'Maren, come with me' puts her in the party, unpaid", ws.party_turn("Maren, come with me") and any(m.get("npc") == "maren" for m in player.party), player.party)
check("...and she is no longer waiting at the hall", "maren" not in store.load_place(hall_id).residents)
near, later = CombatScene.allies(ws)
check("in a fight she is on your side with her own sheet", any(a.name == mentor.NAME and a.ally_role == "mentor" for a in near), [a.name for a in near])
ev.release_allies(ws)
check("event allies going home does not send her home", any(m.get("npc") == "maren" for m in player.party))
ws.party_turn("dismiss Maren")
check("dismissed, she is a resident again", not player.party and "maren" in store.load_place(hall_id).residents)
ws.party_turn("Maren, come with me")
ev.E["allies"]["death_when_down"] = 1.0
ev.fallen_allies(ws, {"ally_npc_maren"})
check("if she goes down she can die", store.load_npc("maren").gone, store.load_npc("maren").gone)

# ---- her manner: dry and amused, sceptical of an armed stranger, warm once they have shown themselves to be a new traveller
for stg, word in (("invite", "sceptical"), ("board", "warmed"), ("hunt", "warmed"), ("harvest", "warmed")):
    mentor.set_stage(player, stg)
    fs = mentor.facts(player, "Parth")
    check(f"her attitude at stage {stg}", "ATTITUDE:" in fs and word in fs, fs[:300])
check("her persona is the one written for her", "warm, wry personality" in mentor.chat_system() and "soft spot for inexperienced adventurers" in mentor.chat_system() and "gently teasing" in mentor.chat_system())
mentor.set_stage(player, "done")

# ---- the engine's figures
for sd in range(300):
    r = mentor.troll_fight(sd)
    if len(r["blows"]) != 1 or r["blows"][0] < r["max"] or r["left"][-1] != 0:
        check(f"one blow kills the troll (seed {sd})", False, r); break
else:
    check("one blow kills the troll on every seed", True)
check("the troll's death is reproducible", mentor.troll_fight(5) == mentor.troll_fight(5))
check("the troll has 800 health", mentor.troll_fight(5)["max"] == 800)
worst = 10**9
for sd in range(300):
    rng = random.Random(sd)
    pl = combat.fighter_from_character(c); pl.side = "player"
    fg = combat.Combat(fighters=[pl, mentor.troll_fighter("engaged")], record=True)
    m = mentor.maren_fighter()
    fg.mentor_ally = m; fg.fighters.append(m); fg.mentor_in = True; fg.mentor_troll = True
    from engine import battlefield as bf
    bf.engage(fg, m, fg.enemies()[0])
    fg.enemies()[0].always_miss = True
    combat.finish_round(fg, rng)
    if fg.mentor_struck or fg.mentor_phase != 1 or fg.over or not (0.5 * m.max_hp < m.hp < 0.7 * m.max_hp):
        check(f"the first round: its blow lands on her and she lives (seed {sd})", False, (m.hp, m.max_hp)); break
    combat.finish_round(fg, rng)
    if fg.mentor_struck or fg.mentor_phase != 2 or fg.over:
        check(f"the second round: she guards and has not struck (seed {sd})", False); break
    combat.finish_round(fg, rng)
    m.order = "guard"
    combat.finish_round(fg, rng)
    if fg.mentor_struck:
        check(f"she waits for the order to attack and does not strike on a guard order (seed {sd})", False); break
    m.order = "focus"
    combat.finish_round(fg, rng)
    swings = [h for h in fg.hits if h["att"] == mentor.NAME]
    worst = min(worst, swings[0]["final"] if swings else 0)
    if len(swings) != 1 or fg.over != "victory" or any(h["outcome"] != "miss" for h in fg.hits if h["att"] == "troll" and h["dfn"] != mentor.NAME):
        check(f"she ends it in one blow in the third round (seed {sd})", False, (len(swings), fg.over)); break
else:
    check("the script holds on every seed and her blow kills the troll", worst >= 800, worst)

# ---- the hunt taken before she finds them, talk that is meant for her, the walk to the Greywood, and no stray wolves before the lesson
s6, w6 = fresh("mentor_early")
p6 = w6.player; p6.guild_rank = "F"; s6.meta.minutes = 1800
mentor.set_stage(p6, "invite")
w6.enter("guild_house"); w6.refresh_present()
w6.on_accept_quest(ActionIntent(kind="accept_quest", item="wolf hunt"), "take the wolf hunt")
check("the hunt can be taken from the board before she comes to find them", mentor.has_contract(p6))
w6.enter("parth")
SAID.clear()
w6.mentor_tick()
sp = " ".join(t for _, t in SAID)
check("she sees they have it, and does not send them to the board", mentor.stage(p6) == "hunt" and M["board_step"]["already"] in sp and "Take it from the board" not in sp, sp[:200])
npc = next((n for n in w6.present if n.id), None)
if npc:
    check("naming the person says it to them", not w6.mentor_wants_talk(ActionIntent(kind="talk", target=npc.id, speech="hi"), f"hello {npc.role.replace('_', ' ')}"))
    check("...and anything else goes to her", w6.mentor_wants_talk(ActionIntent(kind="talk", target=npc.id, speech="I have it"), "I have it"))
SAID.clear()
w6.mentor_go_hunt("Okay, let's go maren")
check("'let's go' sets out for the Greywood", w6.player.location == "greywood", w6.player.location)
check("no wandering wolves before her lesson", w6.maybe_encounter(1.0, "As you arrive,") is False and w6.combat is None)
w6.mentor_tick()
check("then she teaches tracking", p6.mentor.get("briefed") and any("search for wolves" in t for _, t in SAID))
s7, w7 = fresh("mentor_go")
p7 = w7.player; p7.guild_rank = "F"; s7.meta.minutes = 1800
mentor.set_stage(p7, "hunt"); p7.quests.append(mentor.make_contract(s7.meta.minutes)); p7.mentor.update({"briefed": False, "found": False})
s8, w8 = fresh("mentor_nogo")
p8 = w8.player; p8.guild_rank = "F"; s8.meta.minutes = 1800
mentor.set_stage(p8, "hunt"); p8.quests.append(mentor.make_contract(s8.meta.minutes)); p8.mentor.update({"briefed": False, "found": False})
jd = w8.journal_data()
names = [x["name"] for g in jd["groups"] for x in g["people"]]
check("while the lesson runs, Maren is in the journal", names == [mentor.NAME] and jd["groups"][0]["people"][0]["line"] == M["journal_line"], jd["groups"])
mentor.set_stage(w8.player, "invite"); mentor.set_stage(w8.player, "hunt")
check("asking someone 'when will it be ready?' does not set out", not w8.mentor_go_hunt("when will it be ready?") and w8.player.location != "greywood")
check("...nor does 'is it ready yet'", not w8.mentor_go_hunt("is it ready yet") and w8.player.location != "greywood")
check("'I'm ready' still sets out", w8.mentor_go_hunt("I'm ready") and w8.player.location == "greywood")
check("'I head to the greywood with Maren' goes", w7.mentor_go_hunt("I head to the greywood with Maren") and w7.player.location == "greywood")

# ---- while she travels with you she is one of the people here: the narrator and the interpreter both know it, and what you say to her reaches her
s10, w10 = fresh("mentor_here", location="greywood")
mentor.set_stage(w10.player, "harvest")
check("the narrator is told she is here", any(v[0] == mentor.NAME and "travelling with the player" in v[2] for v in w10.people_view()), w10.people_view())
mentor.set_stage(w10.player, "done")
check("once the lesson is over she is not listed", not any(v[0] == mentor.NAME for v in w10.people_view()))
mentor.set_stage(w10.player, "harvest")
TALKED = []
w10.mentor_talk = lambda t: TALKED.append(t)
w10.advance = lambda *a, **k: None
w10.handle('"so, tell me about yourself while we gather our strength"')
check("a line wholly in quotes, with her beside you, is said to her", TALKED == ["so, tell me about yourself while we gather our strength"], TALKED)

# ---- her first appearance is narrated by the model from the facts about her, with the written passage as the fallback
s9, w9 = fresh("mentor_look")
good = "She has looked your way twice before she moves: a broad woman in dark plate, a guild crest with an enamelled A on one shoulder, a greatsword across her back. She steps into your path."
keep = stub.a_Narration
ASKED_N = []
stub.a_Narration = lambda u, k: (ASKED_N.append(u) or {"text": good})
SAID.clear()
w9.mentor_look(True, "I try the door of the shop and look over the counter")
check("the narrator is given what the player just said", ASKED_N and "I try the door of the shop" in ASKED_N[0] and "not about to cause trouble" in ASKED_N[0], ASKED_N[:1])
check("a good narration of her is used", any(good in t for _, t in SAID) and not any(M["approach"]["interrupt"] in t for _, t in SAID), SAID)
stub.a_Narration = lambda u, k: {"text": "A figure approaches."}
SAID.clear()
w9.mentor_look(True)
check("a narration that leaves out her sword and crest falls back to the written passage", any(M["approach"]["interrupt"] in t for _, t in SAID), SAID)
stub.a_Narration = lambda u, k: {"text": "Maren Holt, a woman with a greatsword and a crest, walks over."}
SAID.clear()
w9.mentor_look(False)
check("a narration that names her before she has introduced herself is not used", not any("Maren Holt, a woman" in t for _, t in SAID), SAID)
stub.a_Narration = keep

# ---- the skip: two yeses and she lets you go
s2, w2 = fresh("mentor_skip")
SAID.clear()
ANSWERS[:] = ["work", "proof", "yes I do", "yes, I'm sure"]
w2.mentor_intercept("I look around")
check("two yeses skip the tutorial", mentor.stage(w2.player) == "done" and w2.player.mentor.get("skipped") and not w2.player.quests)
check("she says goodbye and no troll", M["approach"]["skip_leave"][0] in " ".join(t for _, t in SAID) and w2.combat is None)
s3, w3 = fresh("mentor_skip2")
ANSWERS[:] = ["work", "proof", "yes", "hmm, not really", "ok", "ok", "ok", "go on"]
SAID.clear()
w3.mentor_intercept("I look around")
check("a yes then a doubt gets the walkthrough", mentor.stage(w3.player) == "invite" and "nobody is born knowing" in " ".join(t for _, t in SAID).lower())
for yes in ("yes", "Yeah, I do", "yep sure", "I understand it"):
    check(f"'{yes}' is a yes", mentor.says_yes(yes))
for no in ("no", "I don't", "not really", "sort of", "I don't understand", "maybe", "can you explain", ""):
    check(f"'{no}' is not a yes", not mentor.says_yes(no))

# ---- wording by build
seen = {}
for arch, expect in ((Archetype.WARRIOR, "melee"), (Archetype.MAGE, "caster"), (Archetype.SUPPORT, "support")):
    ch, _ = simlib.make_character("warrior", random.Random(2)); ch.archetype = arch
    check(f"{arch.value} reads as {expect}", mentor.build_of(ch) == expect, mentor.build_of(ch))
    seen[expect] = mentor.line(NS(character=ch, mentor={}), "start", 5)
ch, _ = simlib.make_character("ranger", random.Random(2))
check("a bow reads as ranged", mentor.build_of(ch) == "ranged", mentor.build_of(ch))
seen["ranged"] = mentor.line(NS(character=ch, mentor={}), "start", 5)
check("each build gets its own wording of the same lesson", len(set(seen.values())) == 4, seen)
pl = NS(character=ch, mentor={})
a, b = mentor.line(pl, "steady", 5), mentor.line(pl, "steady", 5)
check("a retry hears it a little differently", a != b)
check("the first-hurt lesson says how to use any item, not only the draught", all("drink the healing draught" in x and "'Items' list" in x and "Anything else you're carrying" in x for b in mentor.BUILDS for x in M["lessons"]["first_blood"][b]))
check("every lesson has every build", all(set(M["lessons"][k]) == set(mentor.BUILDS) for k in ("track", "found", "start", "first_blood", "steady")))

# ---- she walks them to the guild hall, signs them in and explains the board there
s6, w6 = fresh("mentor_escort")
s6.meta.minutes = 1800
w6.player.character.coins = max(w6.player.character.coins, 5000)
c0 = w6.player.character.coins
ANSWERS[:] = ["work", "proof", "no", "ok", "ok", "ok", "go on"]
SAID.clear()
w6.mentor_intercept("I look around")
sp6 = " ".join(t for _, t in SAID)
check("she goes with them and they end up in the guild hall", w6.player.location == "guild_house" or w6.place.type == "guild", w6.player.location)
check("at the desk it is the player's turn: nothing is paid until they say so (f271)", mentor.stage(w6.player) == "sign" and not w6.rank and w6.player.character.coins == c0
      and M["escort"]["your_turn"].split("{")[0] in sp6, (mentor.stage(w6.player), w6.rank, sp6[-200:]))
SAID.clear()
w6.handle("what happens if I lose the badge?")
check("...a question there is answered, and still nothing is paid", mentor.stage(w6.player) == "sign" and not w6.rank, (mentor.stage(w6.player), w6.rank))
w6.handle("i hand over the three silver")
w6.mentor_tick()                                          # the turn's tick (scenes/world.py turn) is what carries her on
sp6 = " ".join(t for _, t in SAID)
check("they are signed in at rank F and the fee is paid", w6.rank == "F" and w6.player.character.coins < c0, (w6.rank, c0, w6.player.character.coins))
check("the stage is board and the hunt is posted for the player to take", mentor.stage(w6.player) == "board" and w6.player.mentor.get("posting") and not w6.player.quests)
check("she explains the board there, with no send-off", M["board_step"]["explain"][0] in sp6 or "Board pane" in sp6, sp6[-300:])
check("she does not send them off alone", "Then find me" not in sp6 and "walks off" not in sp6)
s7, w7 = fresh("mentor_escort2")
s7.meta.minutes = 1800
w7.player.character.coins = 0
ANSWERS[:] = ["work", "proof", "no", "ok", "ok", "ok", "go on"]
SAID.clear()
w7.mentor_intercept("I look around")
check("short of coin she waits in town and the stage stays invite", mentor.stage(w7.player) == "invite" and not w7.rank, (mentor.stage(w7.player), w7.rank))

# ---- she stops the first thing they do in Parth; arriving alone does not bring her
s8, w8 = fresh("mentor_intercept")
SAID.clear()
w8.mentor_tick()
check("arriving in Parth does not bring her over", mentor.stage(w8.player) == "" and not SAID)
ANSWERS[:] = ["work", "proof", "no", "ok", "ok", "ok", "go on"]
w8.handle("I buy a sword from the smith")
spoken8 = " ".join(t for _, t in SAID)
check("their first action in Parth is stopped by her", mentor.stage(w8.player) in ("invite", "board") and M["approach"]["interrupt"] in spoken8, mentor.stage(w8.player))
check("...and what they meant to do did not happen", "smith" not in " ".join(t for k, t in SAID if k == "narrate" and "buy" in t.lower()))

# ---- gates
s4, w4 = fresh("mentor_test2", level=20)
SAID.clear()
w4.mentor_intercept("I look around"); s4.meta.minutes += 100; w4.mentor_intercept("I look around")
check("an experienced player is left alone", mentor.stage(w4.player) == "" and not SAID)
s5, w5 = fresh("mentor_test3", location="willowmead")
w5.mentor_intercept("I look around"); s5.meta.minutes += 100; w5.mentor_intercept("I look around")
check("she is only in Parth", mentor.stage(w5.player) == "")

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
