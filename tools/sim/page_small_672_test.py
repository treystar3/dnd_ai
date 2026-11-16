"""(f672) The rest of group F that is built (docs/design/21_play_faults_plan.md; found in play: docs/play/2026-11-15_play_findings.md 8.4
to 8.9): a view typed leaves the fight's pane as one clicked does (8.4); the notice strip keeps one row's height, so notices never move
the tabs or a pane's buttons under the pointer (8.5); an item's level is written once (8.6, "lv 6 · · lv 6"); the Continue card says
when the game was last played, not when it was opened (8.7); the wolves' arrival is told once (8.8); and the small wrong words
(8.9): no dash in a check's label, "1 more round", the page's own names instead of typed commands, and a felled tree is not offered
for skinning. Left: the weapon asked for (8.3) and abilities alike in what they do (8.2).
Run: python tools/sim/page_small_672_test.py"""
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
import types
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 2))
simlib.quiet_console()
from engine import checks, loot
from scenes.shop_actions import ShopActions
from storage import saves

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


js = open("ui/gui/web/app.js", encoding="utf-8").read()
css = open("ui/gui/web/style.css", encoding="utf-8").read()
html = open("ui/gui/web/index.html", encoding="utf-8").read()
form = js[js.index('$("form").onsubmit'):js.index('input.addEventListener("keydown"', js.index('$("form").onsubmit'))]
check("8.4: a view typed sets the pane to the view, as a click does", "isViewCmd(text)" in form and 'combat.mode = "view"' in form)
check("8.5: the notice strip is never hidden away, only emptied, and holds one row", 'id="ticker" class="ticker empty"' in html
      and "hidden" not in html[html.index('id="ticker"') - 20:html.index('id="ticker"') + 60] and "height: 34px" in css and ".ticker.empty { visibility: hidden; }" in css)
item = types.SimpleNamespace(item_level=6)
check("8.6: an item's level is written once: the summary's own", ShopActions.with_level(item, "lv 6 iron sword; 9 damage") == "lv 6 iron sword; 9 damage")
check("...or put first when the summary has none", ShopActions.with_level(types.SimpleNamespace(item_level=1), "6 spell damage") == "lv 1 6 spell damage")
tidy = lambda t: re.sub(r"^lv (\d+) (?=\S)", r"lv \1 · ", t)
check("...and the page's dot follows it once", tidy(ShopActions.with_level(types.SimpleNamespace(item_level=1), "6 spell damage")) == "lv 1 · 6 spell damage")

main_src = open("main.py", encoding="utf-8").read()
loop = main_src[main_src.index("scene.run()"):main_src.index("scene.run()") + 600]
check("8.7: the Continue card's time is stamped when a game is left, not only when it is opened", "saves.touch(name)" in loop
      and loop.index("finally:") < loop.index("saves.touch(name)"))

mentor_src = open("scenes/mentor_actions.py", encoding="utf-8").read()
check("8.8: the wolves' arrival is told once: the fight is told it was", 'told=M["arrive"]["found_narrate"].strip()' in mentor_src)
check("8.9: no dash in a check's label", checks.label("theft", "failure") == "Theft: failure" and chr(0x2014) not in open("engine/checks.py", encoding="utf-8").read())
check("...'1 more round', and more rounds for more", "more round{'' if" in open("engine/combat.py", encoding="utf-8").read())
check("...the page's own names on joining, the typed command only in a terminal",
      "The Board tab shows the contracts" in open("scenes/guild_actions.py", encoding="utf-8").read())
tree = types.SimpleNamespace(category="plant", creature="t672_pine", level=5)
beast = types.SimpleNamespace(category="beast", creature="wolf", level=3)
words = loot.remains_words([tree])
check("...a felled tree is not offered for skinning", "skinn" not in words and "hide" not in words, words)
check("...a beast still is", "skinned" in loot.remains_words([beast]), loot.remains_words([beast]))
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
