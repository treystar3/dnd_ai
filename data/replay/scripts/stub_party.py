"""(f476) The script of the kept recording stub_party (data/replay/sessions/stub_party): what stub_short, the night bot's walk, never
reaches. Bundle D changes the party's talk, a hire's canon, what townsfolk remember and are owed, and how a failed reply is taken back;
this session covers each, so every Bundle D step replays them before it is pushed. Recorded on the tree before Bundle D (f476), with
the stand-in model's answers planted where the stub would say nothing useful, and kept by tools/rerun.py --golden stub_party.

    the save   a warrior at Parth with three hires from the home hall, a hire who fell ninety days ago, the town's people
    the lines  a hire asked where they learned to fight, the others asked where they are from (each reply read for claims about
               themselves and a promise, the others chiming in as one exchange), then the same again; a farmer greeted
               with the party there; the run's lie, told to the farmer; work the farmer offers, taken and done; a request offered,
               taken and given up; the party told to hold back while something is lifted from the merchant out of their sight, then
               called back; a reply that fails, then the same line again

CENSUS (census()) is what the recording must hold, or the maker refuses it."""
from __future__ import annotations

import random
import shutil
from pathlib import Path

SEED = 52
SAVE = "rerun_make_stub_party"
LIE = "Vosk Hallarin"


ABOUT_WORDS = ("grew up", "come from", "where are you from", "father", "mother", "family", "learn to fight", "past")


def _topic_embedder():
    import simlib

    class TopicEmbedder(simlib.FakeEmbedder):
        """The stand-in embedding model with one planted sense: talk of someone's past and where they come from lies close together,
        so the canon's 'was this about them' (engine/canon.py worth_reading) holds for the hire's answer as a real model's would. The
        vectors are recorded with the calls, so a replay serves them as made."""
        def vec(self, text):
            v = super().vec(text)
            low = str(text).lower()
            hits = sum(w in low for w in ABOUT_WORDS)
            return v + [8.0 * hits]
    return TopicEmbedder


def record(folder: Path, root: Path) -> Path:
    import sys
    sys.path.insert(0, str(root / "tools"))
    import simlib
    stub = simlib.Stub("warrior", SEED)
    held = simlib.install(stub)
    from core.models import Entity
    from engine.session import CampaignSession
    from npc.traits import load_traits
    from storage.campaign import PlayerState
    from engine import recording
    from ui import console
    import nightrun

    shutil.rmtree(root / "saves" / SAVE, ignore_errors=True)
    session = CampaignSession.open(SAVE)
    store = session.store
    store.meta.seed, store.meta.turn, store.meta.minutes = SEED, 1, 8 * 60 + 600 * 1440
    store.save_meta()
    char, _ = simlib.make_character("warrior", random.Random(SEED))
    char.level = 6
    player = PlayerState(character=char, location="parth")
    player.mentor["never"] = True
    player.guild_rank = "F"
    store.save_player(player)
    for name in recording.STORY:
        if hasattr(console, name):
            setattr(console, name, lambda *a, **k: None)
    console.panel = lambda name, data: False
    for name in ("out", "status_block", "combat_state", "show_header", "debug"):
        if hasattr(console, name):
            setattr(console, name, lambda *a, **k: None)
    ws = session.scene(load_traits(), store.load_player())
    nightrun.hire_party(ws, 3)
    store.save_entity(Entity(ref="hire:fallen_corwin", kind="hire", name="Corwin Ashby", pronoun="he", people="human", state="dead",
                             since=store.meta.minutes - 90 * 1440, data={"role": "fighter", "place_name": "the Greywood", "how": "a wolf pack"}))
    ws.enter("parth")
    store.save_player(ws.player)
    session.close()                                                # the recording starts from the save as a replay opens it: a fresh scene
    session = CampaignSession.open(SAVE)
    store = session.store
    ws = session.scene(load_traits(), store.load_player())
    hires = [m["name"] for m in ws.player.party]
    first = hires[0].split()[0] if hires else "friend"
    farmer = next((n for n in ws.present if n.role == "farmer"), None) or (ws.present[0] if ws.present else None)
    merchant = next((n for n in ws.present if n.role == "merchant" and n is not farmer), None) or \
        next((n for n in ws.present if n is not farmer), None)

    fail = {"on": False}
    from llm import embed as _embed
    TopicEmbedder = _topic_embedder()
    fake = TopicEmbedder()                                         # the stand-in embedding model, the same in every process

    def chat(**k):
        if fail["on"] and k["format"].get("title") == "NPCReply":
            raise ConnectionError("the model server cannot be reached")    # every try of this input fails: the line is not taken
        return stub.chat(**k)
    planted = simlib.stand_in(chat=chat, embed=fake.embed)        # (f518) the stub, its failure and the embedder, as a source: the
    _embed.reset()                                                 # embedder is the stand-in's (its facts), fixed for the recording

    def companion(u):
        return {"speech": "In a town militia up north, before it broke. I'll see you as far as the next town, that much I promise.",
                "gesture": "taps the hilt", "remember": "", "impression": ""}

    said = {"n": 0}

    def extract(u):
        import re as _re
        known = u.split("WHAT WAS JUST SAID", 1)[0]
        said_now = u.split("WHAT WAS JUST SAID:", 1)[-1]
        speakers = [m.group(1).strip() for m in _re.finditer(r"^\s{2}([^:\n]+):", said_now, _re.M)]
        who = speakers[0] if speakers else (hires[0] if hires else "")
        said["n"] += 1                                             # once it is known, they tell it a little differently: the canon is checked
        mine = next((l for l in known.splitlines() if l.strip().startswith(who + ":")), "")
        past = ("learned to fight in a city militia down south, before it broke" if "town militia up north" in mine
                else "learned to fight in a town militia up north, before it broke")
        return {"facts": [{"speaker": who, "subject": "self", "kind": "backstory", "text": past, "weight": "personal"},
                          {"speaker": who, "subject": "self", "kind": "commitment", "text": "will see the player as far as the next town",
                           "weight": "personal", "lasts": "while"}]}
    others = hires[1:]

    def overheard(u):
        return {"about": list(others), "party": True, "weight": "personal"}

    def exchange(names, first_msg):
        talk = {0: "Up north too, though I came to it late.", 1: "A fishing town on the cold coast. I left at fifteen."}
        return [{"speaker": n, "text": talk.get(i % 2, "Here and there.")} for i, n in enumerate(names[:2])] * 1
    stub.companion, stub.extract, stub.overheard, stub.exchange = companion, extract, overheard, exchange
    reply = {"now": None}
    real_reply = stub.a_NPCReply

    def npc_reply(u, k):
        return reply["now"] or real_reply(u, k)
    stub.a_NPCReply = npc_reply
    fid = farmer.id if farmer else ""
    mid = merchant.id if merchant else ""
    steps = [
        (f"{first}, where did you learn to fight? " + " and ".join(o.split()[0] for o in others) + ", where are you from?", [{"kind": "look"}], None),
        (f"{first}, where did you learn to fight? " + " and ".join(o.split()[0] for o in others) + ", where are you from?", [{"kind": "look"}], None),
        ("I go over to the farmer and say good morning.", [{"kind": "talk", "target": fid, "speech": "Good morning."}],
         {"speech": "Morning to you. Fine day for it.", "intent": "small_talk"}),
        (f'"My name is {LIE}, by the way."', [{"kind": "talk", "target": fid, "speech": f"My name is {LIE}, by the way."}],
         {"speech": f"Well met, {LIE}.", "intent": "small_talk", "learned_player_name": LIE,
          "remember": f"A traveller who gave the name {LIE} stopped to talk."}),
        ('"Is there any work going?"', [{"kind": "talk", "target": fid, "speech": "Is there any work going?"}],
         {"speech": "The fence by the barn wants mending, if you've the hands for it.", "intent": "help",
          "offers_work": {"task": "mend the fence by the barn", "pay": 30, "minutes": 60}}),
        ('"I\'ll take the work."', [{"kind": "work", "target": fid}], None),
        ('"Anything else I could help with?"', [{"kind": "talk", "target": fid, "speech": "Anything else I could help with?"}],
         {"speech": "Wolves have been at the fold. Thin them out and I'll pay.", "intent": "help",
          "offers_quest": {"kind": "hunt", "what": "wolves", "count": 3}}),
        ('"I\'ll do it."', [{"kind": "accept_quest", "target": fid}], None),
        ("I give up the wolf contract.", [{"kind": "abandon_quest", "item": "wolves"}], None),
        ("Hold back, all of you.", [{"kind": "look"}], None),
        ("I slip a trinket off the merchant's stall.", [{"kind": "steal", "target": mid, "item": "a trinket"}], None),
        ("Come with me.", [{"kind": "look"}], None),
        ("I ask the farmer whether rain is coming.", [{"kind": "talk", "target": fid, "speech": "Is rain coming, do you think?"}], "fail"),
        ("I ask the farmer whether rain is coming.", [{"kind": "talk", "target": fid, "speech": "Is rain coming, do you think?"}],
         {"speech": "By nightfall, I'd say. Feel it in the knee.", "intent": "share"}),
    ]
    count = {"n": 0}

    def ask(*a, **k):
        if not k.get("main", a[0] if a else False):
            return "yes"
        n = count["n"]
        count["n"] += 1
        if n >= len(steps):
            return "quit"
        text, plan, planted = steps[n]
        stub.plan = plan
        fail["on"] = planted == "fail"
        reply["now"] = planted if isinstance(planted, dict) else None
        return text
    console.ask = ask
    session.record(folder=folder, rows=True)
    try:
        ws.run()
    finally:
        session.close()
        planted()
        held()
        _embed.reset()
        shutil.rmtree(root / "saves" / SAVE, ignore_errors=True)
    return folder


CENSUS = ("CompanionReply", "Extracted", "Exchange", "Overheard", "NPCReply", "NPCProfile")
# Not here: CanonCheck. Under the stand-in model a claim read from the party's talk is never kept before the next one is read, so the
# check against what is already true of a hire is not reached; it is tested on its own (tools/sim/canon tests), not through this session.


def census(rec: dict) -> list[str]:
    """What the recording must hold: each title below at least once, a reply that failed and was said again, the party held and called
    back, and the fallen hire in the save it starts from."""
    titles = {c.get("title") for c in rec["calls"]}
    missing = [t for t in CENSUS if t not in titles]
    if not any(c.get("title") == "NPCReply" and c.get("error") for c in rec["calls"]):
        missing.append("a failed NPCReply")
    texts = [i.get("text", "") for i in rec["inputs"] if i.get("main")]
    if "Hold back, all of you." not in texts or "Come with me." not in texts:
        missing.append("the party held and called back")
    if LIE not in " ".join(texts):
        missing.append("the lie")
    return missing
