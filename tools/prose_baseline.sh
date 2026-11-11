#!/usr/bin/env bash
# (f575) One prose measurement on the game's own model (docs/design/09 section A), run on a machine with the model files in place (a pod):
#   bash tools/prose_baseline.sh OUT_DIR
# 1. tools/live_check.py --runs 3              townsfolk conversation, judged (its report: OUT/live_check_report.md)
# 2. tools/interp_eval.py --live               how the game reads typed lines (a shorter prompt must not cost it: OUT/interp_eval.txt)
# 3. scripted plays (tools/nightrun.py), each with a hired party of 3, so narration, fights, the party's exchanges and frames are
#    written: four hunters (fights, seeds 101, 103, 105, 107: enough fights to draw 20 of them, f577) and a talker (talk, seed 102),
#    60 turns each
# 4. tools/prose_measure.py over every call log: OUT/prose.md (the table and sample passages) and OUT/prose.json (to compare against)
# Every call is kept: DND_LOG_MAX_MB lifts the call log's trim for the run.
set -euo pipefail
OUT="${1:?usage: bash tools/prose_baseline.sh OUT_DIR}"
mkdir -p "$OUT"
export DND_LOG_MAX_MB=100000 PYTHONUTF8=1
LOG=logs/llm_calls.jsonl
fresh_log() { mkdir -p logs; rm -f "$LOG"; }

echo "== live_check --runs 3"
fresh_log
python tools/live_check.py --runs 3 --report prose_live_check.md
cp saves/prose_live_check.md "$OUT/live_check_report.md"
mv "$LOG" "$OUT/live_check_calls.jsonl"

echo "== interp_eval --live"
fresh_log
python tools/interp_eval.py --live | tee "$OUT/interp_eval.txt" || echo "interp_eval counted wrong readings (it exits non-zero then); the count is kept and the measurement goes on"
[ -f "$LOG" ] && mv "$LOG" "$OUT/interp_calls.jsonl" || true

for play in "hunter 101" "talker 102" "hunter 103" "hunter 105" "hunter 107"; do
  set -- $play
  echo "== scripted play: $1 (seed $2)"
  python tools/nightrun.py --persona "$1" --seed "$2" --party 3 --turns 60 --hours 3 --out "$OUT/play_$1_$2" --save "prose_$1_$2"
done

echo "== prose measures"
mapfile -t LOGS < <(find "$OUT" -name '*calls*.jsonl' ! -name 'interp_calls.jsonl' | sort)
python tools/prose_measure.py "${LOGS[@]}" --json "$OUT/prose.json" --samples 4 | tee "$OUT/prose.md"
