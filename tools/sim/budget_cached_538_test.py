"""(f538) The turn's budget charges a call for the prompt the server read, not the part it reused from its cache: the share comes from the
server's own counts (usage prompt and cached), so the understanding, which reuses most of its prompt since f536, no longer eats the
time the rest of the turn needs. A stand-in that reports no counts, or a failed try, is charged in full as before. A recording says how its
calls were priced (meta budget_cached), and a recording made before f538 replays with reuse charged as read, so it defers where it did.
The estimate of a recording's required path prices the reuse it recorded the same way."""
import gzip
import json
import shutil
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from pydantic import BaseModel   # noqa: E402

from engine import budget         # noqa: E402
from llm import backend, gateway  # noqa: E402

bad = []


def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {extra}"))
    if not ok:
        bad.append(name)


class Tiny(BaseModel):
    ok: bool


cpt = float(budget.B.get("chars_per_token") or 4.0)
read, write = budget.PROFILE["read_tps"], budget.PROFILE["write_tps"]

# ---- 1. the estimate: the reused share is not read; the answer is written in full; the share is held to 0..1
full = budget.estimate("interpret_action", 4000, 40)
part = budget.estimate("interpret_action", 4000, 40, cached=0.75)
check("a reused share of the prompt is not priced: a quarter of the reading, all of the writing",
      abs(part - (1000 / cpt / read + 40 / cpt / write)) < 1e-9 and abs(full - (4000 / cpt / read + 40 / cpt / write)) < 1e-9, (full, part))
check("...a share past 1 or below 0 is held to the ends", abs(budget.estimate("narrate", 4000, 40, cached=1.7) - 40 / cpt / write) < 1e-9
      and abs(budget.estimate("narrate", 4000, 40, cached=-0.5) - budget.estimate("narrate", 4000, 40)) < 1e-9)
check("the share is read from the server's counts, and is none without them",
      budget.cached_share({"prompt": 1000, "cached": 770}) == 0.77 and budget.cached_share({"prompt": 0, "cached": 0}) == 0.0
      and budget.cached_share({"prompt": 1000}) == 0.0 and budget.cached_share(None) == 0.0 and budget.cached_share({"prompt": True, "cached": 1}) == 0.0)


# ---- 2. through the gateway: an answer with the server's counts is charged for what was read; one without, in full
class Fake:
    def __init__(self):
        self.usage = None

    def chat(self, **k):
        r = types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content='{"ok": true}'))
        if self.usage is not None:
            r.usage = dict(self.usage)
        return r


fake = Fake()
undo = backend.use(backend.StandIn(chat=fake.chat))
try:
    system, user = "s" * 3000, "u" * 1000
    b = budget.open(limit=600)
    fake.usage = None
    gateway.generate("interpret_action", system, user, Tiny)
    no_counts = b.charges[-1][1]
    fake.usage = {"prompt": 1000, "cached": 750, "out": 5}
    gateway.generate("interpret_action", system, user, Tiny)
    with_counts = b.charges[-1][1]
    budget.close()
    answer = len('{"ok": true}')
    check("a call the server answered with its counts is charged for the quarter it read",
          abs(with_counts - (1000 / cpt / read + answer / cpt / write)) < 1e-6, (with_counts, 1000 / cpt / read + answer / cpt / write))
    check("...one with no counts (a stand-in) is charged in full, as before", abs(no_counts - (4000 / cpt / read + answer / cpt / write)) < 1e-6, no_counts)
    check("...and the required path counts what was charged", b.required_seconds == b.spent and b.spent < 2 * no_counts)
    budget.CACHED = False
    b = budget.open(limit=600)
    gateway.generate("interpret_action", system, user, Tiny)
    budget.close()
    check("with the pricing off (a replay of a recording from before f538), reuse is charged as read", abs(b.charges[-1][1] - no_counts) < 1e-6,
          (b.charges[-1][1], no_counts))
finally:
    budget.CACHED = True
    undo()

# ---- 2b. the pricing decides: the understanding's reuse charged as read leaves no room for an optional call it leaves room for now
def after_understanding(on):
    budget.CACHED = on
    b = budget.open(limit=60)
    b.charge("interpret_action", 40000, 40, cached=0.77)
    return b


b_on, b_off = after_understanding(True), after_understanding(False)
budget.close()
keep = b_on.reserve
room_on, room_off = b_on.remaining() - keep, b_off.remaining() - keep
tokens = ((room_on + room_off) / 2 - float(budget.TASKS["dialogue_frame"]["answer_tokens"]) / write) * read      # an optional call between the two
fits = []
for on, b in ((True, b_on), (False, b_off)):
    budget.CACHED = on
    try:
        b.allow("dialogue_frame", int(tokens * cpt))
        fits.append(True)
    except budget.Dropped:
        fits.append(False)
budget.CACHED = True
check("an optional call the turn has room for once the understanding's reuse is not charged is made, and dropped when it is charged as read",
      fits == [True, False] and room_on > room_off, (fits, round(room_on, 1), round(room_off, 1)))
check("...and a required call still running is given the longer deadline", b_on.deadline() > b_off.deadline())

# ---- 3. the replay prices calls as the recording did; the pricing is put back after
import rerun   # noqa: E402

seen = []
out = rerun.replay(rerun.golden("stub_short"), on_call=lambda row, k, request: seen.append(budget.CACHED))
check("a kept recording made before f538 replays whole, its calls priced as they were (reuse charged as read)",
      out["parted"] is None and out["matched"] == out["of"] and seen and not any(seen), (out.get("parted"), set(seen)))
check("...and the pricing is put back after", budget.CACHED is True)
tmp = Path(tempfile.mkdtemp(prefix="cached538_"))
try:
    copy = tmp / "stub_short"
    shutil.copytree(rerun.golden("stub_short"), copy)
    meta = json.loads((copy / "meta.json").read_text(encoding="utf-8"))
    meta["budget_cached"] = True
    (copy / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    seen.clear()
    out = rerun.replay(copy, on_call=lambda row, k, request: seen.append(budget.CACHED))
    check("a recording that says its calls were priced by reuse replays with the pricing on (a stub reports no reuse, so it still matches)",
          out["parted"] is None and seen and all(seen), (out.get("parted"), set(seen)))

    # ---- 4. the recorder says how it priced; the estimate tool prices recorded reuse as the budget does
    src = (ROOT / "engine" / "recording.py").read_text(encoding="utf-8")
    check("the recorder writes how the budget priced its calls", '"budget_cached": bool(budget.CACHED)' in src)
    import card_profile
    rec = tmp / "rec"
    rec.mkdir()
    row = {"i": 0, "input": 1, "kind": "chat", "task": "interpret_action", "title": "ActionPlan", "answer": "x" * 40, "seconds": 1.0,
           "request": {"messages": [{"role": "system", "content": "s" * 3000}, {"role": "user", "content": "u" * 1000}]},
           "usage": {"prompt": 1000, "cached": 750, "out": 10, "read_ms": 100, "write_ms": 300}}
    with gzip.open(rec / "calls.jsonl.gz", "wt", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
        f.write(json.dumps({**row, "i": 1, "input": 2, "usage": {}}) + "\n")
    est = dict(card_profile.estimate_inputs(rec))
    m = card_profile.measure(rec)
    check("the card's reading speed is the tokens it read over the time it read them, never the reused ones too (they would be credited twice)",
          m["read_tps"] == 2500.0, m["read_tps"])
    check("the required path of a recording is priced without the reuse it recorded, and in full where it recorded none",
          abs(est[1] - budget.estimate("interpret_action", 4000, 40, 0.75)) < 1e-9 and abs(est[2] - budget.estimate("interpret_action", 4000, 40)) < 1e-9, est)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
