# 11. A "Send logs" button: design

Goal: a tester presses one button and you get their logs, with their consent, without them finding folders or attaching files.

## What exists
- The game already writes what you need to `logs/`, beside the exe:
  - `turns.jsonl` (every turn),
  - `llm_calls.jsonl` (every model call, with full prompts),
  - `refusals.jsonl` (facades, dead ends, refusals),
  - `pulse.jsonl`, `sessions.jsonl`, `audit/`,
  - `crash.log`, which the code says is written "so the next upload carries it".
- `core/paths.py` already describes logs/ as the folder "which players send". Today that means by hand.
- `core/updates.py` already talks to GitHub releases (read-only), and the home page has a Settings section.

## What the player sees
1. **Settings → Send a report**, and the same button on the narrator's "something went wrong" line (`engine/failures.py`).
2. A dialog with:
   - an optional box: "What happened? (optional)";
   - checkboxes: ☑ logs from this session and the last 3, ☐ include my save (off by default), ☐ include the full model prompts (on
     for testers, off for the public);
   - the size, for example "about 4 MB", and a **"See what's sent"** link that opens the folder with the zip before upload;
   - **Send** / Cancel.
3. On success: "Sent. Your report number is **MR-7K3Q**." The player can quote that number to you on Discord or by email.
4. If upload fails (offline, or the server's down), the zip is saved to `logs/reports/` and the folder opens, so it can be sent by hand.

## The bundle (core/report.py)
```python
def build(note: str, include_save: bool, include_prompts: bool, sessions: int = 4) -> Path:
    rid = report_id()                                  # 'MR-' + 4 chars, also inside the manifest
    with zipfile.ZipFile(tmp / f"{rid}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps({
            "id": rid, "version": VERSION, "data_hash": statehash.data_hash()[:12], "model": config.MODEL,
            "os": platform.platform(), "card": launch.card_summary(), "class": launch.machine_class(),   # llm/launch.py already knows these
            "python": sys.version.split()[0], "when": utcnow(), "note": note[:4000]}))
        for f in recent_logs(sessions):                # turns, refusals, pulse, sessions, crash.log, audit/ for the last N sessions
            z.write(f, arcname=f"logs/{f.name}")
        if include_prompts:
            z.write(tail(LOGS / "llm_calls.jsonl", mb=40), arcname="logs/llm_calls.jsonl")   # newest 40 MB at most
        if include_save:
            z.write(store.backup_copy(), arcname="save/campaign.db")    # a consistent SQLite copy, not the live file
    return redact(tmp / f"{rid}.zip")                  # paths: C:\Users\<name>\ -> <HOME>\ ; nothing else
```
- **Caps:** the newest 40 MB of the prompt log; the zip itself capped at 50 MB (data, `data/runtime/report.yaml`).
- **Redaction:** home-directory paths and the Windows user name. The game holds no other personal data, but the **player's typed
  lines are in the logs**, and the dialog says so.

## Where it goes: three options

| Option | Effort | Notes |
|---|---|---|
| **A. Cloudflare Worker + R2 storage** (recommended) | About 40 lines of Worker code; R2's free tier probably covers testers | The Worker accepts a POST of one zip up to the cap, rate-limits by IP, stores it as `reports/<date>/<id>.zip`, and can post a message to your Discord. The game holds only the upload URL; **there's no way to list or read reports from the client** |
| **B. A Discord webhook** | Minimal | Files land in a private channel. But the webhook URL ships inside the game, so anyone who extracts it can spam the channel, and file size limits are small. Fine for a private tester build, not for Steam |
| **C. No server: the zip plus a pre-filled message** | Very low | Builds the zip and opens your Discord invite, or a pre-filled `mailto:` or GitHub issue form, with instructions to attach it. Never put a GitHub token in the client |

Steam's own features (Workshop, Cloud saves) aren't meant for collecting reports, so option A is the standard shape for a Steam
release too.

### A's Worker (sketch)
```js
export default {
  async fetch(req, env) {
    if (req.method !== "POST") return new Response("no", {status: 405});
    const len = Number(req.headers.get("content-length") || 0);
    if (!len || len > 50 * 1024 * 1024) return new Response("too big", {status: 413});
    const ip = req.headers.get("cf-connecting-ip");
    if (!(await env.LIMIT.limit({key: ip})).success) return new Response("slow down", {status: 429});   // rate-limit binding
    const id = (req.headers.get("x-report-id") || "").replace(/[^A-Z0-9-]/g, "").slice(0, 12) || crypto.randomUUID();
    const key = `reports/${new Date().toISOString().slice(0, 10)}/${id}.zip`;
    await env.REPORTS.put(key, req.body, {httpMetadata: {contentType: "application/zip"}});
    if (env.DISCORD_HOOK) await fetch(env.DISCORD_HOOK, {method: "POST", headers: {"content-type": "application/json"},
        body: JSON.stringify({content: `New report ${id} (${(len / 1e6).toFixed(1)} MB)`})});   // the hook stays on the server
    return Response.json({ok: true, id});
  }
};
```
The Discord webhook lives in the Worker's secrets, never in the game. That's what makes A safe where B isn't.

## Hooking it into the game
- `core/report.py`: `build()`, `upload(path)` (in a thread, with progress events and one retry), `report_id()`.
- `data/runtime/report.yaml` (outside the data hash, like `server.yaml`): `url`, `max_mb`, `prompt_mb`, `default_include_prompts`.
- `ui/gui/server.py`: a `POST /report` endpoint (the existing token check applies). `ui/gui/bridge.py`: progress through the existing
  `busy` events.
- `ui/gui/web/app.js`: the dialog in Settings, and the button on the failure line.
- `engine/failures.py`: the narrator's failure line offers "Send a report" (one plain line, read by the owner first, per the Bundle F
  rule on new lines a player sees).
- `tools/reports.py` (yours): downloads new reports from R2, unzips them, and runs `latency.py`, `interp_eval --promote` and
  `world_report.py` on them. Testers' sessions then feed the corpora from doc 10 directly.

## Privacy and consent
- **Nothing is sent without pressing Send.** No background telemetry. Opt-in automatic sending can come later as a separate decision.
- A short note in the dialog and the README: what's in a report, where it's kept, and how to ask for deletion (by report number).
- Keep reports for a set time (for example 180 days) and delete them on request. For a Steam release, the store page needs a privacy
  policy that mentions this.

## Tests (tools/sim)
- **`report_bundle_test`:**
  - the zip has the manifest and the right logs;
  - the save is left out unless asked for;
  - the prompt log is capped;
  - home paths are redacted.
- **`report_upload_test`:** against a local fake endpoint (`http.server`): success returns the id; a 413 or 429 or a dropped connection
  leaves the zip in `logs/reports/` and says so.
- **`report_ui_test`:** the endpoint needs the GUI token; the dialog's events reach the page.

## Order
1. Option C, the zip plus "open the folder and our Discord". About a day of work, and testers can send logs right away.
2. The Cloudflare Worker and the upload (option A), plus `tools/reports.py` on your side.
3. Wire `tools/reports.py` into the doc 10 human-line corpora.
