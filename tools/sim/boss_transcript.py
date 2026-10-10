"""A full boss fight through the real combat scene, with every prompt the narrator would receive written to a transcript.
The model is the scripted stand-in (no Ollama here), so the narration lines are the events as sent; what this proves is what the real
model would be GIVEN, and that every set-piece beat reaches it.  Usage: python3 tools/sim/boss_transcript.py [seed] [out.md]"""
import sys, random, shutil, json, re, types
sys.path.insert(0, ".")
import simlib
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 3
OUT = sys.argv[2] if len(sys.argv) > 2 else "boss_transcript.md"
stub = simlib.Stub("warrior", SEED)
simlib.install(stub)
import config
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from engine import items, pulse, events, combat, bosses
from scenes.combat_scene import CombatScene
from scenes import combat_prompts as cp
from ui import console

shutil.rmtree("saves/boss_transcript", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("boss_transcript")
store.meta.seed = SEED; store.meta.minutes = 400 * 1440; store.save_meta()
rng = random.Random(SEED)
char, _ = simlib.make_character("warrior", rng)
char.level = 60
store.save_player(PlayerState(character=char, location="parth"))
catalog = load_traits()
ws = WorldScene(store, world, catalog, store.load_player())
t = 400 * 1440
state = pulse.empty_state(t); store.save_world_state(state)

# ---- a real campaign, started through the pipeline, until its boss is in the world
out = []
def w(s=""): out.append(s)
ok = pulse.start_thread(store, world, catalog, state, t, rng, tier="campaign", pressure_id="ironvein_deeps")
th = next(x for x in state["threads"] if x["tier"] == "campaign")
tt = t
for _ in range(400):
    if any(s["boss"] and s.get("tier") == "campaign" for s in state.get("spawns", [])): break
    tt += pulse.INTERVAL; state["last"] = tt
    pulse.tick_threads(store, world, catalog, state, tt, rng)
spawn = next((s for s in state.get("spawns", []) if s["boss"] and s.get("tier") == "campaign"), None)
assert spawn, "no campaign boss spawned"
store.meta.minutes = tt; store.save_meta()
store.save_world_state(state)
creature, foes = events.spawn_fighters(world, spawn, rng, char.level)
boss = foes[0]

# ---- record every model call; the stand-in narrates by echoing the events
calls = []
real_chat = stub.chat
def chat(**k):
    msgs = k["messages"]; title = k["format"].get("title", "?")
    r = real_chat(**k)
    calls.append((title, msgs[0]["content"], msgs[-1]["content"], json.loads(r.message.content)))
    return r
stub.chat = chat; simlib.install(stub)
class FakeBot:
    def combat_choice(self):
        f = ws.combat.fight; e = f.enemies()
        mv = [m for m in f.player.moves if m.effect == "damage" and not combat.can_use(f.player, m, f)]
        if mv: return {"kind": "ability", "ability": mv[0].id, "target": e[0].id if e else "", "move": "closer", "summary": "strike"}
        return {"kind": "attack", "target": e[0].id if e else "", "move": "closer", "summary": "strike"}
stub.bot = FakeBot()
orig_narr = stub.a_Narration
def narr(u, k):
    if "EVENTS:" in u:
        ev = u.split("EVENTS:\n", 1)[1]
        return {"text": f"(stand-in: {len(ev.splitlines())} events, no prose written)"}
    return {"text": "(stand-in: no prose written)"}
stub.a_Narration = narr

console_lines = []
for name in ("narrate", "note", "combat_panel", "combat_numbers"):
    if hasattr(console, name):
        setattr(console, name, (lambda n: (lambda *a, **kw: console_lines.append((n, a))))(name))

# ---- the fight. The player is made hardy enough to see every beat (this tests prompts, not balance).
ws.combat = CombatScene.begin(ws, creature, foes, "You find the one the whole valley fears:")
f = ws.combat.fight
p = f.player
p.max_hp = p.hp = p.max_hp * 60
p.weapon_damage *= 12
c0 = (char.coins, [i.uid for i in char.inventory], char.xp if hasattr(char, "xp") else 0, char.level)
rounds = 0
beats = []
while ws.combat and rounds < 60:
    rounds += 1
    ws.handle("I press the attack and watch for its next move.")
    for s in f.story if ws.combat else []:
        pass
over = f.over

# ---- the transcript
w(f"# Boss fight transcript - {creature.name}, campaign boss (seed {SEED})\n")
w("The model here is the scripted stand-in, so it writes no prose; each block shows what it was SENT. "
  "Everything above it in each block is exactly what gemma would receive. The player is buffed (60x health, 12x weapon damage) so the "
  "fight lasts long enough to show every beat; this tests prompts, not balance.\n")
w("## The story that led here\n")
w(f"**{th['title']}**  \n{th['stages'][0]['description']}\n")
w("Boss lines written by the model for this story (stored on the spawn):\n")
for k, v in (spawn.get("lines") or {}).items(): w(f"- {k}: {v}")
w(f"\nBoss: {boss.name}, level {boss.level}, {boss.max_hp} health, kit `{boss.boss.get('kit') if boss.boss else None}`, tier `{boss.boss.get('tier') if boss.boss else None}`.\n")
w("## System prompts used in combat\n")
seen_sys = {}
for title, system, user, res in calls:
    if title in ("Narration",) and system not in seen_sys: seen_sys[system] = title
for system in seen_sys:
    w("```\n" + system + "\n```\n")
n = 0
for title, system, user, res in calls:
    if title != "Narration": continue
    n += 1
    w(f"## Narration call {n}\n")
    w("Sent to the model:\n\n```\n" + user + "\n```\n")
    w("The stand-in answered:\n\n> " + res["text"].replace("\n", "\n> ") + "\n")
c = ws.player.character
w("## Rewards\n")
w(f"- coins: {c0[0]} -> {c.coins}")
w(f"- level: {c0[3]} -> {c.level}" + (f", xp: {c0[2]} -> {c.xp}" if hasattr(c, 'xp') else ""))
for i in c.inventory:
    if i.uid not in c0[1]: w(f"- item: {i.name} ({i.rarity}{', ' + i.good if i.good else ''})" + ("" if i.good else f" - {items.summary(i)}"))
for kind, a in console_lines:
    if kind == "note" or kind == "narrate": continue
w("- on-screen messages after the fight: " + " | ".join(str(a[0])[:200] for kind, a in console_lines if kind == "note" and a)[:1500])
st = store.load_world_state()
w(f"- event spawn defeated: {next((x['defeated'] for x in st['spawns'] if x['id'] == spawn['id']), None)}; thread status: {next((x['status'] for x in st['threads'] if x['id'] == th['id']), None)}")
w("")
w(f"## Result\n\nFight ended: **{over}** after {rounds} rounds. Boss final state: {boss.boss}\n")

# ---- prompt checks
allreq = "\n".join(u for ti, s, u, r in calls if ti == "Narration")
allsys = "\n".join(s for ti, s, u, r in calls if ti == "Narration")
checks = []
def chk(name, ok, extra=""): checks.append((name, bool(ok), extra))
lines = spawn.get("lines") or {}
chk("the narrator's rules explain the BOSS beats", "BOSS ENTRANCE" in allsys and "BOSS LAST STAND" in allsys)
chk("opening request carries the entrance and the speech", "BOSS ENTRANCE" in allreq and lines.get("intro", "?")[:30] in allreq)
for tag, key in (("BOSS TURNING POINT", "bloodied"), ("BOSS LAST STAND", "last_stand"), ("BOSS FALLS", "fall")):
    chk(f"{tag} reaches the narrator with its line", tag in allreq and lines.get(key, "?")[:25] in allreq, f"line: {lines.get(key, '')[:40]}")
chk("legendary actions reach the narrator", "BOSS ACTS BETWEEN TURNS" in allreq)
chk("signature move reaches the narrator", "BOSS SIGNATURE MOVE" in allreq)
events_text = "\n".join(l for l in allreq.splitlines() if l.strip().startswith("- BOSS"))
chk("no game words or numbers in boss events", not re.search(r"legendary|phase|\bround|\d", events_text), events_text[:120] if re.search(r"legendary|phase|\bround|\d", events_text) else "")
biggest = max((len(s) + len(u)) for ti, s, u, r in calls if ti == "Narration")
chk("largest narration prompt fits the context window", biggest / 3.5 < config.NUM_CTX * 0.5, f"{biggest} chars ~ {round(biggest / 3.5)} tokens of {config.NUM_CTX}")
w("## Prompt checks\n")
for name, ok, extra in checks: w(f"- {'PASS' if ok else 'FAIL'}: {name}" + (f" ({extra})" if extra else ""))
open(OUT, "w", encoding="utf-8").write("\n".join(out))
for name, ok, extra in checks: print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
print("fight:", over, rounds, "rounds; transcript ->", OUT)
