"""(f537) The prompt cache's shape is settings, measured before any change: the RAM cache's size, the context checkpoints a slot keeps,
the KV cache's type and whether an idle slot is saved to the RAM cache reach llama-server's launch line from data/runtime/server.yaml
(outside the data hash), and the settings check names a bad value. The shipped values are the ones the 7 Nov pod night measured best:
the server's own defaults, with the RAM cache off (the owner's choice)."""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from llm import runtime  # noqa: E402

bad = []


def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {extra}"))
    if not ok:
        bad.append(name)


def val(args, flag):
    return args[args.index(flag) + 1] if flag in args else None


cfg = runtime.settings()
s = cfg["server"]
check("the shipped shape is the one the 7 Nov pod measured best and the owner chose: 32 checkpoints, f16, idle slots saved, no RAM cache",
      (s["ctx_checkpoints"], s["kv_type"], s["cache_idle_slots"], s["cache_ram_mib"]) == (32, "f16", True, 0), (s["ctx_checkpoints"], s["kv_type"], s["cache_idle_slots"], s["cache_ram_mib"]))
check("...and passes the settings check", not [p for p in runtime.runtime_problems(cfg) if "kv_type" in p or "idle" in p or "checkpoints" in p])
exe, models = Path("/x/llama-server"), Path("/m")
a = runtime.chat_argv(exe, cfg, 1234, "k", models)
check("the launch line carries them: the checkpoints, the KV type for K and V alike, the idle-slot saving, the cache cap",
      val(a, "--ctx-checkpoints") == "32" and val(a, "-ctk") == "f16" and val(a, "-ctv") == "f16" and "--cache-idle-slots" in a
      and "--no-cache-idle-slots" not in a and val(a, "--cache-ram") == "0", [x for x in a if "cache" in x or x in ("-ctk", "-ctv")])
other = copy.deepcopy(cfg)
other["server"].update(ctx_checkpoints=4, kv_type="q8_0", cache_idle_slots=False, cache_ram_mib=6144)
b = runtime.chat_argv(exe, other, 1234, "k", models)
check("another shape reaches the line as set", val(b, "--ctx-checkpoints") == "4" and val(b, "-ctk") == "q8_0" and val(b, "-ctv") == "q8_0"
      and "--no-cache-idle-slots" in b and "--cache-idle-slots" not in b and val(b, "--cache-ram") == "6144", [x for x in b if "cache" in x or x in ("-ctk", "-ctv")])
check("...and passes the check too (every type the server knows)", not [p for p in runtime.runtime_problems(other) if "kv_type" in p]
      and all(t in runtime.KV_TYPES for t in ("f32", "f16", "bf16", "q8_0", "q4_0", "q4_1", "q5_0", "q5_1", "iq4_nl")))
wrong = copy.deepcopy(cfg)
wrong["server"].update(ctx_checkpoints=-1, kv_type="q3_k", cache_idle_slots="yes")
probs = runtime.runtime_problems(wrong)
check("a bad value is named: a negative checkpoint count, a type the server has not, a saving that is not true or false",
      any("ctx_checkpoints" in p for p in probs) and any("kv_type" in p and "q8_0" in p for p in probs) and any("cache_idle_slots" in p for p in probs), probs)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
