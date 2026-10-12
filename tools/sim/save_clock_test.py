"""The game clock and turn count survive a save and reload (loading a save must not replay the waking scene)."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from storage.campaign import CampaignStore, PlayerState
shutil.rmtree("saves/save_clock_test", ignore_errors=True)
store = CampaignStore.open_or_create("save_clock_test")
char, _ = simlib.make_character("warrior", random.Random(1))
player = PlayerState(character=char, location="parth")
store.meta.minutes, store.meta.turn = 1234, 9
store.save_player(player)
again = CampaignStore.open_or_create("save_clock_test")
ok = again.meta.minutes == 1234 and again.meta.turn == 9
print(("PASS" if ok else "FAIL") + " clock and turn persist", again.meta.minutes, again.meta.turn)
sys.exit(0 if ok else 1)
