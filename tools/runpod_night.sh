#!/usr/bin/env bash
# (f370, f529) A night of runs on a rented Linux box with an NVIDIA card (RunPod, Lambda, any Ubuntu): tools/HOSTED.md has the steps around it.
#
#     RUNS=5 HOURS=2 PARALLEL=2 bash tools/runpod_night.sh
#
# Fetches the game's own model server and model files by their pinned checksums (tools/fetch_runtime.py: the CUDA build of llama.cpp's
# pinned commit, built from source on Linux, and the GGUF files data/runtime/server.yaml names), installs the game's libraries, plays
# RUNS runs of HOURS hours (PARALLEL at a time, tools/nightrun.py: each run starts a server of its own, as the game ships), and zips
# every log under out/ to carry home. Everything the night needs is on the box; nothing reaches the machine you started it from but
# the zip you download. The nights run on the engine the game ships with and nothing else (GOALS.md, the owner's decision of 5 Nov).
set -euo pipefail
cd "$(dirname "$0")/.."

RUNS="${RUNS:-5}"
HOURS="${HOURS:-2}"
PARALLEL="${PARALLEL:-1}"
OUT="${OUT:-logs/nightrun}"
EXTRA="${EXTRA:-}"                              # anything else for tools/nightrun.py: --starts veteran,legend --personas hunter,talker --level 40
BUILD="${BUILD:-cuda}"                          # the llama-server build: cuda (built from source here), vulkan or cpu (releases)
MODEL="$(python3 -c 'import config; print(config.MODEL)')"
mkdir -p logs out

# A path that drops big packets (seen on Runpod: 1,300-byte packets pass, 1,400 do not) stalls every download. MSS_PROXY=1 routes the
# installs and the fetches through tools/mss_proxy.py, which caps its outbound segments; the game's own calls to its server stay local.
if [ "${MSS_PROXY:-0}" = "1" ]; then
    if ! curl -sS -o /dev/null -m 5 -x http://127.0.0.1:3128 https://github.com/ 2>/dev/null; then
        (setsid nohup python3 tools/mss_proxy.py --port 3128 > logs/mss_proxy.log 2>&1 < /dev/null &)
        sleep 1
    fi
    export HTTPS_PROXY=http://127.0.0.1:3128 HTTP_PROXY=http://127.0.0.1:3128 https_proxy=http://127.0.0.1:3128 http_proxy=http://127.0.0.1:3128
    export NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
    echo "Downloads go through the segment-capping proxy (MSS_PROXY=1)."
fi

# A container may see every core of the host (nproc 128) while its quota is a dozen; a server then spawns a thread per core seen and
# they fight over the quota, and a 5090 ran at a tenth of its speed. The quota's cores are split among the runs at once (each run's
# server gets DND_NUM_THREAD threads, llm/runtime.py chat_argv -t), and the night is pinned to those cores (the servers inherit it).
PIN=""
CORES="$(nproc)"
if [ -r /sys/fs/cgroup/cpu.max ]; then
    read -r QUOTA PERIOD < /sys/fs/cgroup/cpu.max
    if [ "$QUOTA" != "max" ] && [ "$QUOTA" -gt 0 ] 2>/dev/null; then
        CORES=$(( (QUOTA + PERIOD - 1) / PERIOD ))
        if [ "$CORES" -lt "$(nproc)" ] && command -v taskset >/dev/null 2>&1; then
            PIN="taskset -c 0-$((CORES - 1))"
            echo "Pinning the night to $CORES cores (the container's quota; nproc says $(nproc))."
        fi
    fi
fi
[ "$CORES" -gt "$(nproc)" ] && CORES="$(nproc)"
if [ "${DND_NUM_THREAD:-0}" = "0" ]; then
    export DND_NUM_THREAD=$(( CORES / PARALLEL > 2 ? CORES / PARALLEL : 2 ))
fi
echo "Each of the $PARALLEL server(s) at once gets $DND_NUM_THREAD threads (DND_NUM_THREAD) of $CORES cores."

# The CUDA build needs the compiler (the pod images carry the driver and the runtime, not nvcc); zstd for the release archives.
if [ "$BUILD" = "cuda" ]; then
    export PATH=/usr/local/cuda/bin:/usr/local/cuda-12.8/bin:$PATH
    if ! command -v nvcc >/dev/null 2>&1; then
        echo "Installing the CUDA compiler for the server's build..."
        (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq cuda-nvcc-12-8 cuda-cudart-dev-12-8 libcublas-dev-12-8 cuda-nvrtc-dev-12-8) \
            > logs/apt.log 2>&1 || { echo "apt failed (logs/apt.log):"; tail -5 logs/apt.log; }
        export PATH=/usr/local/cuda-12.8/bin:$PATH
    fi
    command -v cmake >/dev/null 2>&1 || python3 -m pip install -q cmake
fi
python3 -m pip install -q -r requirements.txt

# (f387, f529) A fetch is tried up to six times, a little longer apart each time: a registry answered one night's first fetch with a bare
# 503, and a script stopping at the first error ended the night before it began while the pod went on billing. Every file is checked
# against its sha256 in data/runtime/server.yaml by the tool itself; one already here with the right checksum is not fetched again.
fetch() {
    for n in 1 2 3 4 5 6; do
        python3 tools/fetch_runtime.py "$@" && return 0
        echo "fetch_runtime $* failed (try $n of 6); trying again in $((n * 20)) s."
        sleep $((n * 20))
    done
    return 1
}
fetch --models
if [ "$BUILD" = "cuda" ] && [ "$(python3 -c 'from llm import runtime; print(runtime.platform())')" = "linux" ]; then
    fetch --build cuda --from-source
else
    fetch --build "$BUILD"
fi
python3 - <<'EOF'
import sys
sys.path.insert(0, ".")
from llm import runtime
bad = runtime.runtime_problems(check_files=True)
if bad:
    print("The server's files are not in place:\n  - " + "\n  - ".join(bad))
    sys.exit(1)
print("The server's files are in place, each at its pinned checksum.")
EOF
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || true

echo "A night of $RUNS run(s), $HOURS h each, $PARALLEL at a time: $MODEL on the game's own llama-server ($BUILD)"
# shellcheck disable=SC2086
$PIN python3 tools/nightrun.py --runs "$RUNS" --hours "$HOURS" --parallel "$PARALLEL" --out "$OUT" --record $EXTRA || true

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
