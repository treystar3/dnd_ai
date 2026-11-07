"""(f535) The prompt cache measured: the night's summary says, task by task, how much of the server's reading was the constant system
message (what a kept cache would spare) and how much the server reused, and what the server's own log says of its checkpoints and its
RAM cache's copies; the card profile splits the median turn's model time into reading, the system part of it, and writing."""
import gzip
import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import card_profile   # noqa: E402
import latency        # noqa: E402

bad = []


def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {extra}"))
    if not ok:
        bad.append(name)


tmp = pathlib.Path(tempfile.mkdtemp(prefix="cache535_"))
try:
    # ---- the gateway's rows: two attempts of one task (the second a retry the server reused), one of another, one without a shape
    rows = [
        {"task": "narrate", "attempt": 0, "tokens": {"prompt": 1000, "cached": 0}, "chars": 4000, "sizes": [["system", "", 3000], ["fact", "scene", 1000]]},
        {"task": "narrate", "attempt": 1, "tokens": {"prompt": 1100, "cached": 1000}, "chars": 4400, "sizes": [["system", "", 3000], ["fact", "scene", 1400]]},
        {"task": "ruling", "attempt": 0, "tokens": {"prompt": 500, "cached": 0}, "chars": 1000, "sizes": [["system", "", 250], ["fact", "x", 750]]},
        {"task": "ruling", "attempt": 0, "tokens": {"prompt": 400, "cached": 0}},
        {"task": "embedless", "attempt": 0, "error": "x"},
    ]
    (tmp / "llm_calls.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    m = latency.cache_measures(latency.load(tmp / "llm_calls.jsonl"))
    check("the system message's share of each attempt's reading is read from the shape (3000 of 4000, 3000 of 4400)",
          round(m["narrate"]["system"]) == 1500 and m["narrate"]["prompt"] == 2100 and m["narrate"]["cached"] == 1000 and m["narrate"]["attempts"] == 2, m.get("narrate"))
    check("...a row without the shape counts its reading, not its system part",
          m["ruling"] == {"attempts": 2, "prompt": 900, "known_prompt": 500, "system": 125.0, "cached": 0, "unknown": 1}, m.get("ruling"))
    check("...and the share of the attempts with a shape is applied to all (25% of 900)", latency._system_estimate(m["ruling"]) == (225, 0.25)
          and latency._system_estimate({"known_prompt": 0, "system": 0.0, "prompt": 5}) is None)
    check("...and a row without the server's counts is not a call read", "embedless" not in m)
    check("the share itself", latency.system_share(rows[0]) == 0.75 and latency.system_share(rows[3]) is None)

    # ---- the server's log, in the lines llama-server writes
    log = "\n".join([
        "0.01 I slot operator(): id  0 | task 1 | new prompt, n_ctx_slot = 16384, n_keep = 0, task.n_tokens = 1000",
        "0.02 I slot operator(): id  0 | task 1 | forcing full prompt re-processing due to lack of cache data (likely due to SWA or hybrid/recurrent memory, see x)",
        "0.03 I slot create_check: id  0 | task 1 | created context checkpoint 1 of 32 (pos_min = 0, pos_max = 467, n_tokens = 468, size = 146.256 MiB)",
        "0.04 I slot create_check: id  0 | task 1 | created context checkpoint 2 of 32 (pos_min = 0, pos_max = 1019, n_tokens = 1020, size = 318.763 MiB)",
        "0.05 I srv  get_availabl: prompt cache update took 500.00 ms",
        "0.06 I slot operator(): id  0 | task 2 | new prompt, n_ctx_slot = 16384, n_keep = 0, task.n_tokens = 1100",
        "0.07 I slot operator(): id  0 | task 2 | restored context checkpoint (pos_min = 0, pos_max = 467, n_tokens = 468, n_past = 467, size = 146.256 MiB)",
        "0.08 I srv  get_availabl: prompt cache update took 700.00 ms",
        "0.09 I srv         alloc:  - making room for prompt cache entry, removing oldest entry (size = 815.3 MiB)",
        "0.10 I slot operator(): id  0 | task 3 | new prompt, n_ctx_slot = 16384, n_keep = 0, task.n_tokens = 500",
        "0.11 I slot operator(): id  0 | task 3 | forcing full prompt re-processing due to lack of cache data (likely due to SWA or hybrid/recurrent memory, see x)",
        "0.12 I slot operator(): id  1 | task 4 | new prompt, n_ctx_slot = 16384, n_keep = 0, task.n_tokens = 400",
    ]) + "\n"
    (tmp / "llama-server.log").write_text(log, encoding="utf-8")
    lg = latency.server_log_measures(tmp / "llama-server.log")
    check("the server's log is read: prompts, whole re-processings, checkpoints made and restored, cache updates and their time, evictions",
          lg == {"prompts": 4, "whole": 2, "restored": 1, "checkpoints": 2, "evicted": 1, "updates": 2, "update_ms": 1200.0, "update_ms_max": 700.0}, lg)
    check("...and no log is no account", latency.server_log_measures(tmp / "none.log") == {})

    text = latency.summarise(tmp)
    sec = text.split("## Prompt cache", 1)[1] if "## Prompt cache" in text else ""
    check("the night's summary has the section", bool(sec), text[-400:])
    check("...the task table, biggest reading first, attempts counted", "| Task | Attempts |" in sec and "| narrate | 2 | 2100 | 1500 (71%) | 1000 (48%) |" in sec
          and "| ruling | 2 | 900 | 225 (25%) | 0 (0%) |" in sec and sec.index("| narrate |") < sec.index("| ruling |"), sec)
    check("...the whole in one line, the estimate named as one, the reused apart from the read",
          "The prompts held 3000 tokens; the constant system messages were about 1725 of them (58%, estimated from their share of the prompts' characters)" in sec
          and "the server reused 1000 (33%) and read the rest." in sec, sec)
    check("...and the server's own account, in what it counts", "4 prompts; 2 forced to re-process the whole prompt for want of cache data" in sec
          and "2 checkpoints made, 1 restored" in sec and "2 prompt-cache updates taking 1.2 s in all (mean 600 ms, the longest 700 ms)" in sec
          and "1 entries evicted" in sec and "it is capped" not in sec, sec)

    # ---- the game caps the server log and keeps the file before as .1: both are read, and a log shorter than the night says so
    (tmp / "llama-server.log.1").write_text("0.00 I slot operator(): id  1 | task 0 | new prompt, n_ctx_slot = 16384, n_keep = 0, task.n_tokens = 300\n"
                                           "0.00 I srv  get_availabl: prompt cache update took 100.00 ms\n", encoding="utf-8")
    lg2 = latency.server_log_measures(tmp / "llama-server.log")
    check("the rotated log is read before the live one", lg2["prompts"] == 5 and lg2["updates"] == 3 and lg2["update_ms"] == 1300.0, lg2)
    short = latency.cache_table(latency.load(tmp / "llm_calls.jsonl"), {**lg2, "prompts": 2})
    check("...and a log holding fewer prompts than the night's attempts says it is capped", any("2 prompts (the log holds the night's last 2 prompts of 4: it is capped)" in l for l in short), short[-1])

    # ---- the card profile's split of a turn: reading, the system part of it, writing (an embed row is not reading)
    rec = tmp / "recording"; rec.mkdir()
    calls = [
        {"i": 0, "input": 1, "kind": "chat", "title": "Narration", "seconds": 3.1, "usage": {"prompt": 1000, "out": 20, "read_ms": 2000, "write_ms": 1000},
         "request": {"messages": [{"role": "system", "content": "s" * 300}, {"role": "user", "content": "u" * 100}]}},
        {"i": 1, "input": 1, "kind": "embed", "seconds": 0.2, "request": {"input": ["a", "b"]}},
        {"i": 2, "input": 2, "kind": "chat", "title": "Ruling", "seconds": 7.2, "usage": {"prompt": 2000, "out": 60, "read_ms": 4000, "write_ms": 3000},
         "request": {"messages": [{"role": "system", "content": "s" * 200}, {"role": "user", "content": "u" * 200}]}},
    ]
    with gzip.open(rec / "calls.jsonl.gz", "wt", encoding="utf-8") as f:
        for c in calls:
            f.write(json.dumps(c) + "\n")
    m = card_profile.measure(rec)
    check("the median turn's model time is split into reading, the constant system part of it, and writing",
          (m["read_s_p50"], m["system_s_p50"], m["write_s_p50"]) == (3.0, 1.8, 2.0), (m["read_s_p50"], m["system_s_p50"], m["write_s_p50"]))
    check("...the system share of a recorded chat is its system message's characters of the prompt's", card_profile.system_share(calls[0]) == 0.75
          and card_profile.system_share({"input": 1, "usage": {"read_ms": 5}}) is None)
    scaled = card_profile.measure(rec, read=2.0, write=0.5)
    check("...and scaled to another card with the reading and writing", (scaled["read_s_p50"], scaled["system_s_p50"], scaled["write_s_p50"]) == (6.0, 3.5, 1.0),
          (scaled["read_s_p50"], scaled["system_s_p50"], scaled["write_s_p50"]))
    # a re-timed recording (timed.jsonl, the card's counts and no messages) takes each call's messages from the recorder's own row, by i
    timed = [{"i": 0, "input": 1, "kind": "chat", "title": "Narration", "seconds": 6.2, "usage": {"prompt": 1000, "out": 20, "read_ms": 4000, "write_ms": 2000}},
             {"i": 2, "input": 2, "kind": "chat", "title": "Ruling", "seconds": 7.2, "usage": {"prompt": 2000, "out": 60, "read_ms": 4000, "write_ms": 3000}}]
    (rec / "timed.jsonl").write_text("\n".join(json.dumps(c) for c in timed) + "\n", encoding="utf-8")
    mt = card_profile.measure(rec)
    check("a re-timed recording's system part is read from the recorder's rows, not taken as nothing",
          (mt["read_s_p50"], mt["system_s_p50"], mt["write_s_p50"]) == (4.0, 2.5, 2.5), (mt["read_s_p50"], mt["system_s_p50"], mt["write_s_p50"]))
    (rec / "timed.jsonl").write_text(json.dumps({**timed[0], "i": 99}) + "\n", encoding="utf-8")
    mu = card_profile.measure(rec)
    check("...and a row no recorder row matches leaves the system part unknown, never a measured nothing", mu["read_s_p50"] == 4.0 and mu["system_s_p50"] is None, mu)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
