# 4. Easy performance wins: tested patch

File: `perf_easy_wins.patch` (110 files, +274/-130). It applies cleanly to 06b393c with `git apply`. It's not committed or pushed
anywhere.

## What it changes
1. **`core/yamlio.py` (new):** `safe_load()` on libyaml's `CSafeLoader` when PyYAML has it, otherwise the pure-Python `SafeLoader`.
   All 129 `yaml.safe_load(` call sites in the game (not `tools/`) now use it. That's a mechanical replacement plus one import per file
   (after `from __future__` where a file has one; the import inside a function in `engine/clock.py` is handled).
2. **`engine/mapview.py layout()`:**
   - When every top-level place already has a drawn position (`data/world/map.yaml`) or its own x/y, the 400-step force-directed layout
     is skipped. Its result was being thrown away.
   - Otherwise, the result is memoised by its inputs (graph, regions, own and drawn positions), never by which world it belongs to, as
     f452 requires.
   - Each world gets its own copy of the dict.

## Checks
- **Identical data:** all 131 YAML files in the repo load to equal Python objects with both loaders.
- **Identical map:** `layout()` output is byte-for-byte the same before and after (all 82 top-level places are drawn).
- **Recording:** `stub_party` replays unchanged ("all 15 inputs matched").
- **Full suite** (Python 3.11): the same failures as the untouched tree, with no new ones. Those are the environment failures from
  before: five need Python 3.12 and seven are line-ending or data-hash goldens. `map_caches_452_test`, which checks each world's layout
  is its own object, passes after the per-world copy.

## Measured gains (my machine, without the profiler)
| What | Before | After |
|---|---|---|
| Reading all 131 data YAML files | 2.35 s | 0.26 s |
| `load_world()` in a fresh process | 0.86 s | 0.26 s |
| `mapview.layout()`, first call | 0.51 s | 0.002 s |
| Whole `stub_party` replay (process start, world load, 15 inputs) | 5.3–5.6 s | 2.8–3.0 s |
| Full suite wall time (`-j 16`) | 470 s | 270 s* |

\*The suite timings were on a shared machine and aren't a controlled comparison, but the direction is consistent with the YAML gain.

For players, this means faster loading and a faster first move after loading. Per-turn time in the middle of a session barely changes,
because the model dominates it.

## Notes
- **Shipping:** PyInstaller has to bundle PyYAML's `_yaml` C extension (it does by default when it's installed). Without it, `yamlio`
  falls back to the pure-Python loader and still works.
- **The data hash is unchanged,** because it hashes file bytes.
- **Later finding (f560, f572):** when this patch was applied the goldens did fail on their data hash, but neither the patch nor line
  endings were the cause. They had been recorded on VERSION 0.0.4.1, and the hash then included the version. f560 re-blessed them
  (only the hash moved); f572 took the version out of the hash.

## Not done (low value or needs a decision)
- **The route cache's validity check walks every place on each lookup** (`world/loader.py:271`). It costs milliseconds per turn now. A
  version counter on the authored world would fix it, but I left it because the f426 safety it provides is subtle.
- **Importing modules during the model load:** worthwhile, but it touches `main.py`'s startup order. Worth doing with the owner.
- **Model-side wins (prompt-start layout, conversation prompt size, code repairs before retries, `q8_0` KV):** these need night runs
  to measure. See my earlier answer.
