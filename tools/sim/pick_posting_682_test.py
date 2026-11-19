"""(f682) A contract asked for by its words is that contract or none, never another one picked by a number in its title (found in
the second blind play: docs/play/2026-11-16_blind_play_journal.md). `I take the contract to hunt 2 giant crabs in the Shipwreck
Shoals.` took "Hunt 3 sahuagins in the Tidepool Caves", said nothing of it: the crab posting had left the board, only "hunt" matched
anything, and the "2" of the asked title was read as the board's second posting.
Held here: words that name a posting take it (several words, or one word with nothing else named); words that name a posting not on
the board take none; a bare number ("take 2", "the second one" is not numbers) still picks by position.
Run: python tools/sim/pick_posting_682_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("pick_posting_682_test", seed=3, minutes=900)
ws = g.scene
board = [{"title": "Gather 5 yarrow"}, {"title": "Hunt 3 sahuagins in the Tidepool Caves"}, {"title": "Hunt 4 ogres in the badlands"},
         {"title": "Clear floor 1 of the Rat-King's Stronghold"}]
pick = lambda words: (ws.pick_posting(board, words) or {}).get("title")
check("a posting not on the board is none, though its title has a number",
      pick("hunt 2 giant crabs in the shipwreck shoals I take the contract to hunt 2 giant crabs in the Shipwreck Shoals.") is None,
      pick("hunt 2 giant crabs in the shipwreck shoals"))
check("words naming a posting take it", pick("hunt 4 ogres in the badlands") == "Hunt 4 ogres in the badlands")
check("one word with nothing else named takes it", pick("the ogres one") == "Hunt 4 ogres in the badlands", pick("the ogres one"))
check("the stronghold by its name", pick("I take the contract to clear the stronghold floor") == "Clear floor 1 of the Rat-King's Stronghold",
      pick("I take the contract to clear the stronghold floor"))
check("a word as one of its kind names it: 'the wolf contract' is 'Hunt 3 wolves'",
      ws.pick_posting([{"title": "Hunt 3 wolves in the Greywood"}], "wolves I give up the wolf contract.") is not None)
check("a bare number still picks by position", pick("2 take 2") == "Hunt 3 sahuagins in the Tidepool Caves", pick("2 take 2"))
import shutil; shutil.rmtree("saves/pick_posting_682_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
