"""(f671) The page echoes no machinery (docs/design/21_play_faults_plan.md, group F; found in play: docs/play/2026-11-15_play_findings.md
8.1: "create:who {...}" and "create:stats {...}" in the story, "Character saved to saves\\character.json", and the bracketed class card).
Held here: one rule for what the page shows of a line sent (bridge.echoed), tried on every line the page itself can send: its views,
its panes' buttons, the home page's and every creation page's choice show nothing; a creation box's own words show as said, without
the prefix; anything typed shows as typed. The save's path and the bracketed card are not in the story when the game runs in a window.
Run: python tools/sim/page_echo_671_test.py"""
import re
import sys
sys.path.insert(0, ".")
from ui.gui import bridge

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


js = open("ui/gui/web/app.js", encoding="utf-8").read()
sent = set(re.findall(r"""crSend\(\s*["']([a-z]+:[a-z]+)""", js)) | set(re.findall(r"""["'](#[a-z]+)\s*["']?\s*\+""", js))
creation = sorted(s for s in sent if s.startswith("create:"))
check("(the page sends creation choices)", len(creation) >= 4, creation)
for s in creation:
    line = s + ' {"x": 1}'
    shown = bridge.echoed(line)
    if s in bridge.SAID:
        check(f"a creation box's own words show as said, without the prefix: {s}", shown == '{"x": 1}', shown)
    else:
        check(f"8.1: a creation page's choice shows nothing: {s}", shown == "", shown)
for s in sorted(x for x in sent if x.startswith("#")):
    check(f"a pane's button shows nothing: {s}", bridge.echoed(s + " 12") == "" or bridge.is_view(s), s)
for v in ("#map", "#quests", "#places"):
    check(f"a view shows nothing: {v}", bridge.echoed(v) == "")
check("a line typed shows as typed", bridge.echoed("I head out the north gate") == "I head out the north gate")
check("the save's path is the debug view's", 'console.debug(f"Character saved to {path}")' in open("scenes/goddess.py", encoding="utf-8").read())
check("the bracketed card is the terminal's", "if console.windowed():" in open("scenes/goddess.py", encoding="utf-8").read())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
