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

# A path that drops big packets (seen on Runpod: 1,300-byte packets pass, 1,400 do not) stalls every download. MSS_PROXY=1 routes the
# installs and the pulls through tools/mss_proxy.py, which caps its outbound segments; the game's own calls to Ollama stay local.
if [ "${MSS_PROXY:-0}" = "1" ]; then
    if ! curl -sS -o /dev/null -m 5 -x http://127.0.0.1:3128 https://ollama.com/ 2>/dev/null; then
        (setsid nohup python3 tools/mss_proxy.py --port 3128 > logs/mss_proxy.log 2>&1 < /dev/null &)
        sleep 1
    fi
    export HTTPS_PROXY=http://127.0.0.1:3128 HTTP_PROXY=http://127.0.0.1:3128 https_proxy=http://127.0.0.1:3128 http_proxy=http://127.0.0.1:3128
    export NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
    echo "Downloads go through the segment-capping proxy (MSS_PROXY=1)."
fi

if ! command -v ollama >/dev/null 2>&1; then
    echo "Installing Ollama..."
    if ! command -v zstd >/dev/null 2>&1; then          # (f445) Ollama's installer unpacks with zstd, which some images lack
        (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq zstd) > /dev/null 2>&1 || true
    fi
    curl -fsSL https://ollama.com/install.sh | sh
fi
# A container may see every core of the host (nproc 128) while its quota is a dozen; the model runner then spawns a thread per core
# seen and they fight over the quota, and a 5090 ran at a tenth of its speed. Pinning the server to as many cores as the quota allows
# (the runner inherits the pinning) gave the card its full speed: 4,700 tokens/s read, 200 written, up from 580 and 25.
PIN=""
if command -v taskset >/dev/null 2>&1 && [ -r /sys/fs/cgroup/cpu.max ]; then
    read -r QUOTA PERIOD < /sys/fs/cgroup/cpu.max
    if [ "$QUOTA" != "max" ] && [ "$QUOTA" -gt 0 ] 2>/dev/null; then
        CORES=$(( (QUOTA + PERIOD - 1) / PERIOD ))
        if [ "$CORES" -lt "$(nproc)" ]; then
            PIN="taskset -c 0-$((CORES - 1))"
            echo "Pinning Ollama to $CORES cores (the container's quota; nproc says $(nproc))."
            if [ "${DND_NUM_THREAD:-0}" = "0" ]; then
                export DND_NUM_THREAD=$(( CORES / 2 > 2 ? CORES / 2 : 2 ))   # the runner's threads, else it spawns one per core shown and they fight
            fi
            echo "The model runner gets $DND_NUM_THREAD threads (DND_NUM_THREAD)."
        fi
    fi
fi
if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "Starting Ollama with room for $PARALLEL request(s) at once..."
    (OLLAMA_NUM_PARALLEL="$PARALLEL" OLLAMA_KEEP_ALIVE=30m setsid nohup $PIN ollama serve > logs/ollama.log 2>&1 < /dev/null &)   # its own session: outlives the shell that started it
    for _ in $(seq 1 60); do
        curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
        sleep 1
    done
fi
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || true
# (f387) A pull is tried up to six times, a little longer apart each time: the registry answered one night's first pull with a bare 503,
# and the script, stopping at the first error, ended the night before it began while the pod went on billing.
pull() {
    ollama show "$1" >/dev/null 2>&1 && return 0          # already on the box: no pull, no registry round trip
    for n in 1 2 3 4 5 6; do
        ollama pull "$1" && return 0
        echo "Pulling $1 failed (try $n of 6); trying again in $((n * 20)) s."
        sleep $((n * 20))
    done
    return 1
}
pull "$MODEL"
pull "$EMBED"
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
