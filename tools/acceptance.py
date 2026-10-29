"""(f393) Scripted scenes: the goal's acceptance tests, played through the real turn on a real scene (data/replay/scenes.yaml).

    python tools/acceptance.py                 every scene, with the stand-in model: what the engine does around the model's answers
    python tools/acceptance.py --only tidepool the scenes whose name holds one of these words
    python tools/acceptance.py --live          the interpreter and the ruling are the real model's (needs Ollama); the rest stays stubbed

A scene: where it starts, then steps. Each step types a line (`say`) and, with the stand-in model, says what the model reads from it
(`reads`: the interpreter's plan; `ruling`: the dungeon master's ruling, slice 2). `wait` lets minutes pass first; `reopen` saves and
opens the save again, as a player coming back would. `then` is what must be true afterwards:

    place, spot             where the player is (a place id; a part of the place, by a word of its name)
    knows                   parts of this place the game knows, by a word of their name
    note_has, note_not      words in what the game noted this step
    told_has, told_not      words in what the narrator was told this step (its GAME EVENT)
    facade                  false: no facade or dead end was met (refusals of kind facade / dead_end)
    refused                 true: the game said no (a refusal of kind refused); false: it did not
    made                    at least this many additions to the world this step (the turn's record, kind made)
    entity                  {kind, name, state}: someone or something in the registry
    fight                   a creature of this kind is in the fight now

Every scene belongs to a slice of the build plan (`slice`). Scenes of a slice not built yet (BUILT) are expected to fall short, and are
reported, not failed: they say how far the game is from the goal."""
from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import yaml

SCENES = ROOT / "data" / "replay" / "scenes.yaml"
BUILT = 1                     # the slices of the build plan built so far


def load(path=SCENES) -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []


class Table:
    """One scene's game: a fresh save, a character, the stand-in model, and what the game noted and told."""

    def __init__(self, scene: dict, live: bool = False):
        import simlib
        from llm import gateway as gw
        real = gw._client
        st = scene.get("start") or {}
        self.stub = simlib.Stub(st.get("class", "warrior"), int(st.get("seed", 4)))
        simlib.install(self.stub)
        import types
        stub_chat = self.stub.chat
        self.told: list[str] = []

        def chat(**k):
            title = (k.get("format") or {}).get("title")
            if title == "Narration":
                import re
                m = re.search(r"GAME EVENT: (.*)", k["messages"][-1]["content"])
                if m:
                    self.told.append(m.group(1))
            if live and title in ("ActionPlan", "Ruling"):
                return real.chat(**k)
            return stub_chat(**k)
        gw._client = types.SimpleNamespace(chat=chat)
        import config
        import ui.console as uc
        self.notes: list[str] = []
        for f in ("narrate", "say", "npc_says", "dialogue", "ledger"):
            setattr(uc, f, lambda *a, **k: None)
        uc.note = lambda m, *a, **k: self.notes.append(str(m))
        uc.ask = lambda *a, **k: ""
        from engine import refusals
        self.refusals = refusals
        from npc.traits import load_traits
        from scenes.world import WorldScene
        from storage.campaign import CampaignStore, PlayerState
        from world.loader import load_world
        self.save = f"scene_{scene['name']}"[:60]
        shutil.rmtree(ROOT / "saves" / self.save, ignore_errors=True)
        config.TURN_LOG_PATH = f"saves/{self.save}/turns.jsonl"
        config.AUDIT_ENABLED = False
        config.REFUSALS_LOG = False
        self.world = load_world()
        self.store = CampaignStore.open_or_create(self.save)
        self.store.meta.seed = int(st.get("seed", 4)); self.store.meta.turn = 1
        self.store.meta.minutes = int(st.get("minutes", 600)); self.store.save_meta()
        char, _ = simlib.make_character(st.get("class", "warrior"), random.Random(int(st.get("seed", 4))))
        char.level = int(st.get("level", 10))
        if st.get("capabilities") and "capabilities" in type(char).model_fields:        # (slice 2) granted by the story or an item
            char.capabilities = list(st["capabilities"])
        self.store.save_player(PlayerState(character=char, location=st.get("place", "trading_square"), guild_rank=st.get("rank", "E")))
        self.WorldScene, self.CampaignStore, self.load_traits = WorldScene, CampaignStore, load_traits
        self.ws = WorldScene(self.store, self.world, load_traits(), self.store.load_player())
        self.ws.player.mentor["never"] = True
        self.ws.enter(st.get("place", "trading_square"))
        from engine import inventory
        for good in st.get("pack") or []:
            self.ws.to_pack(inventory.make_good(good, 1))
        if st.get("coins") is not None:
            self.ws.player.character.coins = int(st["coins"])
        from npc.models import NPC
        for p in st.get("present") or []:                     # people standing here, as the scene needs them
            n = NPC(id=p["id"], name=p.get("name", p["id"]), gender=p.get("gender", "male"), people=p.get("people", "human"),
                    role=p.get("role", "merchant"), location=self.ws.player.location, traits=[], trust=50)
            self.store.save_npc(n)
            self.ws.residents = self.ws.residents + [n]
            self.ws.present = self.ws.present + [n]

    def reopen(self) -> None:
        self.ws.save()
        self.store.close()
        self.store = self.CampaignStore.open_or_create(self.save)
        self.ws = self.WorldScene(self.store, self.world, self.load_traits(), self.store.load_player())
        self.ws.player.mentor["never"] = True
        self.ws.enter(self.ws.player.location)

    def step(self, s: dict) -> list[str]:
        """Play one step; what fell short of `then`, as lines."""
        if s.get("wait"):
            self.ws.advance(int(s["wait"]))
        if s.get("reopen"):
            self.reopen()
        self.notes.clear(); self.told.clear()
        before = len(self.refusals.SESSION)
        made_before = self.made()
        self.coins_before = self.ws.player.character.coins
        if s.get("say"):
            self.stub.plan = list(s.get("reads") or [{"kind": "look"}])
            self.stub.ruling = s.get("ruling")
            self.ws.turn(s["say"])
        kinds = [r["kind"] for r in self.refusals.SESSION[before:]]
        return [f"{s.get('say') or s.get('wait') or 'reopen'}: {why}" for why in self.expect(s.get("then") or {}, kinds, self.made() - made_before)]

    def made(self) -> int:
        """Additions to the world so far, from the turn's record (slice 1)."""
        try:
            from engine import ledger
            return ledger.count("made")
        except Exception:
            return 0

    def spot_name(self) -> str:
        spot = getattr(self.ws.player, "spot", "") or ""
        e = self.store.load_entity(spot) if spot else None
        return (e.name if e else spot).lower()

    def expect(self, t: dict, kinds: list[str], made: int) -> list[str]:
        out = []
        ws = self.ws
        notes, told = " | ".join(self.notes).lower(), " | ".join(self.told).lower()
        for key, want in t.items():
            if key == "place" and ws.player.location != want:
                out.append(f"at {ws.player.location}, not {want}")
            elif key == "spot" and str(want).lower() not in self.spot_name():
                out.append(f"standing at '{self.spot_name() or 'nowhere in particular'}', not at the {want}")
            elif key == "knows":
                have = [e.name.lower() for e in self.store.find_entities(kind="feature", place=ws.player.location)]
                for w in want:
                    if not any(w.lower() in h for h in have):
                        out.append(f"the game does not know of the {w} here (it knows: {have or 'nothing'})")
            elif key == "note_has":
                out += [f"no note says '{w}' ({notes[:200] or 'no notes'})" for w in want if w.lower() not in notes]
            elif key == "note_not":
                out += [f"a note says '{w}'" for w in want if w.lower() in notes]
            elif key == "told_has":
                out += [f"the narrator was not told '{w}' ({told[:200] or 'told nothing'})" for w in want if w.lower() not in told]
            elif key == "told_not":
                out += [f"the narrator was told '{w}'" for w in want if w.lower() in told]
            elif key == "facade" and want is False and any(k in ("facade", "dead_end") for k in kinds):
                out.append("met a facade: " + ", ".join(k for k in kinds if k in ("facade", "dead_end")))
            elif key == "refused" and bool(want) != ("refused" in kinds):
                out.append("the game did not say no" if want else "the game said no")
            elif key == "made" and made < int(want):
                out.append(f"{made} additions to the world, not {want}")
            elif key == "entity":
                hits = [e for e in self.store.find_entities(kind=want.get("kind", "")) if want.get("name", "").lower() in e.name.lower()
                        and (not want.get("state") or e.state == want["state"])]
                if not hits:
                    out.append(f"no {want.get('kind')} '{want.get('name', '')}'" + (f" in state {want['state']}" if want.get("state") else ""))
            elif key == "present":
                if not any(want.lower() in f"{n.label()} {n.name} {n.role}".lower() for n in ws.present):
                    out.append(f"nobody here is a {want} ({[n.label() for n in ws.present][:6]})")
            elif key == "has":
                from engine import inventory
                labels = " | ".join(inventory.label(i) for i in ws.player.character.inventory).lower()
                out += [f"the pack no longer holds {w}" for w in want if w.lower() not in labels]
            elif key == "coins_spent" and bool(want) != (ws.player.character.coins < self.coins_before):
                out.append("no coins changed hands" if want else "coins were spent")
            elif key == "fight":
                fight = getattr(ws, "combat", None)
                kinds_ = [e.creature for e in fight.fight.enemies()] if fight else []
                if want not in kinds_:
                    out.append(f"no {want} in a fight ({kinds_ or 'no fight'})")
            elif key not in ("place", "spot", "note_has", "note_not", "told_has", "told_not", "facade", "refused", "made", "coins_spent"):
                out.append(f"unknown expectation '{key}'")
        return out

    def close(self) -> None:
        self.store.close()
        shutil.rmtree(ROOT / "saves" / self.save, ignore_errors=True)


def play(scene: dict, live: bool = False) -> list[str]:
    t = Table(scene, live)
    try:
        out = []
        for s in scene.get("steps") or []:
            out += t.step(s)
        return out
    except Exception as e:
        import traceback
        return [f"broke: {type(e).__name__}: {e} ({traceback.format_exc().strip().splitlines()[-3][:160]})"]
    finally:
        t.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()
    words = [w for w in a.only.split(",") if w]
    bad, ahead = 0, 0
    for sc in load():
        if words and not any(w in sc["name"] for w in words):
            continue
        short = play(sc, a.live)
        due = sc.get("slice", 0) <= BUILT
        tag = "ok  " if not short else ("FAIL" if due else "todo")
        print(f"{tag} [{sc.get('slice', 0)}] {sc['name']}: {sc.get('about', '')}")
        for line in short:
            print(f"       {line}")
        bad += bool(short) and due
        ahead += bool(short) and not due
    print(f"\n{'ALL PASS' if not bad else f'FAILED: {bad}'}" + (f" ({ahead} scene(s) for slices not built yet still fall short)" if ahead else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
