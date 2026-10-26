MODEL = "gemma4:12b"
THINK = False
NUM_CTX = 32768
DEFAULT_TEMPERATURE = 0.8
LOG_PATH = "logs/llm_calls.jsonl"
DEBUG = False
MAX_TOKENS = 800
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
REFUSALS_LOG_PATH = "logs/refusals.jsonl"   # (f321) every line the game failed to act on, with why and what it asked back
AUDIT_LOG = True           # a readable record of every model call, one file per session under logs/audit/ (data/rules/audit_log.yaml)

GAME_TITLE = "Meravia"                      # (f345) the name the home page, the window, the exe and the installer carry
GAME_SUBTITLE = "A tale of gifts unforgiven"
UPDATE_REPO = "treystar3/dnd_ai"            # "owner/repo" of the public GitHub repository whose releases carry the installer; empty turns the update check off

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
SAMPLING = {
    "hire_chat": DIALOGUE_SAMPLING,                 # a companion answering the player
    "mentor_chat": DIALOGUE_SAMPLING,               # Maren answering the player
    "exchange": DIALOGUE_SAMPLING,                  # banter, and Maren with the clerk
    "mentor_speech": {"temperature": 0.85, "top_p": 0.95, "top_k": 64},   # Maren's lessons: warm, but they carry the guild's rules
    "pair_dynamic": {"temperature": 0.5, "top_p": 0.9},                   # a summary of how two people are with each other
    "persona_details": {"temperature": 0.8, "top_p": 0.95, "top_k": 64},  # a hire's small personal details, written once
    "stranger_read": {"temperature": 0.1},
    "live_judge": {"temperature": 0.1}, "canon_check": {"temperature": 0.1},
}                           # how a companion who curses may curse: "off" (the world's own curses only), "mild" (damn, hell...), "strong"
