"""Preview the world pulse without playing: force an event of any tier at any place and fast-forward it to the end.

Uses the real model (Ollama) unless --stub is given. Writes a readable report to saves/pulse_preview/.

  python tools/pulse_preview.py                          one campaign-tier event, wherever a random scenario puts it
  python tools/pulse_preview.py --tier rare --n 3        three rare events in a row (they see each other in "already going on")
  python tools/pulse_preview.py --pressure hrimgard_hall_feud --tier campaign
  python tools/pulse_preview.py --place brinewatch --tier uncommon
  python tools/pulse_preview.py --list                   every scenario you can force
  python tools/pulse_preview.py --stub                   no model: a template stand-in, to check the tool itself
"""
import argparse
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine import clock, pulse  # noqa: E402
from npc.life import populate_place  # noqa: E402
from npc.traits import load_traits  # noqa: E402
from storage.campaign import SAVES_DIR, CampaignStore  # noqa: E402
from world.loader import load_world  # noqa: E402


def fx(e: dict) -> str:
    k = e["kind"]
    bits = [k] + [f"{n}={e[n]}" for n in ("npc", "other", "place", "role", "value", "days", "add", "remove") if e.get(n)]
    if e.get("text"):
        bits.append(f'"{e["text"]}"')
    return " ".join(bits)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", default="campaign", choices=["normal", "uncommon", "rare", "campaign", "cataclysm"])
    ap.add_argument("--pressure", default="", help="force this scenario id (see --list)")
    ap.add_argument("--place", default="", help="force this place (uses a scenario set there, if any)")
    ap.add_argument("--level", type=int, default=100, help="player level to assume for a cataclysm")
    ap.add_argument("--n", type=int, default=1, help="how many events to run")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--stub", action="store_true", help="use the template stand-in instead of the model")
    ap.add_argument("--fresh", action="store_true", help="start the scratch world over")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    world = load_world()
    if a.list:
        for p in world.pressures.values():
            print(f"{p.id:26} {p.place:20} {p.kind:9} sev {p.severity[0]}-{p.severity[1]}  {p.description}")
        return
    if a.stub:
        sys.path.insert(0, str(ROOT))
        import simlib
        simlib.install(simlib.Stub("warrior", a.seed or 1))
    scratch = SAVES_DIR / "pulse_preview"
    if a.fresh and scratch.exists():
        shutil.rmtree(scratch)
    store = CampaignStore.open_or_create("pulse_preview")
    catalog = load_traits()
    rng = random.Random(a.seed)
    state = store.load_world_state() or pulse.empty_state(clock.day_start(5) if hasattr(clock, "day_start") else 5 * 1440)
    t = max(state["last"], 5 * 1440)
    report = []
    for i in range(a.n):
        before = {x["id"] for x in state["threads"]}
        where = world.pressures[a.pressure].place if a.pressure else a.place
        if where and where in world.places:
            try:
                populate_place(store, world, pulse.town_of(world, where), catalog)
            except Exception as err:
                print(f"(could not populate {where} with residents: {err}; the event will have no named people)")
        if a.tier in ("campaign", "cataclysm"):
            state["campaign"] = ""
        if a.tier == "cataclysm":
            from engine import events
            events.player_level = lambda s, _l=a.level: _l
            ok = events.start_cataclysm(store, world, catalog, state, t, rng)
        else:
          ok = pulse.start_thread(store, world, catalog, state, t, rng, tier=a.tier, pressure_id=a.pressure, place_id=a.place)
        if not ok:
            print("The model gave nothing usable this time (try again).")
            continue
        th = next(x for x in state["threads"] if x["id"] not in before)
        town = world.places[th["place"]].name
        out = [f"# Event {i + 1}: {th['title']}",
               f"- Tier **{th['tier']}** · at {town} · seed `{th['pressure'] or 'free choice'}` · {len(th['stages'])} stage(s) over "
               f"{(th['times'][-1] - th['times'][0]) / 1440:.1f} days · first heard by: {', '.join(th['groups'])}",
               f"- What people are saying: {state['news'][-1]['text'] if state['news'] else ''}",
               f"- What would settle it: {th['resolution']}", ""]
        for n, st in enumerate(th["stages"]):
            day = (th["times"][n] - th["times"][0]) / 1440
            out.append(f"**Stage {n + 1}** (day {day:.0f}): {st['description']}")
            out += [f"  - effect: {fx(e)}" for e in st["effects"]]
        out.append(f"**If nobody steps in:** {th['fallout']['description']}")
        out += [f"  - effect: {fx(e)}" for e in th["fallout"]["effects"]]
        board = [q["title"] for pid in store.list_places() for q in store.load_place(pid).board if q.get("thread") == th["id"]]
        if board:
            out.append(f"**Guild contract posted:** {board[0]}")
        out.append("")
        out.append("### How it plays out (fast-forwarded)")
        seen_stage, news_n = 0, len(state["news"])
        while th["status"] == "active":
            t += pulse.INTERVAL
            state["last"] = t
            pulse.tick_threads(store, world, catalog, state, t, rng)
            for n in state["news"][news_n:]:
                out.append(f"- day {(t - th['times'][0]) / 1440:.0f}: news - {n['text']}")
            news_n = len(state["news"])
        last = state["history"][-1] if state["history"] else {"text": ""}
        out.append(f"- day {(t - th['times'][0]) / 1440:.0f}: **{th['status']}** - {last['text']}")
        live = [e for e in state["effects"] if e["until"] > t]
        if live:
            out.append("- still in force afterwards: " + "; ".join(f"{e['kind']} {e.get('value', '')} at {e['place']}" for e in live))
        out.append("")
        report.append("\n".join(out))
        t += pulse.INTERVAL * 3
        state["last"] = t
    store.save_world_state(state)
    text = "\n".join(report)
    store.root.mkdir(parents=True, exist_ok=True)
    dest = store.root / "preview.md"
    dest.write_text(text, encoding="utf-8")
    print(text)
    print(f"\n(saved to {dest})")


if __name__ == "__main__":
    main()
