"""The truth layer (f313): what is true at this moment, assembled once a turn, read by every speaker and every checker.

Whatever a speaker is not told, a model invents: a smith the town does not have, a contract that is not on the board, a stranger's
business that only Maren knows. Each prompt used to gather its own view of the scene, so each leaked in its own way. Now there is one
assembly, the Scene, built from facets - small functions that each read one part of the game's state and return facts tagged with who may
know them - and one renderer that writes a viewer's view under fixed headers (data/rules/truth.yaml). The audit and the interpreter read
the same present list as the narrator and the people of the world, so they can never disagree about who is here.

  Fact      one line, with the tags of who can know it (see truth.yaml for the tags)
  Present   one being standing here: a townsperson, Maren, a hire, the wildlife - for the narrator, the interpreter and the audit alike
  Viewer    who is reading: their knowledge groups, whether they are the player or travel with them
  Scene     the facets, computed lazily and cached for the turn
  View      a viewer's facts, rendered by profile

Adding a system to the world means adding a facet (the @facet decorator) and naming it in a profile; nothing else changes."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
T = yaml.safe_load((ROOT / "data" / "rules" / "truth.yaml").read_text(encoding="utf-8"))
_WORD = re.compile(r"[a-z]+")

TOWN_BUILDINGS = ("smithy", "shop", "inn", "temple", "guild", "workshop")
BUILDING_ROLES = {"smithy": ("smith",), "shop": ("merchant", "chandler", "relic_dealer"), "inn": ("innkeeper",), "temple": ("priest", "acolyte", "water_priest"),
                  "guild": ("guild_clerk",), "workshop": ("engineer", "tinker", "enchanter")}
TRADES = ("smith", "herbalist", "priest", "innkeeper", "merchant", "enchanter", "land_agent", "guild_clerk", "relic_dealer", "tinker",
          "engineer", "stonemason", "chandler", "butcher", "baker", "cook", "miller", "hunter", "trapper", "caravan_master", "watch_captain",
          "loremaster", "quartermaster", "fisher", "shepherd", "farmer", "miner", "lumberjack", "orchard_keeper", "scout", "guard")


@dataclass
class Fact:
    facet: str
    text: str
    known: frozenset = frozenset({"all"})
    id: str = ""


@dataclass
class Present:
    id: str
    name: str                   # their real name (what their neighbours call them)
    label: str                  # what the player knows them as
    desc: str
    doing: str
    kind: str = "npc"           # npc | maren | hire | wildlife
    note: str = ""              # for the interpreter: an offer they have made, how to speak to them
    role: str = ""              # a townsperson's role
    plain: str = ""             # their description without the people and manner (what the interpreter is shown)
    local: str = ""             # the community a townsperson belongs to (world.locals_group): their neighbours know their name


@dataclass
class Viewer:
    id: str = ""
    kind: str = "npc"           # npc | hire | maren | narrator | interpreter | audit | player
    groups: frozenset = frozenset({"everyone"})
    in_party: bool = False
    is_player: bool = False

    def sees(self, fact: Fact) -> bool:
        k = fact.known
        if "all" in k:
            return True
        if self.is_player and "player" in k:
            return True
        if self.in_party and "party" in k:
            return True
        if "narrator" in k and self.kind in ("narrator", "interpreter", "audit"):
            return True
        if self.id and f"npc:{self.id}" in k:
            return True
        return any(f"groups:{g}" in k for g in self.groups)


FACETS: dict = {}


def facet(name: str):
    def wrap(fn):
        FACETS[name] = fn
        return fn
    return wrap


class Scene:
    """The facts of this moment. Built on a world scene (scenes/world.py); each facet is computed the first time it is asked for."""

    def __init__(self, ws):
        self.ws = ws
        self._facts: dict[str, list[Fact]] = {}
        self._present: list[Present] | None = None
        self._condition = None

    def condition(self):
        """The town's condition this turn (engine/towns.py, f316): calm, uneasy, mourning, hungry, festive, prospering or besieged."""
        if self._condition is None:
            from engine import towns
            from ui import console
            self._condition = towns.condition(self.ws.store, self.ws.world, self.ws.player.location, self.ws.minutes)
            if self._condition.name != "calm":
                console.debug(f"town condition: {self._condition.name} ({self._condition.why})")
        return self._condition

    @staticmethod
    def key(ws) -> tuple:
        return (ws.store.meta.turn, ws.minutes, ws.player.location, tuple(n.id for n in ws.present), len(ws.player.quests),
                tuple(m.get("id") for m in ws.player.party), ws.player.party_mode, bool(ws.combat), bool(ws.wildlife),
                ws.player.mentor.get("stage", ""), ws.player.guild_rank, player_pronoun(ws.player.character))     # (f386) '#pronoun' is seen at once

    def facts(self, name: str) -> list[Fact]:
        if name not in self._facts:
            self._facts[name] = list(FACETS[name](self)) if name in FACETS else []
        return self._facts[name]

    # ---- who is here: one list for everyone that asks

    def present_people(self) -> list[Present]:
        if self._present is None:
            self._present = _present_people(self.ws)
        return self._present

    def present_ids(self) -> dict[str, str]:
        """id -> label, for the audit and anyone checking a target."""
        return {p.id.lower(): p.label for p in self.present_people()}

    def names(self) -> set[str]:
        """Every name a speaker here may use for a person: those present, and the people of this town."""
        out = {p.name for p in self.present_people() if p.name} | {p.label for p in self.present_people()}
        from engine import retrieval, pulse
        town = pulse.town_of(self.ws.world, self.ws.player.location)
        out |= {r.name for r in retrieval.people_in_town(self.ws.store, self.ws.world, town, gone=None) if r.name}
        return out

    def known_words(self) -> frozenset:
        """The words of every name a speaker here may use whatever their prompt happens to hold (f315): the people here and of this town,
        the party, the player, Maren, and the places of the world. The speech check (check_speech) lets these pass and nothing else that
        was not in the prompt."""
        if getattr(self, "_known", None) is None:
            ws = self.ws
            from engine import mentor
            names = self.names() | {ws.player.character.name, mentor.NAME, ws.world.name} | {m.get("name", "") for m in ws.player.party}
            names |= {p.name for p in ws.world.places.values()} | {r.name for r in ws.world.regions.values()} | {p.name for p in ws.world.peoples.values()}
            t = ws.world.town(ws.player.location)
            if t:                                                   # (f316) the town's named things and quarters
                names |= {l.name for l in t.landmarks} | set(t.districts) | {f.name for f in t.festivals}
            words = set()
            for n in names:
                words |= set(_WORD.findall((n or "").lower()))
            self._known = frozenset(words)
        return self._known

    def view(self, viewer: Viewer, profile: str) -> "View":
        return View(self, viewer, profile)


class View:
    def __init__(self, scene: Scene, viewer: Viewer, profile: str):
        self.scene, self.viewer, self.profile = scene, viewer, profile
        self.skip: set[str] = set()
        self.allow: set[str] = set()                  # (f375) narrator-only facts this viewer is given for this reply ('crowd')

    def asking(self, text: str) -> "View":
        """(f375) The same view for a reply to these words: the street scene comes in when they are about the town or its streets."""
        if streets_asked(text):
            self.allow.add("crowd")
        return self

    def without(self, *names: str) -> "View":
        """The same view with these people left out of WHO IS HERE: the speakers of an exchange are introduced in its own block."""
        self.skip |= {n for n in names if n}
        return self

    def facets(self) -> list[str]:
        return list(T["profiles"][self.profile])

    def lines(self, name: str) -> list[str]:
        if name == "present":
            return self.present_lines()
        v = self.viewer
        return [f.text for f in self.scene.facts(name) if v.sees(f) or (f.id and f.id in self.allow)]

    def present_lines(self) -> list[str]:
        """Who is here, as this viewer knows them: a townsperson knows their neighbours by name and sees strangers (Maren, the hires) as
        what they look like; the narrator, the interpreter and the audit use what the player knows them as; those travelling with the
        player know everyone's name. (f375) What the others are doing goes only to the narrator and the engine's readers: told everyone's
        chores, the people who speak brought them up as news, and garbled them."""
        v = self.viewer
        out = []
        for p in self.scene.present_people():
            if p.id == v.id or p.name in self.skip or p.label in self.skip:
                continue
            if v.kind == "npc":
                who = p.name if (p.kind == "npc" and p.local and p.local in v.groups) else (p.name if p.kind == "npc" else p.desc)
                out.append(who if p.kind == "npc" else (p.desc if p.kind == "companion" else f"a stranger here with the one in front of you - {who}".strip()))
            elif v.kind in ("hire", "maren"):                 # (f315) the party knows its own by name, and the townsfolk as the player does - unless they are neighbours
                who = p.name if (p.kind != "npc" or (p.local and p.local in v.groups)) else p.label
                out.append(f"{who}: {p.desc}".strip().rstrip(":"))
            else:
                out.append(f"{p.label}: {p.desc} {p.doing}".strip())
        return out

    def streets(self) -> list[str]:
        """The crowd, the watch and the quarters: the lines of WHERE that are not the place's own description."""
        return [f.text for f in self.scene.facts("here") if f.id in ("crowd", "guard", "districts", "condition", "landmarks") and self.viewer.sees(f)]

    def sections(self) -> list[tuple[str, list[str]]]:
        out = []
        for name in self.facets():
            lines = self.lines(name)
            if lines:
                out.append((T["headers"][name], lines))
        return out

    def text(self) -> str:
        return "\n".join(f"{h}:\n" + "\n".join(f"  - {l}" for l in lines) for h, lines in self.sections())


# ---------- building the scene

def scene_of(ws) -> Scene:
    """This turn's scene, built once; the key says when the moment has moved on."""
    key = Scene.key(ws)
    cached = getattr(ws, "_truth", None)
    if cached is None or cached[0] != key:
        cached = (key, Scene(ws))
        ws._truth = cached
    return cached[1]


_STREETS = re.compile(r"\b(streets?|town|busy|crowds?|crowded|square|market|bridge|outside|out there|going on|about today|people about|traffic|carts?|quiet)\b",
                      re.I)


def streets_asked(text: str) -> bool:
    """(f375) Are these words about the town or its streets (how busy, who is about, what is going on outside)? Then a speaker is given
    the street scene for this reply; otherwise only the narrator has it."""
    return bool(_STREETS.search(text or ""))


def viewer_for_npc(npc, world=None) -> Viewer:
    """A townsperson's knowledge: the groups set when they became a person, or, before that, the groups their place and role give."""
    groups = set(npc.knowledge_groups)
    if not groups and world is not None:
        groups = {world.locals_group(npc.location) or "", *world.roles[npc.role].knowledge_groups} - {""}
    return Viewer(id=npc.id, kind="npc", groups=frozenset(groups | {"everyone"}))


def viewer_for_hire(hid: str) -> Viewer:
    """A hired adventurer: guild people, travelling with the player. hid is the present-list id (hire:<id>), so they are not shown themselves."""
    return Viewer(id=hid, kind="hire", groups=frozenset({"everyone", "guild"}), in_party=True)


MAREN = Viewer(id="maren", kind="maren", groups=frozenset({"everyone", "guild", "parth_locals"}), in_party=True)      # of Parth: she knows its people by name
PARTY = Viewer(id="party", kind="hire", groups=frozenset({"everyone", "guild"}), in_party=True)                      # the party among themselves (an exchange)
NARRATOR = Viewer(id="narrator", kind="narrator", groups=frozenset({"everyone"}))
INTERPRETER = Viewer(id="interpreter", kind="interpreter", groups=frozenset({"everyone"}))
AUDIT = Viewer(id="audit", kind="audit", groups=frozenset({"everyone"}))
PLAYER = Viewer(id="player", kind="player", groups=frozenset({"everyone"}), is_player=True, in_party=True)


def their_work(label: str, role: str) -> str:
    """(f378) What someone does for a living, for the narrator: 'the guild clerk', or '' when how the player knows them already says it.
    Told only their look and their doing, the narrator took a spectacled quartermaster weighing a sack for the clerk, and wrote the real
    clerk, whom the player knew by name, as a second man reading at the board."""
    role = (role or "").replace("_", " ").strip()
    if not role or role.split()[-1] in (label or "").lower():
        return ""
    return f"the {role}"


def _present_people(ws) -> list[Present]:
    from npc.life import manner
    out = []
    from engine import entities
    for n in ws.present:
        who = entities.identity(ws, n.id)                                    # (f392) she or he, and their people: never guessed at
        people = f"{who.pronoun}, {who.people}" if who else (ws.world.peoples[n.people].name if n.people in ws.world.peoples else n.people)
        from scenes.work_actions import offer_open                  # (f395) an offer that still stands
        note = (f"Has offered the player paid work ({n.work_offer['task']}): the player agreeing to it, doing it or finishing it is a work action, "
                "and 'taking the pay' once it is done is part of that work." if offer_open(n, ws.minutes) else "")
        out.append(Present(id=n.id, name=n.name or n.label(), label=n.label(), kind="npc", doing=n.activity or "", role=n.role.replace("_", " "),
                           desc=f"({people}) {n.description} Manner: {manner(n, ws.catalog, ws.store)}." + (f" Lately: {n.mood}." if n.mood else ""),   # (f334) a mood shows
                           note=note, plain=n.description or "",
                           local=ws.world.locals_group(n.location) or ""))
    her = ws.mentor_person()
    if her:
        out.append(Present(id="maren", name=her[0], label=her[0], desc=her[1].replace("(human)", "(she, human)", 1), doing=her[2], kind="maren",
                           note="travelling with the player; speech to her is talk with target maren"))
    for hid, name, desc, doing in ws.hire_people():
        out.append(Present(id=hid, name=name, label=name, desc=desc, doing=doing, kind="hire",
                           note=f"hired, travelling with the player; speech to them is talk with target {hid}"))
    for comp in [c for c in getattr(ws.player.character, "companions", None) or [] if c.active and c.name]:     # (f384) Fenris, at your side
        kind_of = (ws.world.bestiary[comp.creature].name.lower() if comp.creature in ws.world.bestiary else (comp.kind or "animal"))
        out.append(Present(id=f"companion:{comp.id}", name=comp.name, label=comp.name,
                           desc=f"({entities.identity(ws, f'companion:{comp.id}').pronoun}) the player's own {kind_of}, at the player's side",
                           doing="at the player's side", kind="companion",
                           note="the player's own companion: telling it to track, sniff out or hunt something is search; it is not talked with"))
    if ws.wildlife:
        out.append(Present(id="wildlife", name=", ".join(e.name for e in ws.wildlife[1]), label=", ".join(e.name for e in ws.wildlife[1]),
                           desc="a creature, keeping its distance", doing="", kind="wildlife"))
    return out


# ---------- the facets

def scale_of(world, place) -> str:
    """How big and busy a place is: its own scale, else its town's, else by type."""
    from engine import mapview
    if place.scale:
        return place.scale
    top = world.places.get(mapview.top_of(world, place.id))
    if top is not None and top is not place and top.scale:
        return top.scale
    t = (top or place).type
    return T["scale_by_type"].get(t, "village")


@facet("here")
def _here(scene: Scene):
    ws = scene.ws
    from engine import clock, pulse, mapview
    place, world = ws.place, ws.world
    top_id = mapview.top_of(world, place.id)
    top = world.places.get(top_id)
    where = place.name + (f", in {top.name}" if top is not None and top is not place else "")
    out = [Fact("here", f"{where}: {ws.time_label()}")]
    for v in place.visible:
        out.append(Fact("here", " ".join(v.split())))
    if not place.danger:                                          # a settled place has streets, and a crowd in them
        scale = scale_of(world, place)
        slot = T["periods"].get(clock.period(ws.minutes), "quiet")
        cond = scene.condition()
        crowd = cond.crowd or (place.crowd or (top.crowd if top is not None else {}) or {}).get(slot) or T["crowd"].get(scale, T["crowd"]["village"])[slot]
        crowd = " ".join(crowd.split())
        prefix = "Outside: " if top is not None and top is not place else ""
        out.append(Fact("here", prefix + crowd + ("" if crowd.endswith((".", "!", "?")) else "."), id="crowd",
                        known=frozenset({"narrator"})))           # (f375) the street scene is the narrator's; a speaker hears it when asked (View.asking)
        guard = place.guard or (top.guard if top is not None else "") or T["guard"].get(scale, "light")
        line = T["guard_lines"].get(guard, "")
        if line:
            out.append(Fact("here", "The watch: " + line + ".", id="guard"))
        if cond.hint:                                             # (f316) the town's condition, as it shows
            out.append(Fact("here", f"The town right now ({cond.name}): {cond.hint}", id="condition"))
        if place.districts or (top is not None and top.districts):
            out.append(Fact("here", "Quarters of the town: " + ", ".join(place.districts or top.districts) + ".", id="districts"))
        from engine import towns
        marks = towns.landmarks_at(world, place.id)
        if marks:
            out.append(Fact("here", "Landmarks here: " + "; ".join(f"{l.name} ({l.note})" if l.note else l.name for l in marks) + ".", id="landmarks"))
    return out


@facet("present")
def _present(scene: Scene):
    return []                   # rendered from present_people() by the viewer's knowledge (View.present_lines)


@facet("town")
def _town(scene: Scene):
    """What this town has, every one of it: its buildings and its tradespeople by name, and for the usual buildings it lacks, the nearest
    one elsewhere. Parth has no smithy, and a smith (f313): both are said."""
    ws = scene.ws
    from engine import mapview, clock, retrieval
    world = ws.world
    if ws.place.danger:
        return []
    top = mapview.top_of(world, ws.player.location)
    town = world.places[top].name if top in world.places else "this town"
    out = []
    prof = world.town(ws.player.location)                           # (f316) what the town is like, and the state it is in
    if prof and prof.character:
        out.append(Fact("town", f"{town}: " + " ".join(prof.character.split())))
    cond = scene.condition()
    if cond.name != "calm":
        out.append(Fact("town", f"the town is {cond.name} ({cond.why}): {cond.hint}"))
    from engine import matters
    for m in matters.town_memory(ws.store, world, ws.player.location, ws.minutes):      # (f317) what the town remembers of matters ended here
        out.append(Fact("town", f"lately: {m}"))
    have: dict[str, list[str]] = {}
    for p in world.places.values():
        if p.type in TOWN_BUILDINGS and mapview.top_of(world, p.id) == top:
            have.setdefault(p.type, []).append(p.name)
    people_by_role: dict[str, list[str]] = {}
    for r in retrieval.people_in_town(ws.store, world, top):
        if r.role in TRADES and r.name:
            spot = world.places[r.location].name if r.location in world.places else town
            people_by_role.setdefault(r.role, []).append(f"{r.name} ({spot})")
    for pid in retrieval.town_places(world, top):                 # people the town is written to have but the player has not yet come across
        if ws.store.load_place(pid).populated:
            continue
        spot = world.places[pid].name
        for role, n in (world.places[pid].residents or {}).items():
            if role in TRADES and role not in people_by_role:
                people_by_role.setdefault(role, []).append(f"{'one' if n == 1 else n} at {spot}, not yet met")
    for t, names in sorted(have.items()):
        out.append(Fact("town", f"{t}: {', '.join(names)}"))
    for role, names in sorted(people_by_role.items()):
        out.append(Fact("town", f"{role.replace('_', ' ')}: {', '.join(names)}"))
    for t in TOWN_BUILDINGS:
        tradesman = next((r for r in BUILDING_ROLES.get(t, ()) if r in people_by_role), "")
        if t in have:
            continue
        if tradesman:
            out.append(Fact("town", f"{t}: no {t} building in {town}; the {tradesman.replace('_', ' ')} above works without one"))
            continue
        best = None
        for p in world.places.values():
            if p.type != t:
                continue
            r = world.path(ws.player.location, p.id)
            if r and (best is None or r[1] < best[1]):
                best = (p, r[1])
        out.append(Fact("town", f"{t}: none in {town}" + (f"; the nearest is {best[0].name} in {world.places[mapview.top_of(world, best[0].id)].name}, "
                                                           f"{clock.walk_words(best[1])} away" if best else "")))        # (f349) as a local says it
    return out


@facet("board")
def _board(scene: Scene):
    ws = scene.ws
    if not ws.hall_here():
        return []
    from engine import quests
    known = frozenset({"all"}) if ws.place.type == "guild" else frozenset({"groups:guild"})    # pinned on the wall in the hall; the guild's people know it anywhere in town
    rank = ws.rank or "F"
    out = []
    for q in ws.ensure_board():
        out.append(Fact("board", f"[{q['letter']}] {q['title']}" + ("" if quests.at_or_below(q["letter"], rank) else " (above the player's rank)"), known))
    if not out:
        out.append(Fact("board", "nothing is posted", known))
    held = [q["title"] for q in ws.player.quests if q.get("guild")]
    if held:
        out.append(Fact("board", "the player holds: " + "; ".join(held), known))
    return out


@facet("happenings")
def _happenings(scene: Scene):
    """The situations' own happenings here, and the ordinary day's (engine/ambient.py, f331): market day, a funeral, the watch out."""
    from engine import ambient, moments, pulse
    ws = scene.ws
    out = [Fact("happenings", h) for h in pulse.happenings_at(ws.store, ws.world, ws.player.location, ws.minutes)]
    out += [Fact("happenings", h) for h in moments.lines_at(ws.store, ws.player.location, ws.minutes)]       # (f348) a moment under way here
    out += [Fact("ambient", h) for h in ambient.lines(ws.store, ws.world, ws.player.location, ws.minutes, ws.player)]
    return out


@facet("news")
def _news(scene: Scene):
    """News that has reached this place, each piece tagged with the circles that carry it: a viewer hears what their circles hear."""
    from engine import pulse
    ws = scene.ws
    state = ws.store.load_world_state()
    return [Fact("news", pulse.news_text(n, ws.minutes), frozenset(f"groups:{g}" for g in n["groups"]))                      # (f356) a window that turns over by the day
            for n in pulse.news_window(state or {}, ws.world, ws.player.location, ws.minutes, 8, key=str(ws.store.meta.seed))]


@facet("fallen")
def _fallen(scene: Scene):
    """(f392) The companions who died travelling with the player (engine/entities.py): known to the party and the narrator, so a death
    is spoken of and remembered, and the dead are never seen alive again."""
    from engine import entities
    ws = scene.ws
    F = T.get("fallen") or {}
    out = []
    dead = [e for e in ws.store.find_entities(kind="hire", state="dead") if ws.minutes - e.since <= F.get("days", 60) * 1440][-F.get("most", 4):]
    for e in reversed(dead):
        days = (ws.minutes - e.since) // 1440
        when = "today" if days < 1 else "yesterday" if days < 2 else f"{days} days ago"
        where = f" at {e.data['place_name']}" if e.data.get("place_name") else ""
        out.append(Fact("fallen", f"{e.name} ({entities.people_word(ws.world, e.people) or 'person'}, {e.pronoun}), "
                                  f"{e.data.get('role') and 'a hired ' + e.data['role'] or 'a companion'}: died {when}{where}",
                        frozenset({"party", "narrator"})))
    return out


@facet("lately")
def _lately(scene: Scene):
    """(f330) What the player did here lately that people saw, from the journal (engine/reactions.py publishes every deed): a deed is known to
    those who saw it and to the narrator; a public one (a job done, a tithe) to everyone of the town. Nothing done unseen, nothing elsewhere."""
    from engine import clock, mapview
    ws = scene.ws
    L = T.get("lately") or {}
    if not L or ws.place.danger:
        return []
    world = ws.world
    top = mapview.top_of(world, ws.player.location)
    here = {pid for pid in world.places if mapview.top_of(world, pid) == top}
    public = set(L.get("public", []))
    keep = int(L.get("days", 10)) * 1440
    out = []
    for row in ws.store.journal_tail(int(L.get("rows", 150))):
        data = row.get("data") or {}
        if row["actor"] != "player" or data.get("place") not in here or ws.minutes - row["minute"] > keep or not row["text"]:
            continue
        witnesses = [w for w in (data.get("witnesses") or []) if w]
        if row["kind"] in public:
            known = frozenset({"all"})
        elif witnesses:
            known = frozenset({f"npc:{w}" for w in witnesses} | {"narrator"})
        else:
            continue
        when = "today" if clock.day(row["minute"]) == clock.day(ws.minutes) else f"day {clock.day(row['minute'])}"
        out.append(Fact("lately", f"{when}: the stranger {row['text']}", known, id=row["kind"]))
    return out[-int(L.get("most", 8)):]


_HE = re.compile(r"\b(he|him|his|himself|man|men|male|boy|lad|son|father|brother|husband|king|lord|mister|gentleman)\b", re.I)
_SHE = re.compile(r"\b(she|her|hers|herself|woman|women|female|girl|lass|daughter|mother|sister|wife|queen|lady|madam|nun|priestess)\b", re.I)
SEEN_AS = {"he": "is a man", "she": "is a woman",
           "they": "you cannot tell at a glance whether a man or a woman: call them nothing that says (no sir, madam, lad or lass)"}


def player_pronoun(c) -> str:
    """(f386) she, he or they for the player, the same every time. Nothing kept it: across a night's runs the people of the world called
    one player sir, madam, lad and lass, two of them in one turn. Read once from their own words at the Threshold and the reading of
    their class, and kept; 'they' when those words do not say. '#pronoun' sets it."""
    if c.pronoun in SEEN_AS:
        return c.pronoun
    words = f"{c.concept} {c.custom_class} {c.class_summary}"
    he, she = len(_HE.findall(words)), len(_SHE.findall(words))
    c.pronoun = "he" if he > she else "she" if she > he else "they"
    return c.pronoun


@facet("player")
def _player(scene: Scene):
    """What anyone can see of the player: whether a man or a woman, the badge, the weapon, the company they keep."""
    ws = scene.ws
    c = ws.player.character
    out = [Fact("player", SEEN_AS[player_pronoun(c)])]
    if getattr(c, "look_text", ""):                     # (f388) what they chose to keep of themselves: what anyone sees
        out.append(Fact("player", "looks like this: " + c.look_text))
    out.append(Fact("player", f"wears a guild badge (rank {ws.rank})" if ws.rank else "wears no guild badge"))
    weapon = (c.equipment or {}).get("main_hand")
    if weapon:
        from engine import items
        out.append(Fact("player", f"carries a {items.base_of(weapon).name.lower()}"))
    crew = [p.name for p in scene.present_people() if p.kind in ("hire", "maren")]
    if crew:
        out.append(Fact("player", "travels with " + ", ".join(crew)))
    return out


_WORLD_WORDS: dict[int, frozenset] = {}


def world_words(world) -> frozenset:
    """(f323) The words of every name the world itself has - places, regions, peoples, the world's name - for checking what the pulse's
    writers say when no scene is standing. Cached per world."""
    key = id(world)
    if key not in _WORLD_WORDS:
        from engine import mentor
        names = {p.name for p in world.places.values()} | {r.name for r in world.regions.values()} | {p.name for p in world.peoples.values()}
        names |= {world.name, mentor.NAME} | {c.name for c in world.bestiary.values()}
        words = set()
        for n in names:
            words |= set(_WORD.findall((n or "").lower()))
        _WORLD_WORDS[key] = frozenset(words)
    return _WORLD_WORDS[key]


# ---------- the speech check (f315): nothing named that was not given

_NAME = r"[A-Z][a-z]{2,}(?:['’][a-z]+)?"
_RUN = re.compile(rf"{_NAME}(?:[ -]{_NAME})*")
_SENTENCE_END = re.compile(r"[.!?:;—–(\[\"'“‘]\s*$")
_NEGATED = re.compile(r"\b(?:no|not|never|without|lack\w*|isn't|wasn't|ain't|hasn't)\b|n't\b", re.I)
_ELSEWHERE = re.compile(r"^\s+(?:in|at|over in|down in|back in|up in|of)\s+[A-Z]")


def _given_words(given: str) -> set[str]:
    return set(_WORD.findall(given.lower()))


def coined(text: str, given: str, known=frozenset()) -> str:
    """A proper name in the speech that the speaker was not given: a run of capitalised words of which one is in neither the prompt nor the
    names the scene allows. A word that opens a sentence is not counted on its own (it is capitalised for that reason), but the rest of
    its run is. Returns the run, or ''."""
    have = _given_words(given) | set(known)
    for m in _RUN.finditer(text or ""):
        words = re.split(r"[ -]", m.group(0))
        if _SENTENCE_END.search(text[:m.start()]) or m.start() == 0:
            words = words[1:]
        for w in words:
            if w == "I" or w.lower().startswith("i'"):
                continue
            if re.sub(r"['’]s?$", "", w).lower() not in have:
                return " ".join(words)
    return ""


def absent_here(text: str, given: str) -> str:
    """A building the speech treats as being here when WHAT THIS TOWN HAS says the town has none: the town line, or ''. Spoken of as
    elsewhere ('the smithy in Lethoria') or as missing ('there's no smithy') is fine."""
    absent = {}
    for kind, line in re.findall(r"^\s*-?\s*(\w+): ((?:no \w+ building in|none in) .*)$", given, re.M):
        absent[kind] = f"{kind}: {line}"
    if not absent:
        return ""
    words = {w: kind for kind, ws in T["building_words"].items() if kind in absent for w in ws}
    pat = re.compile(r"\b(?:the|this|our|a|an|their|that)\s+(?:(?:village|town|local|old|new|little|big)\s+)?(" + "|".join(re.escape(w) for w in words) + r")\b", re.I)
    for m in pat.finditer(text or ""):
        before = text[max(0, m.start() - 40):m.start()]
        if _NEGATED.search(before) or _ELSEWHERE.match(text[m.end():m.end() + 30]):
            continue
        return absent[words[m.group(1).lower()]]
    return ""


def check_speech(text: str, given: str, known=frozenset()) -> str:
    """What is wrong with a line against what its speaker was told, as a complaint the gateway sends back, or ''."""
    run = coined(text, given, known)
    if run:
        return f"'{run}' is no one and nowhere you were told of; name only the people and places you were given, and nothing else by name"
    line = absent_here(text, given)
    if line:
        return f"you speak as if that were here, but the town has none ({line}); say what the town actually has"
    return ""
