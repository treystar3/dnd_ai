MODEL = "gemma4:12b"
THINK = False
# (f425) The context the model is given for each call. DND_NUM_CTX in the environment sets it for one night: a night of six runs on one
# card reserves this much for every run at once, and no call of the f395 night went past about 10,000 tokens.
NUM_CTX = int(__import__("os").environ.get("DND_NUM_CTX", "0") or 0) or 32768
# (f370) CPU threads the model runner may use, 0 for Ollama's own default (one per core the machine shows). A container that shows every
# core of its host while its quota is a dozen needs this set (the night script sets it from the quota), or the runner's threads fight
# for the quota and the card waits on them; DND_NUM_THREAD in the environment sets it without an edit.
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
KEEP_ALIVE = "30m"          # how long Ollama keeps the model loaded after a call (its default is 5 minutes, and a cold load costs 20-60 seconds)
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
UNLOAD_ON_EXIT = True                        # free the model from memory when the game closes
FREE_MENTOR = True                           # her speeches are written freely from facts (False: her written lines, one-to-one in her words)
EMBED_MODEL = "nomic-embed-text"             # a small helper model (about 270 MB) that tells how alike two lines are in meaning; pulled in the background
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
PROFANITY = "strong"
# How freely the model writes, by job. Characters talking use Google's suggested settings for Gemma (warm, varied); jobs that decide facts or
# summarise what happened run colder. A task not listed uses the temperature its caller gives and the model's other defaults.
DIALOGUE_SAMPLING = {"temperature": 1.0, "top_p": 0.95, "top_k": 64}
# (f347) Ollama's own guard against worn words: a token already used within the last repeat_last_n tokens is made less likely by
# repeat_penalty (Ollama's defaults: 1.1 over the last 64 tokens). An hour's transcript leaned on the same few words passage after passage
# ("steady" 258 times, "rhythmic" 178), so prose gets a firmer penalty over a window that covers a whole passage, and speech a gentler one.
# Measured by a night run (tools/nightrun.py) before any word list is added on top.
PROSE_REPEAT = {"repeat_penalty": 1.15, "repeat_last_n": 256}
SPEECH_REPEAT = {"repeat_penalty": 1.12, "repeat_last_n": 192}
SAMPLING = {
    "hire_chat": {**DIALOGUE_SAMPLING, **SPEECH_REPEAT},      # a companion answering the player
    "mentor_chat": {**DIALOGUE_SAMPLING, **SPEECH_REPEAT},    # Maren answering the player
    "exchange": {**DIALOGUE_SAMPLING, **SPEECH_REPEAT},       # banter, and Maren with the clerk
    "npc_conversation": SPEECH_REPEAT,              # a townsperson answering the player (its temperature comes from the caller)
    "narrate": PROSE_REPEAT, "dialogue_frame": PROSE_REPEAT, "combat_narrate": PROSE_REPEAT,   # the narrator, the frames, the fight
    "moment": PROSE_REPEAT,                        # (f348) what is going on as the player walks in
    "player_line": {**DIALOGUE_SAMPLING, **SPEECH_REPEAT},   # (f368) the night bot's own line, written the way a player types (tools/nightbot.py)
    "mentor_speech": {"temperature": 0.85, "top_p": 0.95, "top_k": 64},   # Maren's lessons: warm, but they carry the guild's rules
    "pair_dynamic": {"temperature": 0.5, "top_p": 0.9},                   # a summary of how two people are with each other
    "persona_details": {"temperature": 0.8, "top_p": 0.95, "top_k": 64},  # a hire's small personal details, written once
    "stranger_read": {"temperature": 0.1},
    "live_judge": {"temperature": 0.1}, "canon_check": {"temperature": 0.1},
}                           # how a companion who curses may curse: "off" (the world's own curses only), "mild" (damn, hell...), "strong"
