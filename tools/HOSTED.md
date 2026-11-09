# A night of runs on a rented card (f370, f529)

The night runs need one thing: a card with the memory for the game's own model server, one server a run. Since f529 the nights run on
the engine the game ships with (llama.cpp's `llama-server`, started and stopped by each run as the game starts and stops its own,
tools/runtime_cli.py), so what a night measures is what a player gets; nothing else is installed on the box. That can be a rented Linux
box instead of your own, so your computer stays yours. Everything below is done on the rented box; the only thing that comes home is a
zip of the logs, which `tools/latency.py`, `tools/world_report.py`, `tools/lora_dataset.py` and `tools/interp_corpus.py` read as they
read a local night's.

## What to rent

Each run is its own llama-server with the game's settings (data/runtime/server.yaml: two slots of 16,384 tokens, the draft model, the
embedder on the card), measured on the f527 pod session at 10,262 MiB for the chat server and 892 MiB for the embedder: about 11.2 GB a
run. Runs at once (PARALLEL) are as many servers; the card must hold them all.

| Card | Memory | Runs at once | Where |
| --- | ---: | ---: | --- |
| RTX 3090 / 4090 | 24 GB | 2 | RunPod (Secure Cloud for a data-center machine; Community is cheaper and less certain), Vast.ai |
| RTX 5090 | 32 GB | 2 | RunPod |
| A100 40 GB | 40 GB | 3 | Lambda, RunPod |
| A100 / H100 80 GB | 80 GB | 7 | Lambda, RunPod |

Each server holds its own two slots, so a night with runs at once measures each run's cache hits as the player's own machine would:
one game, one server. Nothing is shared between runs but the card.

Disk: a **container disk of 30 GB** and no volume disk. The model files are 8.1 GB (the chat model, its draft and the embedder, each
pinned by its sha256 in data/runtime/server.yaml), the server's build a few hundred megabytes, the game and its libraries under half a
gigabyte, and a night's logs about 100 MB per run (full prompts) plus the zip, so 12 GB is used and 30 leaves room. Put the game in the
home directory, not `/workspace`: the container disk is local and fast, `/workspace` is the volume disk, which can be network-backed
(slower writes) and bills at a higher rate if the pod is ever stopped rather than terminated. Everything on the container disk is gone
when the pod is terminated, which is what you want once the zip is downloaded.

## The steps

1. Start the machine with a plain Ubuntu or PyTorch image (CUDA drivers already on it), the card above, and a web terminal or SSH.
2. In its terminal, get the game onto the box. The repository is private, so a read-only token or a zip of the folder:

       git clone https://<token>@github.com/treystar3/dnd_ai.git && cd dnd_ai

3. Run the night. The script fetches the model files and the server's build by their pinned checksums (tools/fetch_runtime.py; on
   Linux the CUDA build is made from llama.cpp's pinned commit, so the script installs the CUDA compiler when the image lacks it),
   checks they are in place, installs the game's libraries, plays the runs (each on a server of its own) and zips the logs:

       RUNS=5 HOURS=2 PARALLEL=2 bash tools/runpod_night.sh

   `EXTRA` passes anything else to `tools/nightrun.py`: `EXTRA="--starts veteran,legend --personas hunter,talker"`. `BUILD=vulkan` or
   `BUILD=cpu` takes a release build instead of the CUDA one. One run a night is recorded for replay (`--record`, given to the first
   run); the measuring runs play unrecorded, as the game ships (the owner's decision of 5 Nov).
4. Download `out/night_<when>.zip` from the box's file browser, then **terminate** the machine. A stopped one still bills for its disk.
5. At home, unzip it beside the other nights and read it as usual: each run's `summary.md` ends with the Play section, its `run.json`
   says what the model ran on (the build, the device, the machine's class, the model's sha, the sampling base and table as data has
   them), and `tools/lora_dataset.py --runs-dir` takes the whole folder.

## The depots (f531)

What is built and shipped, so a night on a rented box runs the same files a player gets:

- **The game depot:** `Meravia.exe` with its data/ (build_exe.bat: PyInstaller's folder) and the model server's builds beside it under
  `runtime/<build>/` (cuda, vulkan and cpu on Windows, copied from the project's runtime/ folder, fetched by tools/fetch_runtime.py
  --build <build> --platform windows). The CUDA build carries its runtime libraries; the game picks the build at launch (llm/launch.py's
  ladder) and never needs a download.
- **The model depot:** `models/*.gguf`, the files data/runtime/server.yaml names, each pinned by its sha256 and size: the same files
  tools/fetch_runtime.py --models fetches from their public source and a night runs on. On Steam the depot installs with the game; the
  testers' installer downloads the files itself, checking each checksum (installer/models.iss, written from server.yaml by
  tools/installer_files.py).
- **Never shipped:** data/replay (the kept recordings are a source tree's; the startup check asks for them only where a replay folder
  exists), the tools, the tests.

## Bundle D's closing night (f490)

The night that closes Bundle D is run as its baseline was (four runs at once, continuity on, the same personas and seeds) and measured
against `data/measured/bundle_d_baseline.yaml`: prompt sizes and first tries compare whatever the runs at once, and turn time is priced
from the card's profile, not the night's clock. Its cache-hit rate is each run's own since f529 (one server a run). Before terminating
the box, count the two-speaker reply's first tries on the card: `python tools/live_check.py --mode addressees --runs 20`
(saves/live_check_report.md; it starts a server of its own, so run it after the night, not beside it). At home:

    python tools/latency.py --against <run folders>     the speech tasks' sizes, first tries and cache hits beside the baseline's
    python tools/latency.py --gate                      the goldens priced at expected answers: no input dearer than before Bundle D
    python tools/latency.py --ceilings <run folders>    each speech task's ceiling from the night's p95 (data/measured/prompt_ceilings.yaml)

`brief.yaml many_addressees` stays `one_call` only if the two-speaker reply's first tries are within the closing's `many_points` of
npc_conversation's baseline; otherwise it becomes `flat_each`.

## What to expect

- A 10-hour night on a 3090 costs a few dollars; on an A100 with three runs at once about the same per run, finished sooner.
- Runs at once share the card: each one plays fewer turns per hour than it would alone, and the night as a whole plays more. The logs
  carry the game clock, so the per-day measures stay comparable.
- A run's server takes a few seconds to load from the pod's own disk (7 s cold on the f527 pod); the run waits for it. A server that
  dies is started again once by its run (llm/runtime.py); a second death ends that run with the reason in its run.json, and the night
  goes on with the others.
- The night stops on its own and writes `batch_<when>.md`. If the machine is reclaimed mid-night (spot or interruptible pricing), the
  finished runs are whole and the one in flight keeps its logs but not its summary: `python tools/latency.py <run folder>` writes it.
- Nothing on the box needs your account: the game, the model files and the logs. Keep any token you use read-only.

## Runpod in particular: the pod driven from a session

What the first hosted nights taught, so the next one is one command.

- **Create the pod** in the console or through the API: the official `runpod/pytorch` image (the one the console's Pytorch template
  uses), Secure Cloud, 30 GB container disk, no volume, Jupyter on (port `8888/http`), SSH off. The create call places exactly the GPU
  type named and answers 400 when it has no stock, so read `GET /v2/catalog/gpus?include=AVAILABILITY&product=POD` first.
- **Drive it through Jupyter**, not SSH. `tools/runpod_jupyter.py` reaches the pod over HTTPS alone: the Jupyter proxy's contents API
  takes the game as one tarball and its kernel websocket runs any command. The Runpod key comes from `RUNPOD_API_KEY` or `--key-file`
  and the Jupyter token from the pod's env; neither is printed. `night` uploads the committed game and starts the night detached;
  `status`, `tail` and `exec` watch it (`status` lists the llama-servers running and the card's memory). Needs `requests` and
  `websocket-client` on the driving machine.

      python tools/runpod_jupyter.py --pod <id> night --runs 4 --hours 3 --parallel 2 --mss-proxy
      python tools/runpod_jupyter.py --pod <id> status

- **Expect a path that drops big packets.** Two pods in a row passed 1,300-byte packets and dropped 1,400-byte ones with no word back,
  so every TLS handshake and download stalled, and nothing inside the container may change the MTU. `--mss-proxy` (MSS_PROXY=1 on the
  night script) routes the installs and the fetches through `tools/mss_proxy.py`, a loopback proxy whose outbound sockets cap their own
  segment size; downloads then run at hundreds of MB/s. The game's own calls to its server stay local.
- **The threads.** A container may show every core of the host while its quota is a dozen; the script reads the quota, pins the night
  to those cores and gives each run's server its share (`DND_NUM_THREAD`, the quota's cores divided by PARALLEL). Without that a 5090
  ran at a tenth of its speed.
- **Check the server saw the card** before trusting the night: each run's `llama-server.log` (in its run folder) must say
  `offloaded 49/49 layers to GPU`, and its `run.json` server section `class: minimum` with no warnings. A build that cannot see the
  card falls to the processor and says so there (`class: below`, the reason beside it).
- **At the end**, the zip is at `/workspace/dnd_ai/out/night_<when>.zip`: download it from the pod's Jupyter file browser (Connect, then
  Jupyter Lab, in the console) or through the tool, then **terminate** the pod. A stopped pod still bills for its disk.

Runpod's own guide for agents is at https://agents.runpod.io/ (its API at api.runpod.io); the Runpod plugin in the claude.ai catalog
carries the same skills and the hosted MCP server.
