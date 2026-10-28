#!/usr/bin/env bash
# (f370) A night of runs on a rented Linux box with an NVIDIA card (RunPod, Lambda, any Ubuntu): tools/HOSTED.md has the steps around it.
#
#     RUNS=5 HOURS=2 PARALLEL=2 bash tools/runpod_night.sh
#
# Installs Ollama when the box has none, starts it with room for PARALLEL requests at once, pulls the game's models, installs the game's
# libraries, plays RUNS runs of HOURS hours (PARALLEL at a time, tools/nightrun.py), and zips every log under out/ to carry home.
# Everything the night needs is on the box; nothing reaches the machine you started it from but the zip you download.
set -euo pipefail
cd "$(dirname "$0")/.."

RUNS="${RUNS:-5}"
HOURS="${HOURS:-2}"
PARALLEL="${PARALLEL:-1}"
OUT="${OUT:-logs/nightrun}"
EXTRA="${EXTRA:-}"                              # anything else for tools/nightrun.py: --starts veteran,legend --personas hunter,talker --level 40
MODEL="$(python3 -c 'import config; print(config.MODEL)')"
EMBED="$(python3 -c 'import config; print(config.EMBED_MODEL)')"
mkdir -p logs out

if ! command -v ollama >/dev/null 2>&1; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi
if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "Starting Ollama with room for $PARALLEL request(s) at once..."
    (OLLAMA_NUM_PARALLEL="$PARALLEL" OLLAMA_KEEP_ALIVE=30m setsid nohup ollama serve > logs/ollama.log 2>&1 < /dev/null &)   # its own session: outlives the shell that started it
    for _ in $(seq 1 60); do
        curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
        sleep 1
    done
fi
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || true
ollama pull "$MODEL"
ollama pull "$EMBED"
python3 -m pip install -q -r requirements.txt

echo "A night of $RUNS run(s), $HOURS h each, $PARALLEL at a time: $MODEL"
# shellcheck disable=SC2086
python3 tools/nightrun.py --runs "$RUNS" --hours "$HOURS" --parallel "$PARALLEL" --out "$OUT" $EXTRA || true

STAMP="$(date +%Y%m%d_%H%M)"
python3 - "$OUT" "out/night_$STAMP.zip" <<'EOF'
import sys, zipfile
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(src.rglob("*")):
        if p.is_file():
            z.write(p, p.relative_to(src.parent))
print(f"Logs zipped: {dst} ({dst.stat().st_size // 1_000_000} MB)")
EOF
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || true
echo "Done. Download the zip, then terminate the pod (a stopped pod still bills for its disk)."
