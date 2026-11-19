"""(f755) A stop that leaves the map takes only its own people: whoever walks with a character goes on with them, and a companion is
never let go at a stop (LONG_SAVE-18, found by the audit fix plan's own check). leave_road took every resident of the stop who was not
gone, as "moved on along the road", and enter() calls it before bring_prisoners: so a captive taken in a town and walked bound through
a stop was marked gone in the next town while the registry still had them escorted, and the campaign's check said so. A companion let
go at a stop (Maren, who joins with `stay`, the one companion_home serves) was kept there, every stop entered being populated, and was
then removed with it once the walk went on.
Held here: the case that found it, a captive taken in Parth and walked through a stop to the next town, is still bound at the
character's side there, among its people, and the campaign's check finds nothing; the one met at the stop still goes with it. Second
cases of the kind: a captive taken at the stop itself walks on the same way; Maren let go at a stop goes back to her own place and is
not gone once the stop is left, and let go at a dangerous place goes back too (f735's one rule of a settlement, review Q15); two
captives walked through two stops in a row; and someone of a kind added to the lifecycles later, walking with a character, is not
taken with the stop but walks on with the character into the town, the campaign's check finding nothing of them, while one of that
kind gone is found (nobody walking with a character is gone), and a lifecycle naming a state it does not have as walking with a
character is refused at startup.
Run: python tools/sim/stop_people_755_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import ui.console as uc
uc.put("status_block", lambda *a, **k: None)
from engine import entities, mentor, pulse, roads
from storage import invariants, saves

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


NAME = "stop_people_755"
R = roads.R
KEEP = {k: R[k] for k in ("chance_per_leg", "hostile", "kinds", "max_per_trip")}
ESCAPE = entities.L["captive"]["escape"]
KEEP_ESCAPE = dict(ESCAPE)
MOVED_ON = "moved on along the road"


def fresh(at: str = "parth"):
    g = simlib.campaign(NAME, seed=7, location=at, minutes=420)
    ws = g.scene
    ws.enter(at)
    g.store.save_player(ws.player)
    return g, ws


def farthest(world, start: str = "parth") -> str:
    towns = [p.id for p in world.places.values() if not p.parent and not p.danger and p.type in ("town", "city", "village") and p.id != start]
    return max(((world.path(start, t) or ([], 0))[1], t) for t in towns)[1]


def walk(ws, dest: str, stops: bool) -> list:
    """One typed line through the game's one input path, setting out for dest: stopped on the road by someone met there when `stops`,
    else straight there. The operations of it that failed."""
    if stops:
        R.update(chance_per_leg=1.0, hostile=0.0, kinds={"meeting": 1}, max_per_trip=9)
    else:
        R["chance_per_leg"] = 0.0
    try:
        stub.plan = [{"kind": "move", "destination": dest}]
        ws.play(f"I set out for {ws.world.places[dest].name}.")
        return [f"{o.kind}: {o.failure}" for o in ws.line_failed]
    finally:
        R.update(KEEP)


def at_stop(ws) -> tuple:
    """The stop the character stands at (its record) and who is listed there."""
    stop = dict(ws.player.road or {})
    here = list(ws.store.load_place(stop["id"]).residents) if stop.get("id") and ws.player.location == stop["id"] else []
    return stop, here


def take(ws, name: str) -> str:
    npc = ws.make_prisoner(name, "", tip=False, named=False, kind="bandit")
    ws.store.save_player(ws.player)
    return npc.id


def bound_with(ws, nid: str, place: str) -> bool:
    """Still a captive walking bound at the character's side, standing where the character stands, among its people and present."""
    store = ws.store
    npc, e = store.load_npc(nid), store.load_entity(f"captive:{nid}")
    return (not npc.gone and e is not None and e.state == "escorted" and nid in ws.player.prisoners and nid in ws.escorted()
            and npc.location == place == ws.player.location and nid in store.load_place(place).residents and any(n.id == nid for n in ws.present))


def state_of(ws, nid: str) -> tuple:
    npc, e = ws.store.load_npc(nid), ws.store.load_entity(f"captive:{nid}")
    return npc.gone, npc.location, e.state if e else None, ws.player.location


def problems(ws, ids) -> list:
    return [str(p) for p in invariants.validate_campaign(ws.store, ws.world) if any(i in str(p) for i in ids)]


def maren_along(ws) -> tuple:
    """Maren back at the guild hall in Parth, as a later story might bring her, and asked along there: (the hall, whether she joined)."""
    store = ws.store
    hall = next(p.id for p in ws.world.places.values() if p.type == "guild" and p.parent == "parth")
    mn = mentor.make_npc(ws.player, store.meta.minutes, store.meta.turn, hall)
    mn.gone = ""
    store.save_npc(mn)
    hp = store.load_place(hall)
    hp.residents.append("maren")
    store.save_place(hp)
    ws.enter(hall)
    ws.refresh_present()
    joined = ws.party_turn("Maren, come with me") and any(m.get("npc") == "maren" for m in ws.player.party)
    return hall, joined and "maren" not in store.load_place(hall).residents


g = None
try:
    ESCAPE["chance_per_day"] = ESCAPE["chance_most"] = 0.0        # a long walk: no captive slips their bonds on the way, by the die

    # ---- the case that found it: a captive taken in a town, walked bound through a stop to the next town
    g, ws = fresh()
    store = ws.store
    dest = farthest(ws.world)
    kell = take(ws, "Kell Varrow")
    failed = walk(ws, dest, stops=True)
    stop, here = at_stop(ws)
    met = [n for n in here if n != kell]
    check("(the walk is stopped at a stop with someone met there, the captive walked there bound)",
          not failed and stop and met and bound_with(ws, kell, stop["id"]), (failed, stop.get("id"), here, state_of(ws, kell)))
    sela = take(ws, "Sela Brand")                               # taken at the stop itself, as a road fight won there takes one
    check("(a second captive, taken at the stop, is listed among its people and bound there)",
          sela in store.load_place(stop["id"]).residents and bound_with(ws, sela, stop["id"]), state_of(ws, sela))
    failed = walk(ws, dest, stops=False)
    check("(walked on, the character stands in the next town and the stop is off the map)",
          not failed and ws.player.location == dest and stop["id"] not in ws.world.places, (failed, ws.player.location))
    check("a captive walked bound through a stop is not gone once the stop is left", not store.load_npc(kell).gone, state_of(ws, kell))
    check("...still escorted, and walked on into the next town with the character: there, among its people and present",
          bound_with(ws, kell, dest), state_of(ws, kell))
    check("...and listed at the stop left behind no longer", kell not in store.load_place(stop["id"]).residents, store.load_place(stop["id"]).residents)
    check("the campaign's check finds nothing wrong with the captive", not problems(ws, [kell]), problems(ws, [kell]))
    check("a captive taken at the stop itself walks on the same way: bound at the character's side in the town, the check finding nothing",
          bound_with(ws, sela, dest) and sela not in store.load_place(stop["id"]).residents and not problems(ws, [sela]),
          (state_of(ws, sela), problems(ws, [sela])))
    check("the stop's own person, met there, still goes with it, moved on along the road",
          met and all(store.load_npc(n).gone == MOVED_ON for n in met), [(n, store.load_npc(n).gone) for n in met])
    g.close()

    # ---- a second case of the kind: Maren let go at a stop
    g, ws = fresh()
    store = ws.store
    hall, joined = maren_along(ws)
    check("(Maren, asked along at the hall, joins the party)", joined, ws.player.party)
    failed = walk(ws, dest, stops=True)
    stop, here = at_stop(ws)
    check("(the walk is stopped at a stop with someone met there, Maren in the party)",
          not failed and stop and here and any(m.get("npc") == "maren" for m in ws.player.party), (failed, stop.get("id"), here))
    ws.party_turn("dismiss Maren")
    m = store.load_npc("maren")
    check("(Maren is let go at the stop)", not any(m_.get("npc") == "maren" for m_ in ws.player.party), ws.player.party)
    check("Maren let go at a stop is not kept there: she goes back to her own place",
          m.location == hall and "maren" in store.load_place(hall).residents and "maren" not in store.load_place(stop["id"]).residents,
          (m.location, stop["id"], store.load_place(stop["id"]).residents))
    walk(ws, dest, stops=False)
    m = store.load_npc("maren")
    check("...and is not gone once the stop is left: a person of her own place, there to be found again",
          not m.gone and m.location == hall and "maren" in store.load_place(hall).residents, (m.gone, m.location))
    check("...and the campaign's check finds nothing wrong with her", not problems(ws, ["maren"]), problems(ws, ["maren"]))
    check("the one met at that stop still goes with it", here and all(store.load_npc(n).gone == MOVED_ON for n in here if n != "maren"),
          [(n, store.load_npc(n).gone) for n in here])
    g.close()

    # ---- a second case of the kind: Maren let go at a dangerous place, no settlement either (review Q15)
    g, ws = fresh()
    store = ws.store
    hall, joined = maren_along(ws)
    wild = min(((ws.world.path("parth", p.id) or ([], 10 ** 9))[1], p.id) for p in ws.world.places.values() if not p.parent and p.danger)[1]
    failed = walk(ws, wild, stops=False)
    check("(Maren in the party, the character stands in a dangerous place, entered and peopled)",
          joined and not failed and ws.player.location == wild and not pulse.settled(ws.world, wild) and store.load_place(wild).populated
          and any(m.get("npc") == "maren" for m in ws.player.party), (joined, failed, ws.player.location, wild))
    ws.party_turn("dismiss Maren")
    m = store.load_npc("maren")
    check("(Maren is let go there)", not any(m_.get("npc") == "maren" for m_ in ws.player.party), ws.player.party)
    check("Maren let go at a dangerous place is not kept there: she goes back to her own place",
          not m.gone and m.location == hall and "maren" in store.load_place(hall).residents and "maren" not in store.load_place(wild).residents,
          (m.gone, m.location, store.load_place(wild).residents))
    check("...and the campaign's check finds nothing wrong with her", not problems(ws, ["maren"]), problems(ws, ["maren"]))
    g.close()

    # ---- a second case of the kind: two captives walked through two stops in a row
    g, ws = fresh()
    store = ws.store
    dorn, wynn = take(ws, "Dorn Ashby"), take(ws, "Wynn Carrow")
    walk(ws, dest, stops=True)
    first, here1 = at_stop(ws)
    walk(ws, dest, stops=True)
    second, here2 = at_stop(ws)
    check("(two stops in a row: a second stop, the first off the map)", first and second and first["id"] != second["id"]
          and first["id"] not in ws.world.places and ws.player.location == second["id"], (first.get("id"), second.get("id"), ws.player.location))
    check("two captives walked from a first stop to a second are not gone, and stand bound at the second with the character",
          all(bound_with(ws, n, second["id"]) for n in (dorn, wynn)), [state_of(ws, n) for n in (dorn, wynn)])
    walk(ws, dest, stops=False)
    check("...and on from the second into the town, both still bound at the character's side, in the order they were taken",
          all(bound_with(ws, n, dest) for n in (dorn, wynn)) and [n for n in ws.escorted() if n in (dorn, wynn)] == [dorn, wynn],
          [state_of(ws, n) for n in (dorn, wynn)])
    met = [n for n in here1 + here2 if n not in (dorn, wynn)]
    check("the people met at both stops went with their stops", len(met) >= 2 and all(store.load_npc(n).gone == MOVED_ON for n in met),
          [(n, store.load_npc(n).gone) for n in met])
    check("the campaign's check finds nothing wrong with either captive", not problems(ws, [dorn, wynn]), problems(ws, [dorn, wynn]))
    g.close()

    # ---- the kind, not the captive: someone of a kind added later who walks with a character
    entities.L["ward"] = {"states": ["walking", "parted"], "start": "walking", "final": ["parted"], "moves": {"walking": ["parted"]},
                          "present_with_player": ["walking"]}
    g, ws = fresh()
    store = ws.store
    walk(ws, dest, stops=True)
    stop, here = at_stop(ws)
    ward = here[0] if here else ""
    if ward:
        entities.begin(store, "ward", f"ward:{ward}", store.load_npc(ward).name, ws.minutes, owner=ws.acting, links={"npc": ward})
    check("(someone met at a stop walks with the character, of a kind added to the lifecycles later)",
          ward and ward in {e.links.get("npc") for e in entities.walking(store)}, (here, ward))
    failed = walk(ws, dest, stops=False)
    check("a stop left takes nobody of any kind walking with a character: theirs is the one question leave_road asks",
          ward and not failed and not store.load_npc(ward).gone and stop["id"] not in ws.world.places,
          (failed, ward and store.load_npc(ward).gone, ws.player.location))
    wn = store.load_npc(ward) if ward else None
    check("...and they walk on with the character into the town: there, among its people, listed at the stop no longer",
          wn and wn.location == dest == ws.player.location and ward in store.load_place(dest).residents
          and ward not in store.load_place(stop["id"]).residents and any(n.id == ward for n in ws.residents),
          (wn and wn.location, ws.player.location, ward and ward in store.load_place(dest).residents, store.load_place(stop["id"]).residents))
    check("...and the campaign's check finds nothing wrong with them", ward and not problems(ws, [ward]), problems(ws, [ward]))
    if ward:
        pulse.remove_npc(store, ws.world, store.load_npc(ward), "went their own way", ws.minutes, dead=False)
    found = [str(p) for p in invariants.validate_campaign(store, ws.world) if p.where == "entities.ward"]
    check("nobody walking with a character is gone: the campaign's check finds one of a kind added later",
          any(f"ward:{ward}" in p and "is gone" in p for p in found), found)
    entities.L["ward"]["present_with_player"] = ["wandering"]
    check("a lifecycle naming a state it does not have as walking with a character is refused at startup",
          any("ward" in p and "wandering" in p for p in entities.problems()), [p for p in entities.problems() if "ward" in p])
    g.close()
finally:
    entities.L.pop("ward", None)
    ESCAPE.clear()
    ESCAPE.update(KEEP_ESCAPE)
    R.update(KEEP)
    try:
        g.close()
    except Exception:
        pass
    check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
    saves.drop(NAME)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
