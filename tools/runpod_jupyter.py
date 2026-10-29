"""(f370) Drive a Runpod pod through its JupyterLab server, over HTTPS alone: upload files, run commands, read logs.

    python tools/runpod_jupyter.py --pod ID exec "nvidia-smi"
    python tools/runpod_jupyter.py --pod ID upload local.tar.gz workspace/dnd.tar.gz
    python tools/runpod_jupyter.py --pod ID night --runs 6 --hours 3 --parallel 3      the whole night: upload the game, start it detached
    python tools/runpod_jupyter.py --pod ID tail                                       the night's log so far
    python tools/runpod_jupyter.py --pod ID status                                     the card, the server, the runs

Why: the pod's SSH needs a raw TCP route and a key on the account; a session that has neither still has HTTPS to the pod's Jupyter
proxy (port 8888, which the official templates start), whose REST API uploads files and whose kernel websocket runs Python, and through
it any shell command. The Runpod key comes from RUNPOD_API_KEY or --key-file (it reads the pod's Jupyter token from the pod's env);
nothing here prints either. An HTTPS proxy in HTTPS_PROXY is honoured, with the CA bundle in REQUESTS_CA_BUNDLE or SSL_CERT_FILE.
Needs the `requests` and `websocket-client` packages on the machine running it (not on the pod)."""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.parse
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.runpod.io/v2"


def key_from(args) -> str:
    if args.key_file:
        return Path(args.key_file).read_text(encoding="utf-8").strip()
    key = os.environ.get("RUNPOD_API_KEY", "").strip()
    if not key:
        sys.exit("no Runpod key: set RUNPOD_API_KEY or pass --key-file")
    return key


def ca_file() -> str | None:
    for var in ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE"):
        if os.environ.get(var) and Path(os.environ[var]).exists():
            return os.environ[var]
    for p in ("/root/.ccr/ca-bundle.crt",):
        if Path(p).exists():
            return p
    return None


class Pod:
    def __init__(self, pod_id: str, key: str):
        import requests
        self.rq = requests
        self.verify = ca_file() or True
        self.id, self.key = pod_id, key
        r = requests.get(f"{API}/pods/{pod_id}", headers={"Authorization": f"Bearer {key}"}, timeout=60, verify=self.verify)
        if r.status_code != 200:
            sys.exit(f"pod {pod_id}: the Runpod API answered {r.status_code} {r.text[:120]}")
        self.info = r.json()
        self.token = (self.info.get("env") or {}).get("JUPYTER_PASSWORD", "")
        if not self.token:
            sys.exit("the pod has no JUPYTER_PASSWORD in its env: it was not created with Jupyter, so this route cannot reach it")
        self.host = f"{pod_id}-8888.proxy.runpod.net"
        self.base = f"https://{self.host}"
        self.h = {"Authorization": f"token {self.token}"}
        self.kernel = ""

    # ---- files
    def upload(self, local: Path, remote: str) -> dict:
        """PUT a file through Jupyter's contents API (base64; fine up to tens of MB). `remote` is relative to Jupyter's root, which on the
        official images is the filesystem root, so 'workspace/x' lands at /workspace/x."""
        payload = {"type": "file", "format": "base64", "content": base64.b64encode(local.read_bytes()).decode("ascii")}
        r = self.rq.put(f"{self.base}/api/contents/{remote.lstrip('/')}", headers=self.h, json=payload, timeout=600, verify=self.verify)
        r.raise_for_status()
        return r.json()

    def read(self, remote: str, tail: int = 0) -> str:
        """A text file's contents (its last `tail` lines when asked), read by the kernel so any path works."""
        code = ("import pathlib\n"
                f"p = pathlib.Path({remote!r})\n"
                "t = p.read_text(errors='replace') if p.exists() else '(no such file)'\n"
                f"print('\\n'.join(t.splitlines()[-{tail}:]) if {tail} else t)")
        return self.run(code)

    # ---- commands, through a Python kernel
    def start_kernel(self) -> str:
        if self.kernel:
            return self.kernel
        r = self.rq.get(f"{self.base}/api/kernels", headers=self.h, timeout=60, verify=self.verify)
        for k in r.json() if r.status_code == 200 else []:
            if k.get("name", "").startswith("python"):
                self.kernel = k["id"]
                return self.kernel
        r = self.rq.post(f"{self.base}/api/kernels", headers=self.h, json={"name": "python3"}, timeout=120, verify=self.verify)
        r.raise_for_status()
        self.kernel = r.json()["id"]
        return self.kernel

    def run(self, code: str, timeout: int = 600) -> str:
        """Execute Python in the pod's kernel over the websocket and return what it printed."""
        import websocket                                        # websocket-client
        kid = self.start_kernel()
        kw = {"header": [f"Authorization: token {self.token}"]}
        if ca_file():
            kw["sslopt"] = {"ca_certs": ca_file()}
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if proxy:
            u = urllib.parse.urlparse(proxy)
            kw.update(http_proxy_host=u.hostname, http_proxy_port=u.port, proxy_type="http")
            if u.username:
                kw["http_proxy_auth"] = (urllib.parse.unquote(u.username), urllib.parse.unquote(u.password or ""))
        ws = websocket.create_connection(f"wss://{self.host}/api/kernels/{kid}/channels", timeout=timeout, **kw)
        msg_id = uuid.uuid4().hex
        ws.send(json.dumps({"header": {"msg_id": msg_id, "username": "dnd", "session": uuid.uuid4().hex, "msg_type": "execute_request", "version": "5.3"},
                            "parent_header": {}, "metadata": {}, "channel": "shell", "buffers": [],
                            "content": {"code": code, "silent": False, "store_history": False, "allow_stdin": False, "stop_on_error": True}}))
        out, t0 = [], time.time()
        try:
            while time.time() - t0 < timeout:
                m = json.loads(ws.recv())
                if (m.get("parent_header") or {}).get("msg_id") != msg_id:
                    continue
                t = m.get("msg_type")
                c = m.get("content") or {}
                if t == "stream":
                    out.append(c.get("text", ""))
                elif t == "error":
                    out.append("\n".join(c.get("traceback") or [c.get("evalue", "error")]))
                elif t == "execute_result":
                    out.append(str((c.get("data") or {}).get("text/plain", "")))
                elif t == "status" and c.get("execution_state") == "idle":
                    break
        finally:
            ws.close()
        return "".join(out)

    def sh(self, cmd: str, timeout: int = 600) -> str:
        """A shell command, its output returned whole (for long work, start it detached and read its log)."""
        code = ("import subprocess\n"
                f"r = subprocess.run({cmd!r}, shell=True, capture_output=True, text=True, timeout={timeout})\n"
                "print(r.stdout, end='')\n"
                "print(r.stderr, end='')\n"
                "print(f'[exit {r.returncode}]')")
        return self.run(code, timeout=timeout + 30)


def archive_repo() -> Path:
    """The game as it is committed, as one tarball (what the night plays)."""
    out = Path(os.environ.get("TMPDIR") or "/tmp") / "dnd_ai_head.tar.gz"
    subprocess.run(["git", "archive", "--format=tar.gz", "-o", str(out), "HEAD"], cwd=ROOT, check=True)
    return out


BOOT = """set -o pipefail
cd /workspace
echo "boot $(date -u +%FT%TZ): unpacking the game"
rm -rf dnd_ai && mkdir dnd_ai && tar -xzf dnd.tar.gz -C dnd_ai
cd dnd_ai
{env}MSS_PROXY={mss} DND_NUM_THREAD={threads} RUNS={runs} HOURS={hours} PARALLEL={parallel} EXTRA="{extra}" bash tools/runpod_night.sh
echo "NIGHT DONE $(date -u +%FT%TZ)"
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pod", required=True)
    ap.add_argument("--key-file")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("exec"); e.add_argument("command"); e.add_argument("--timeout", type=int, default=600)
    u = sub.add_parser("upload"); u.add_argument("local"); u.add_argument("remote")
    n = sub.add_parser("night"); n.add_argument("--runs", type=int, default=6); n.add_argument("--hours", type=float, default=2)
    n.add_argument("--parallel", type=int, default=3); n.add_argument("--extra", default="")
    n.add_argument("--mss-proxy", action="store_true", help="route the pod's downloads through tools/mss_proxy.py (a path that drops big packets)")
    n.add_argument("--num-thread", type=int, default=0, help="CPU threads for the model runner (0: half the container's CPU quota when pinned, else Ollama's default)")
    n.add_argument("--env", action="append", default=[], metavar="KEY=VALUE",
                   help="(f387) a setting for the game, e.g. --env DND_TEMP_ADD=0.15 --env DND_REPEAT_ADD=0.1 (config.py reads DND_ settings)")
    t = sub.add_parser("tail"); t.add_argument("--lines", type=int, default=40); t.add_argument("--file", default="/workspace/night.log")
    sub.add_parser("status")
    args = ap.parse_args()
    pod = Pod(args.pod, key_from(args))
    if args.cmd == "exec":
        print(pod.sh(args.command, args.timeout), end="")
    elif args.cmd == "upload":
        r = pod.upload(Path(args.local), args.remote)
        print(f"uploaded {args.local} -> /{r.get('path')}")
    elif args.cmd == "night":
        tar = archive_repo()
        r = pod.upload(tar, "workspace/dnd.tar.gz")
        print(f"uploaded the game ({tar.stat().st_size // 1_000_000} MB) -> /{r.get('path')}")
        import re as _re
        env = [e for e in args.env if _re.fullmatch(r"DND_[A-Z_]+=[0-9.+-]+", e)]
        if len(env) != len(args.env):
            sys.exit("--env takes DND_NAME=number settings only")
        boot = BOOT.format(runs=args.runs, hours=args.hours, parallel=args.parallel, extra=args.extra.replace('"', ""), mss=int(args.mss_proxy),
                           threads=args.num_thread, env="".join(e + " " for e in env))
        pod.run("import pathlib\npathlib.Path('/workspace/dnd_boot.sh').write_text(" + repr(boot) + ")\nprint('boot script written')")
        print(pod.sh("cd /workspace && (setsid nohup bash /workspace/dnd_boot.sh > /workspace/night.log 2>&1 < /dev/null &) ; sleep 3; echo started; head -3 /workspace/night.log"), end="")
    elif args.cmd == "tail":
        print(pod.read(args.file, args.lines))
    elif args.cmd == "status":
        print(pod.sh("nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader; "
                     "(ollama ps 2>/dev/null || echo 'ollama: not running'); "
                     "ls /workspace/dnd_ai/logs/nightrun 2>/dev/null; ls /workspace/dnd_ai/out 2>/dev/null; "
                     "tail -3 /workspace/night.log 2>/dev/null"), end="")


if __name__ == "__main__":
    main()
