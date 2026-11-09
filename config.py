MODEL = "gemma4-12b-bb722270"                 # (f527) the chat model's GGUF id: its file's stem, name and sha prefix, pinned in data/runtime/server.yaml
THINK = False
# (f533) The model's thinking for chosen tasks only, to measure it before the owner decides (tools/think_ab.py): DND_THINK_TASKS in the
# environment, task names split by commas, turns thinking on for those tasks' calls, each given THINK_ROOM more tokens to think in (so
# the thinking does not cut the answer short); empty, every call goes as THINK says. Not in the data hash; off, nothing kept moves. On,
# a chosen task's request carries the larger num_predict, and a recording's meta names the tasks and the room (engine/recording.py),
# so its replay asks as it did (tools/rerun.py); a name no task has is refused at startup (engine/data_check.py).
THINK_TASKS = frozenset(t.strip() for t in __import__("os").environ.get("DND_THINK_TASKS", "").split(",") if t.strip())
THINK_ROOM = int(__import__("os").environ.get("DND_THINK_ROOM", "").strip() or 8192)       # an explicit 0 is no room
# (f534) 8,192 since the first 5090 session (5 Nov), where 1,024 ran out on most of the interpreter's calls; a call is never given more
# than its context holds beside the prompt and the answer (llm/backend.py think_room).
# (f425) The context the model is given for each call. DND_NUM_CTX in the environment sets it for one night: a night of six runs on one
# card reserves this much for every run at once, and no call of the f395 night went past about 10,000 tokens.
NUM_CTX = int(__import__("os").environ.get("DND_NUM_CTX", "0") or 0) or 32768
# (f370) CPU threads the model server may use (llm/runtime.py chat_argv -t), 0 for its own default (one per core the machine shows). A
# container that shows every core of its host while its quota is a dozen needs this set (the night script sets it from the quota), or
# the server's threads fight for the quota and the card waits on them; DND_NUM_THREAD in the environment sets it without an edit.
NUM_THREAD = int(__import__("os").environ.get("DND_NUM_THREAD", "0") or 0)
# (f387) For a night that tries the world's voice warmer: DND_TEMP_ADD is added to the temperature of every call already warm (0.5 and up:
# the narrator, the frames, everyone who speaks) - never the cold ones that read the player's line or judge (0.1-0.4), and never the night
# bot's own lines (BOT_TASKS), so two nights differ only in how the world writes. DND_REPEAT_ADD is added to repeat_penalty wherever a
# call sets one (prose and speech). (f393) +0.15 and +0.1 are the default since the night that tried them: wording reused from earlier
# passages roughly halved, and townsfolk replies sent back halved; the words of other alphabets it brought into one narration in a
# hundred are sent back by the content guard (f390). DND_TEMP_ADD=0 DND_REPEAT_ADD=0 gives the voice as it was.
TEMP_ADD = float(__import__("os").environ.get("DND_TEMP_ADD", "0.15") or 0)
REPEAT_ADD = float(__import__("os").environ.get("DND_REPEAT_ADD", "0.1") or 0)
WARM_FROM = 0.5
BOT_TASKS = ("player_line",)
DEFAULT_TEMPERATURE = 0.8
LOG_PATH = "logs/llm_calls.jsonl"
PULSE_LOG_PATH = "logs/pulse.jsonl"   # (f355) what the world did: every pulse event and every one the player met (engine/pulselog.py, tools/world_report.py)
DEBUG = False
MAX_TOKENS = 800
# (f375) The most one narration or one reply may run to, so a runaway generation stops. It is never told to the model and nothing is
# measured against it: no narrator or speaker is given a length any more.
PROSE_MAX_TOKENS = 2048
REQUEST_TIMEOUT = 120
# (f528) Which model server a session talks to: "runtime" (the default: the game starts its own llama-server from runtime/ with the
# model files in models/, llm/runtime.py, as it ships); or "llama", a llama-server started by hand at DND_LLAMA_URL (llm/llama.py
# from_env), for a measurement beside one. The suite drops every DND_* setting and, under MERAVIA_NO_SERVER, no default ever reaches a
# live server.
BACKEND = (__import__("os").environ.get("DND_BACKEND", "") or "runtime").strip().lower()
CLOSE_WAIT_SECONDS = 2      # (f453) how long a closing campaign waits for its background work (a creation call, people being written) before leaving it behind
COMBAT_NUMBERS = True  # show the numbers under each narrated round (#numbers toggles it in game)
NARRATED_DIALOGUE = True  # wrap conversations in narration (#dialogue toggles it in game)
LOG_MAX_MB = 5            # when logs/llm_calls.jsonl grows past this, it is trimmed
LOG_KEEP_ENTRIES = 300    # how many of the most recent entries survive a trim
LOG_FULL_PROMPTS = False  # True stores every system prompt in full (large); False keeps the first part

AUDIT_ENABLED = True       # a second opinion on risky action plans (several steps, money words, an unmatched verb...); costs two quick model calls on those turns only
TURN_LOG = True            # every line the player types is a row in TURN_LOG_PATH, naming what handled it (engine/turnlog.py)
TURN_LOG_PATH = "logs/turns.jsonl"  # one line per typed line: what handled it; for an interpreted line, what was read and what the audit changed
SESSION_STATS_PATH = "logs/sessions.jsonl"  # one line per session: lines by handler, model calls and failures by task, refusals by kind
REFUSALS_LOG = True
# (f440) Record each play session so the real turn can replay it (engine/recording.py, tools/rerun.py): the save as it opened, every
# input, every model call. DND_RECORD=1 in the environment turns it on without an edit. Only RECORD_KEEP recordings are kept.
RECORD = bool(int(__import__("os").environ.get("DND_RECORD", "0") or 0))
RECORD_KEEP = 5
REFUSALS_LOG_PATH = "logs/refusals.jsonl"   # (f321) every line the game failed to act on, with why and what it asked back
CRASH_LOG_PATH = "logs/crash.log"           # (f449) every fault the game went on without (a turn rolled back) or stopped on, with its traceback
CRASH_KEEP = 50                             # how many of the most recent faults the crash log keeps
AUDIT_LOG = True           # a readable record of every model call, one file per session under logs/audit/ (data/rules/audit_log.yaml)

GAME_TITLE = "Meravia"                      # (f345) the name the home page, the window, the exe and the installer carry
GAME_SUBTITLE = "A tale of gifts unforgiven"
UPDATE_REPO = "treystar3/dnd_ai"            # "owner/repo" of the public GitHub repository whose releases carry the installer; empty turns the update check off
UPDATE_CHECK = True                          # (f364) False for a build whose updates come another way (a store): no release is looked for

VOICED_MENTOR = True        # Maren says her written lines in her own words (False: exactly as written)
FREE_MENTOR = True                           # her speeches are written freely from facts (False: her written lines, one-to-one in her words)
EMBED_MODEL = "nomic-embed-text-970aa74c"    # (f527) the embedding model's GGUF id (about 270 MB): tells how alike two lines are in meaning
EMBED_ENABLED = True                         # False: the game uses its simpler word checks instead
SIM_REPEAT = 0.93                            # a sentence this close in meaning to one the speaker said lately is a repeat
SIM_GESTURE = 0.90                           # the same for a gesture
SIM_ASKED = 0.88                             # the player is asking the same thing again
SIM_TOPIC = 0.60                             # a question is about one of Maren's subjects (or a line touches a concern) when at least this close
SIM_RELEVANT = 0.55                          # a piece of what a character knows about themselves is sent only when this close to the moment
SIM_RESTATE = 0.80                           # a claim this close to what they were given to begin with (home, work, motive) is not new
SIM_STANDOUT = 0.06                          # a moment is close to one person's own life only when it is this much closer to their records than to anyone else's present
SIM_ANSWER_MARGIN = 0.05                     # an opening is sent back as not answering only when something else in the scene is clearly closer
SIM_CANON = 0.62                             # a new claim this close to something already true of them is checked for a contradiction
# (f527) How freely the model writes, by job, is data: data/rules/sampling.yaml (tasks, base, retry_temperature_step), in the data
# hash like every other number the game plays by. SAMPLING is its task table (llm/sampling.py resolve lays SAMPLING_BASE under a
# task's own values on a request to llama-server); DND_TEMP_ADD and DND_REPEAT_ADD above shift it for a night.
_SAMPLING_FILE = __import__("yaml").safe_load((__import__("pathlib").Path(__file__).resolve().parent / "data" / "rules" / "sampling.yaml").read_text(encoding="utf-8"))
SAMPLING = {t: dict(v or {}) for t, v in (_SAMPLING_FILE.get("tasks") or {}).items()}
SAMPLING_BASE = dict(_SAMPLING_FILE.get("base") or {})
RETRY_TEMPERATURE_STEP = float(_SAMPLING_FILE.get("retry_temperature_step") or 0.15)
PROFANITY = "strong"        # how a companion who curses may curse: "off" (the world's own curses only), "mild" (damn, hell...), "strong"
