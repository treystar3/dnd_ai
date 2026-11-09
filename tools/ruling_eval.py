"""(f395) How well the dungeon master rules (engine/ruling.py), on the test set (data/replay/ruling_cases.yaml).

    python tools/ruling_eval.py            offline: for every case with a `model` ruling, what the engine makes of it (its own grounds:
                                           what the character can do); the cases without one need the model and are counted, not run
    python tools/ruling_eval.py --live     the real model rules on every case (the game's own server, tools/runtime_cli.py): its sense against what a good dungeon
                                           master would say, and what it says the world needs
    python tools/ruling_eval.py --live --cases data/replay/ruling_cases_complex.yaml     (f534) the improvised actions of several steps

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
    def __init__(self, live: bool = False, save: str = "ruling_eval", source=None):
        import simlib
        from llm import backend
        self.stub = simlib.Stub("warrior", 4)
        self.unstub = simlib.install(self.stub)              # (f518) the stub as the model's source; its Held takes it away again
        self.unlive = None
        if live:                                             # (f518) the ruling is passed on to the real model (f529: the server `source`); the rest stays stubbed
            stub_chat = self.stub.chat
            self.unlive = simlib.stand_in(chat=lambda **k: backend.PASS if (k.get("format") or {}).get("title") == "Ruling" else stub_chat(**k),
                                          name="ruling_eval live", below=source)
        import config
        import ui.console as uc
        for f in ("narrate", "say", "npc_says", "dialogue", "ledger", "note"):
            setattr(uc, f, lambda *a, **k: None)
        config.AUDIT_ENABLED = False
        config.REFUSALS_LOG = False
        from engine.session import CampaignSession
        from npc.traits import load_traits
        from storage.campaign import PlayerState
        self.save = save
        shutil.rmtree(ROOT / "saves" / save, ignore_errors=True)
        self.session = CampaignSession.open(save)                           # (f457) the campaign's session, as main.py opens it
        self.store, self.world = self.session.store, self.session.world
        self.store.meta.seed = 4; self.store.meta.minutes = 720; self.store.save_meta()
        char, _ = simlib.make_character("warrior", random.Random(1))
        char.level = 10
        self.store.save_player(PlayerState(character=char, location="trading_square"))
        self.ws = self.session.scene(load_traits(), self.store.load_player())
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
        self.session.close()
        if self.unlive is not None:
            self.unlive()                   # (f518) this bench's stand-ins away again, the live route first
        self.unstub()
        shutil.rmtree(ROOT / "saves" / self.save, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--cases", default=str(CASES), help="(f534) another case file, e.g. data/replay/ruling_cases_complex.yaml")
    from tools import runtime_cli
    runtime_cli.add_args(ap)
    a = ap.parse_args()
    cases = load(a.cases)
    server = runtime_cli.load(a) if a.live else None            # (f529) the game's own server, as the game starts it
    b = Bench(live=a.live, source=server.source if server is not None else None)
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
        if server is not None:
            server.close()
    print(f"\n{right} of {right + wrong} right" + (f"; {skipped} need the model (--live)" if skipped and not a.live else "")
          + (f"; {skipped} with no ruling" if skipped and a.live else ""))
    return 0 if not wrong or a.live else 1


if __name__ == "__main__":
    sys.exit(main())
