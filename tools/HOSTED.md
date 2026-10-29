# A night of runs on a rented card (f370)

The night runs need one thing: an Ollama server with the game's model on a card with the memory for it. That can be a rented Linux box
instead of your own, so your computer stays yours. Everything below is done on the rented box; the only thing that comes home is a zip of
the logs, which `tools/latency.py`, `tools/world_report.py`, `tools/lora_dataset.py` and `tools/interp_corpus.py` read as they read a
local night's.

## What to rent

| Card | Memory | Runs at once | Where |
| --- | ---: | ---: | --- |
| RTX 3090 / 4090 | 24 GB | 2 | RunPod (Secure Cloud for a data-center machine; Community is cheaper and less certain), Vast.ai |
| A10 | 24 GB | 2 to 3 | Lambda |
| A100 40 GB | 40 GB | 5 to 6 | Lambda, RunPod |

The model's weights take about 8 GB; each run at once adds its own context cache, a few gigabytes at the game's 32k context. `ollama ps`
on the box shows how much of the model sits on the card: anything under 100% GPU means one run too many.

Disk: a **container disk of 30 GB** and no volume disk. The model is 8 GB, Ollama itself about 1.5 GB, the game and its libraries under
half a gigabyte, and a night's logs about 100 MB per run (full prompts) plus the zip, so 15 GB is used and 30 leaves room. Put the game in
the home directory, not `/workspace`: the container disk is local and fast, `/workspace` is the volume disk, which can be network-backed
(slower writes) and bills at a higher rate if the pod is ever stopped rather than terminated. Everything on the container disk is gone
when the pod is terminated, which is what you want once the zip is downloaded.

## The steps

1. Start the machine with a plain Ubuntu or PyTorch image (CUDA drivers already on it), the card above, and a web terminal or SSH.
2. In its terminal, get the game onto the box. The repository is private, so a read-only token or a zip of the folder:

       git clone https://<token>@github.com/treystar3/dnd_ai.git && cd dnd_ai

3. Run the night. The script installs Ollama when the box has none, starts it with room for the runs at once, pulls the models, installs
   the game's libraries, plays the runs, and zips the logs:

       RUNS=5 HOURS=2 PARALLEL=2 bash tools/runpod_night.sh

   `EXTRA` passes anything else to `tools/nightrun.py`: `EXTRA="--starts veteran,legend --personas hunter,talker"`.
4. Download `out/night_<when>.zip` from the box's file browser, then **terminate** the machine. A stopped one still bills for its disk.
5. At home, unzip it beside the other nights and read it as usual: each run's `summary.md` ends with the Play section, and
   `tools/lora_dataset.py --runs-dir` takes the whole folder.

## What to expect

- A 10-hour night on a 3090 costs a few dollars; on an A100 with five runs at once about the same per run, finished sooner.
- Runs at once share the card: each one plays fewer turns per hour than it would alone, and the night as a whole plays more. The logs
  carry the game clock, so the per-day measures stay comparable.
- The night stops on its own and writes `batch_<when>.md`. If the machine is reclaimed mid-night (spot or interruptible pricing), the
  finished runs are whole and the one in flight keeps its logs but not its summary: `python tools/latency.py <run folder>` writes it.
- Nothing on the box needs your account: the game, the model and the logs. Keep any token you use read-only.

## Runpod in particular: the pod driven from a session

What the first hosted night taught, so the next one is one command.

- **Create the pod** in the console or through the API: the official `runpod/pytorch` image (the one the console's Pytorch template
  uses), Secure Cloud, 30 GB container disk, no volume, Jupyter on (port `8888/http`), SSH off. The create call places exactly the GPU
  type named and answers 400 when it has no stock, so read `GET /v2/catalog/gpus?include=AVAILABILITY&product=POD` first.
- **Drive it through Jupyter**, not SSH. `tools/runpod_jupyter.py` reaches the pod over HTTPS alone: the Jupyter proxy's contents API
  takes the game as one tarball and its kernel websocket runs any command. The Runpod key comes from `RUNPOD_API_KEY` or `--key-file`
  and the Jupyter token from the pod's env; neither is printed. `night` uploads the committed game and starts the night detached;
  `status`, `tail` and `exec` watch it. Needs `requests` and `websocket-client` on the driving machine.

      python tools/runpod_jupyter.py --pod <id> night --runs 6 --hours 3 --parallel 3 --mss-proxy
      python tools/runpod_jupyter.py --pod <id> status

- **Expect a path that drops big packets.** Two pods in a row passed 1,300-byte packets and dropped 1,400-byte ones with no word back,
  so every TLS handshake and download stalled, and nothing inside the container may change the MTU. `--mss-proxy` (MSS_PROXY=1 on the
  night script) routes the installs and the pulls through `tools/mss_proxy.py`, a loopback proxy whose outbound sockets cap their own
  segment size; downloads then run at hundreds of MB/s. The game's own calls to Ollama stay local.
- **Check Ollama saw the card** before trusting the night: the server log (`logs/ollama.log`) must say `library=CUDA`. A half-finished
  install leaves an `ollama` that runs on the CPU in silence; the night script reinstalls only when the binary is missing, so remove
  `/usr/local/bin/ollama` and `/usr/local/lib/ollama` by hand after a failed install.
- **At the end**, the zip is at `/workspace/dnd_ai/out/night_<when>.zip`: download it from the pod's Jupyter file browser (Connect, then
  Jupyter Lab, in the console) or through the tool, then **terminate** the pod. A stopped pod still bills for its disk.

Runpod's own guide for agents is at https://agents.runpod.io/ (its API at api.runpod.io); the Runpod plugin in the claude.ai catalog
carries the same skills and the hosted MCP server.
