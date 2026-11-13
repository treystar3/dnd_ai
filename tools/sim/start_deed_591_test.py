"""(f591) The start's deed is numbered like any other (the owner, 2026-11-10: "as its own feature"). A starting point whose past holds a
situation the character settled writes its 'settled' deed through deeds.add, as every other deed is written: it takes the world's next
number, the count is ticked, it names the character whose deed it was, and it is kept within the deeds' cap.
Run: python tools/sim/start_deed_591_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import deeds, starts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def begin(name: str, before: dict | None = None):
    g = simlib.campaign(f"start_deed_591_{name}", seed=7, minutes=8 * 60, char_seed=2)
    store, player = g.store, g.player
    player.character.name, player.guild_rank = "Tam Reed", "B"
    store.save_player(player)
    if before is not None:
        store.save_world_state(before)
    starts.apply(store, g.session.world, g.catalog, player, "veteran", random.Random(3), "Tam Reed")
    return store, player


store, player = begin("veteran")
st = store.load_world_state()
settled = [d for d in st.get("deeds", []) if d["kind"] == "settled"]
check("the veteran's settled situations are deeds, as before", len(settled) == 2, settled)
check("...each numbered, in order, and the world's count ticked to the last", [d.get("seq") for d in settled] == sorted(d.get("seq") for d in settled)
      and all(isinstance(d.get("seq"), int) for d in settled) and st.get("seq") == max(d["seq"] for d in st["deeds"]), (settled, st.get("seq")))
check("...each naming whose deed it was", all(d.get("by") == player.character.id for d in settled), [d.get("by") for d in settled])
check("...with what it was, as before", all(d.get("thread") and d.get("title") and d.get("tier") and d.get("how") == "by the stranger's hand"
                                            and d.get("place") and isinstance(d.get("minute"), int) for d in settled), settled)

full = {"seq": 1000, "deeds": [{"kind": "found", "minute": i, "place": "x", "seq": i + 1} for i in range(deeds.KEEP)]}
store, player = begin("full", before=full)
st = store.load_world_state()
check("a start on a world whose deeds are at their cap keeps them at it, the oldest out", len(st["deeds"]) == deeds.KEEP
      and st["deeds"][-1]["kind"] == "settled" and st["deeds"][0]["seq"] > 1, (len(st["deeds"]), st["deeds"][0]))
check("...and numbers on from the world's own count", st["deeds"][-1]["seq"] == st["seq"] > 1000, (st["deeds"][-1].get("seq"), st.get("seq")))
src = open("engine/starts.py", encoding="utf-8").read()
check("the start writes no deed by hand", 'setdefault("deeds"' not in src and '["deeds"].append' not in src)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
