"""(f739) A trial of rank begins only for a member the register says has earned it, and a question about rank is answered. Whatever
line or caller reaches the start of a trial (scenes/trial_actions.py trial_start), a member not due is given the register's line:
no duel, no examiner faced, no try counted and no wait set. One who is due is told so when they ask and steps into the ring when they
stand. CPU only, simlib's stub."""
import shutil
import sys

sys.path.insert(0, ".")
import simlib

STUB = simlib.Stub("warrior", 5)
simlib.install(STUB)
SHOWN = simlib.quiet_console()
from core.models import Passive, PowerTier
from engine import quests

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


def stand(ws, rank: str, level: int, done: dict) -> None:
    """The member as the case wants them, out of any fight, with no trial begun or waited on."""
    ws.combat = None
    ws.store.save_combat(None)
    ws.player.guild_rank, ws.player.guild_done = rank, dict(done)
    ws.player.character.level = level
    ws.player.trial.clear()
    ws.store.save_player(ws.player)


def said(ws, text: str) -> list[str]:
    """The line through the game's own way in; the notes it showed."""
    SHOWN.clear()
    ws.turn(text)
    return [t for k, t in SHOWN if k == "note"]


def untouched(ws) -> bool:
    """No duel and nothing of one: no rank pending, no try counted, no wait set, in the scene or the save."""
    saved = ws.store.load_player().trial
    return (ws.combat is None and all(k not in t for t in (ws.player.trial, saved) for k in ("pending", "examiner", "wait_until"))
            and not ws.player.trial.get("tries") and not saved.get("tries"))


NAME = "trial_earned_test"
g = simlib.campaign(NAME, seed=3, minutes=600, location="guild_house")
try:
    ws = g.scene
    check("the case stands at a guild hall", ws.place.type == "guild", ws.place.type)

    # ---- the case that found it: rank F, level 1, no contracts, asking
    stand(ws, "F", 1, {})
    check("rank F at level 1 with no contracts is not due", ws.trial_due() is None, ws.trial_due())
    for line in ("What do I need for the next rank?", "How do I rank up?", "When can I take the rank test?"):
        stand(ws, "F", 1, {})
        notes = said(ws, line)
        check(f"'{line}' from a member not due is answered with what the register asks, and no duel",
              untouched(ws) and any("not ready to stand for rank E" in n and "level 10 (you are 1)" in n and "(you have 0)" in n for n in notes),
              (ws.combat is not None, dict(ws.player.trial), notes[:2]))
        check(f"...and the rank stays F after '{line}'", ws.player.guild_rank == "F" and ws.store.load_player().guild_rank == "F")

    # ---- the second case: the level, not the contracts
    for line in ("How do I rank up?", "When can I take the rank test?", "Can I take the test for the next rank?"):
        stand(ws, "F", 10, {"F": 1})
        notes = said(ws, line)
        check(f"'{line}' with the level and one contract of four gets the register's line, no fight, no wait",
              untouched(ws) and any("not ready to stand for rank E" in n and "(you have 1)" in n for n in notes),
              (ws.combat is not None, dict(ws.player.trial), notes[:2]))
    stand(ws, "F", 10, {"F": 1})
    notes = said(ws, "I'd like to take the trial")
    check("standing for it without the contracts is refused the same way", untouched(ws) and any("not ready" in n for n in notes),
          (ws.combat is not None, notes[:2]))

    # ---- the seam: a caller that asks for a trial the register has not earned
    stand(ws, "F", 10, {"F": 1})
    SHOWN.clear()
    began = ws.trial_start("E")
    notes = [t for k, t in SHOWN if k == "note"]
    check("trial_start for a rank not due is refused: nothing pending, no try counted, no examiner",
          not began and untouched(ws) and any("not ready to stand for rank E" in n for n in notes), (began, dict(ws.player.trial), notes[:2]))
    stand(ws, "F", 10, {"F": 5})
    SHOWN.clear()
    began = ws.trial_start("D")
    notes = [t for k, t in SHOWN if k == "note"]
    check("trial_start for a rank other than the one due is refused too, with where the member stands",
          not began and untouched(ws) and any("earned rank E on paper" in n for n in notes), (began, dict(ws.player.trial), notes[:2]))
    stand(ws, "S", 160, {"S": 20})
    SHOWN.clear()
    began = ws.trial_start("S")
    notes = [t for k, t in SHOWN if k == "note"]
    check("and for a member at the top rank", not began and untouched(ws) and any("highest rank, S" in n for n in notes), (began, notes[:2]))

    # ---- the register is the acting character's, with the perk's discount
    stand(ws, "F", 10, {"F": 3})
    check("one contract short, promotion_due alone would refuse", quests.promotion_due("F", 10, {"F": 3}) is None)
    c = ws.player.character
    kept = list(c.passives)
    c.passives.append(Passive(id="btr", name="Born to Rank", description="d", tier=PowerTier.LIGHT, mechanic="born_to_rank", value=0))
    check("...but Born to Rank's one fewer contract makes the rank due", ws.trial_due() == "E", ws.trial_due())
    notes = said(ws, "I'd like to take the trial")
    check("...and the trial begins for them", ws.combat is not None and ws.player.trial.get("pending") == "E", (dict(ws.player.trial), notes[:2]))
    c.passives = kept
    stand(ws, "F", 1, {})
    other = ws.player.model_copy(deep=True)
    other.guild_rank, other.guild_done = "F", {"F": 9}
    other.character.level = 30
    real = ws.player_of
    ws.player_of = lambda who: other if who == ws.acting else real(who)
    try:
        check("the register reads the acting character's record (player_of), not the scene's own", ws.trial_due() == "E", ws.trial_due())
        began = ws.trial_start("E")
        check("...and the seam begins the trial on that record", began and other.trial.get("pending") == "E" and "pending" not in ws.player.trial,
              (began, dict(other.trial), dict(ws.player.trial)))
    finally:
        del ws.player_of

    # ---- the pins that must not move: the earned question is told, the earned request fights, a win gives the rank
    stand(ws, "F", 10, {"F": 5})
    notes = said(ws, "What do I need for the next rank?")
    check("a member who is due and asks is told the rank is earned on paper, and nothing starts",
          untouched(ws) and any("earned rank E on paper" in n for n in notes), notes[:2])
    stand(ws, "F", 10, {"F": 5})
    notes = said(ws, "I'd like to take the trial")
    t = ws.player.trial
    check("a member who is due and stands steps into the ring", ws.combat is not None and t.get("pending") == "E" and t.get("tries") == 1,
          (dict(t), notes[:2]))
    if ws.combat is not None:
        ws.trial_over(True, ws.combat.fight)
    check("...and a win gives the rank", ws.player.guild_rank == "E", ws.player.guild_rank)
    stand(ws, "F", 10, {"F": 5})
    ws.player.trial["wait_until"] = ws.minutes + 600
    ws.store.save_player(ws.player)
    notes = said(ws, "I'd like to take the trial")
    check("a member due but waiting after a loss is still told to come back",
          ws.combat is None and any("Come back in" in n for n in notes), notes[:2])
finally:
    try:
        g.close()
    except Exception as e:
        print("close:", e)
    shutil.rmtree(f"saves/{NAME}", ignore_errors=True)

# ---- a second member and a line meant for someone else: a rank-E mage asks a teacher for the next rank of their spells
NAME2 = "trial_earned_test_mage"
g = simlib.campaign(NAME2, cls="mage", seed=7, minutes=600, location="guild_house")
try:
    ws = g.scene
    stand(ws, "E", 12, {"E": 0})
    check("a rank-E mage at level 12 is not due for D", ws.trial_due() is None, ws.trial_due())
    notes = said(ws, "Can you teach me the next rank of my spells?")
    check("the teacher's line puts nobody in a trial", untouched(ws) and ws.player.guild_rank == "E",
          (ws.combat is not None, dict(ws.player.trial), notes[:2]))
finally:
    try:
        g.close()
    except Exception as e:
        print("close:", e)
    shutil.rmtree(f"saves/{NAME2}", ignore_errors=True)

print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)
