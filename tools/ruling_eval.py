"""(f395) How well the dungeon master rules (engine/ruling.py), on the test set (data/replay/ruling_cases.yaml).

    python tools/ruling_eval.py            offline: for every case with a `model` ruling, what the engine makes of it (its own grounds:
                                           what the character can do); the cases without one need the model and are counted, not run
    python tools/ruling_eval.py --live     the real model rules on every case (needs Ollama): its sense against what a good dungeon
                                           master would say, and what it says the world needs

GOAL.md: "Investigate further into the cave" is met with more cave. "I grow wings and fly away" is not."""
from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import yaml

CASES = ROOT / "data" / "replay" / "ruling_cases.yaml"


def load(path=CASES) -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []


class Bench:
    def __init__(self, live: bool = False, save: str = "ruling_eval"):
        import simlib
        from llm import gateway as gw
        real = gw._client
        self.stub = simlib.Stub("warrior", 4)
        simlib.install(self.stub)
        if live:
            import types
            stub_chat = self.stub.chat
            gw._client = types.SimpleNamespace(chat=lambda **k: real.chat(**k) if (k.get("format") or {}).get("title") == "Ruling" else stub_chat(**k))
        import config
        import ui.console as uc
        for f in ("narrate", "say", "npc_says", "dialogue", "ledger", "note"):
            setattr(uc, f, lambda *a, **k: None)
        config.AUDIT_ENABLED = False
        config.REFUSALS_LOG = False
        from npc.traits import load_traits
        from scenes.world import WorldScene
        from storage.campaign import CampaignStore, PlayerState
        from world.loader import load_world
        self.save = save
        shutil.rmtree(ROOT / "saves" / save, ignore_errors=True)
        self.world = load_world()
        self.store = CampaignStore.open_or_create(save)
        self.store.meta.seed = 4; self.store.meta.minutes = 720; self.store.save_meta()
        char, _ = simlib.make_character("warrior", random.Random(1))
        char.level = 10
        self.store.save_player(PlayerState(character=char, location="trading_square"))
        self.ws = WorldScene(self.store, self.world, load_traits(), self.store.load_player())
        self.ws.player.mentor["never"] = True

    def put(self, case: dict) -> None:
        ws = self.ws
        if ws.player.location != case["at"]:
            ws.enter(case["at"])
        ws.player.character.capabilities = list(case.get("means") or [])

    def offline(self, case: dict) -> str | None:
        """'yes' or 'no', what the engine makes of the case's own ruling; None when the case has none."""
        from engine import ruling
        from llm.contracts import Ruling
        if not case.get("model"):
            return None
        self.put(case)
        r = Ruling.model_validate({"answer": "x", **case["model"]}, context={"capabilities": list(ruling.C)})
        return "yes" if ruling.verdict(self.ws, r)["ok"] else "no"

    def live(self, case: dict):
        from engine import ruling
        self.put(case)
        r = ruling.ask(self.ws, case["line"], case["line"])
        if r is None:
            return None, None
        return r, ("yes" if ruling.verdict(self.ws, r)["ok"] else "no")

    def close(self) -> None:
        self.store.close()
        shutil.rmtree(ROOT / "saves" / self.save, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()
    cases = load()
    b = Bench(live=a.live)
    right = wrong = skipped = 0
    try:
        for c in cases:
            want = "no" if c["expect"] == "no" else "yes"
            if a.live:
                r, got = b.live(c)
                if got is None:
                    print(f"  ?    {c['line']}  (the model gave no ruling)")
                    skipped += 1
                    continue
                needs = sorted({n.kind for n in r.needs})
                ok = got == want and (want == "no" or set(c.get("needs") or []) <= set(needs) or not c.get("needs"))
                print(f"  {'ok ' if ok else 'BAD'}  {c['line']}  -> {r.sense}{' (engine: no)' if got == 'no' and r.sense != 'no' else ''}, needs {needs or '-'}"
                      + (f"  [wanted {c['expect']}, needs {c.get('needs') or '-'}]" if not ok else ""))
            else:
                got = b.offline(c)
                if got is None:
                    skipped += 1
                    continue
                ok = got == want
                print(f"  {'ok ' if ok else 'BAD'}  {c['line']}  (means: {c.get('means') or 'none'}) -> {got}" + (f"  [wanted {want}]" if not ok else ""))
            right += ok
            wrong += not ok
    finally:
        b.close()
    print(f"\n{right} of {right + wrong} right" + (f"; {skipped} need the model (--live)" if skipped and not a.live else "")
          + (f"; {skipped} with no ruling" if skipped and a.live else ""))
    return 0 if not wrong or a.live else 1


if __name__ == "__main__":
    sys.exit(main())
