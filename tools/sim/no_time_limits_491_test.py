"""(f491) No contract or request has a time limit (the owner, 2026-11-03: "let's get rid of quest time restrictions"). A posting, a
contract taken from the board, a personal request and an arc's contract carry no deadline; months pass and each is still in hand; a
contract an older save gave a deadline that has passed is still held, never forfeit; nothing the player reads tells time left (the
board, #quests, the pane's rows, the request's line, an arc's line); the guild's ranks give no days; and no play code reads a
quest's deadline again."""
import re
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import yaml
from engine import money, quests

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

game = simlib.campaign("no_time_limits_491")
ws = game.scene
gid = next(p.id for p in ws.world.places.values() if p.type == "guild")
shown = simlib.quiet_console()
ws.enter(gid)
if ws.clerk_here() is None and ws.present:
    ws.present[-1].role = "guild_clerk"                        # the stand-in town has no clerk on shift: one of the contractors keeps the board
ws.player.character.level = 3
ws.player.character.coins = money.to_smallest(gold=50)
ws.player.guild_rank = "F"                                    # a member (joining is board_click_test's)
board = ws.ensure_board()
check("no posting on the board has a deadline", board and not any("deadline" in q or "extra_days" in q for q in board), [sorted(q) for q in board[:1]])
d = ws.board_data()
check("...and the board says none: no days, no 'time limit'", d["postings"] and not any("limit" in p for p in d["postings"]), d["postings"][:1])
shown.clear()
ws.show_board()
check("...in its listing either", shown and not any(re.search(r"\d+ days\b|time limit", t) for _, t in shown if "expedition" not in t), shown[:4])

take = next(p for p in d["postings"] if p["ok"])
ws.board_click(f"#boardaccept {take['id']}")
q = next((x for x in ws.player.quests if x["id"] == take["id"]), None)
check("a contract taken from the board carries no deadline", q is not None and "deadline" not in q, q)

# a request from a townsperson, and a contract an older save gave a deadline that has passed
npc = next(iter(ws.present), None)
offer = quests._quest("hunt", "F", "Wolves at the fold", ws.minutes, guild=False, issuer=npc.id if npc else "x", issuer_name=npc.name if npc else "X",
                      place=gid, creature="wolf", count=2)
if npc is not None:
    simlib.offer(ws.store, npc.id, "request", dict(offer))      # (f481)
    shown.clear()
    ws.take_personal(npc)
    line = " ".join(t for k, t in shown if k == "ledger")
    req = next((x for x in ws.player.quests if x["title"] == "Wolves at the fold"), None)
    check("a request taken carries no deadline, and its line gives no days", req is not None and "deadline" not in req
          and "Request taken:" in line and not re.search(r"Due in|time limit", line), (req, line))
old = {"id": "oldq1", "letter": "F", "title": "The old bounty", "kind": "hunt", "count": 2, "progress": 0, "guild": True, "issuer": "guild",
       "issuer_name": "the guild", "coins": 10, "xp": 5, "posted": ws.minutes - 9000, "deadline": ws.minutes - 10, "creature": "wolf", "place": gid}
ws.player.quests.append(old)
ws.store.save_player(ws.player)
held = len(ws.player.quests)

# months pass, and a line is played: nothing expires
ws.store.meta.minutes += 120 * 1440
ws.store.save_meta()
shown.clear()
ws.handle("I wait a while.")
check("four months on and a line played, every contract is still in hand", len(ws.player.quests) == held
      and any(x["id"] == "oldq1" for x in ws.player.quests), [x["title"] for x in ws.player.quests])
check("...and nothing was said to have expired or been forfeit", not any(re.search(r"expired|forfeit", t, re.I) for _, t in shown), shown[-4:])
check("the scene has no expiry left to run", not hasattr(ws, "expire_quests"))
rows = ws.quest_rows()
check("the pane's rows tell how far along, never how long is left", rows and not any(k in r for r in rows for k in ("left", "urgent")), rows[:1])
lines = [quests.progress_line(x, ws.pack, ws.minutes) for x in ws.player.quests]
check("#quests lines tell no time", lines and not any(re.search(r"left|expired|time limit", l) for l in lines), lines)

# the data and the code
G = yaml.safe_load(Path("data/rules/guild.yaml").read_text(encoding="utf-8"))
check("the guild's ranks give no days to finish a contract", not any("deadline_days" in (r or {}) for r in G["ranks"].values()), G["ranks"]["F"])
src = {f: Path(f).read_text(encoding="utf-8") for f in ("engine/quests.py", "scenes/guild_actions.py", "scenes/world.py", "scenes/arc_actions.py",
                                                         "engine/mentor.py", "tools/nightbot.py", "ui/gui/web/app.js")}
reads = [f for f, s in src.items() if re.search(r"""q(?:uest)?(?:\.get\()?\[?["']deadline["']|deadline_days|extra_days|expire_quests|q\.urgent|q\.left|q\.limit""", s)]
check("no play code reads a quest's deadline, its days or its expiry again", not reads, reads)

game.close()
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
