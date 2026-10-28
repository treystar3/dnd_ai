"""(f370) A local HTTP CONNECT proxy whose outbound sockets cap their TCP segment size: the way through a network path that drops big packets.

    python3 tools/mss_proxy.py --port 3128 --mss 1200 &
    export HTTPS_PROXY=http://127.0.0.1:3128 HTTP_PROXY=http://127.0.0.1:3128

Why: two Runpod pods in a row sat on a path that passed 1,300-byte packets and dropped 1,400-byte ones with no word back (a path MTU
black hole), so every TLS handshake and every download stalled, while nothing inside the container may change the interface MTU or the
kernel's MSS. A socket may still cap its own segment size (TCP_MAXSEG): the peer then never sends a segment that the path drops.
Ollama, pip, curl and the game's own client all honour HTTPS_PROXY, so one small proxy with that cap carries the whole night's setup.
Plain HTTP (the Ubuntu archive) is proxied too. No logging, no filtering, loopback only."""
from __future__ import annotations

import argparse
import select
import socket
import threading

MSS = 1200
TIMEOUT = 120


def upstream(host: str, port: int) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_MAXSEG, MSS)
    s.settimeout(TIMEOUT)
    s.connect((host, port))
    return s


def splice(a: socket.socket, b: socket.socket) -> None:
    """Bytes both ways until one side closes."""
    a.setblocking(False)
    b.setblocking(False)
    pairs = {a: b, b: a}
    try:
        while pairs:
            readable, _, errored = select.select(list(pairs), [], list(pairs), TIMEOUT)
            if not readable and not errored:
                break
            for s in errored:
                return
            for s in readable:
                try:
                    data = s.recv(65536)
                except (BlockingIOError, InterruptedError):
                    continue
                except OSError:
                    return
                if not data:
                    return
                try:
                    pairs[s].sendall(data)
                except OSError:
                    return
    finally:
        for s in (a, b):
            try:
                s.close()
            except OSError:
                pass


def handle(client: socket.socket) -> None:
    try:
        client.settimeout(TIMEOUT)
        head = b""
        while b"\r\n\r\n" not in head and len(head) < 65536:
            chunk = client.recv(65536)
            if not chunk:
                return
            head += chunk
        request, _, rest = head.partition(b"\r\n\r\n")
        line = request.split(b"\r\n", 1)[0].decode("latin-1")
        method, target, _ = (line.split(" ") + ["", ""])[:3]
        if method.upper() == "CONNECT":                                  # HTTPS: tunnel
            host, _, port = target.rpartition(":")
            up = upstream(host, int(port or 443))
            client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            if rest:
                up.sendall(rest)
            splice(client, up)
            return
        if "://" in target:                                              # plain HTTP: forward the request with a relative path
            scheme_host, _, path = target.partition("://")[2].partition("/")
            host, _, port = scheme_host.rpartition(":") if ":" in scheme_host else (scheme_host, "", "")
            up = upstream(host, int(port or 80))
            first = f"{method} /{path} HTTP/1.1".encode()
            headers = [h for h in request.split(b"\r\n")[1:] if not h.lower().startswith(b"proxy-")]
            up.sendall(b"\r\n".join([first] + headers) + b"\r\n\r\n" + rest)
            splice(client, up)
            return
        client.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
    except Exception:
        try:
            client.close()
        except OSError:
            pass


def serve(port: int) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(64)
    print(f"mss proxy on 127.0.0.1:{port}, outbound segments capped at {MSS} bytes", flush=True)
    while True:
        c, _ = srv.accept()
        threading.Thread(target=handle, args=(c,), daemon=True).start()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=3128)
    ap.add_argument("--mss", type=int, default=MSS)
    args = ap.parse_args()
    MSS = args.mss
    serve(args.port)
