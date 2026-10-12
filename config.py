MODEL = "gemma4:12b"
THINK = False
NUM_CTX = 32768
DEFAULT_TEMPERATURE = 0.8
LOG_PATH = "logs/llm_calls.jsonl"
DEBUG = False
MAX_TOKENS = 800
REQUEST_TIMEOUT = 120
COMBAT_NUMBERS = True  # show the numbers under each narrated round (#numbers toggles it in game)
NARRATED_DIALOGUE = True  # wrap conversations in narration (#dialogue toggles it in game)
LOG_MAX_MB = 5            # when logs/llm_calls.jsonl grows past this, it is trimmed
LOG_KEEP_ENTRIES = 300    # how many of the most recent entries survive a trim
LOG_FULL_PROMPTS = False  # True stores every system prompt in full (large); False keeps the first part

AUDIT_ENABLED = True       # a second opinion on risky action plans (several steps, money words, an unmatched verb...); costs two quick model calls on those turns only
TURN_LOG_PATH = "logs/turns.jsonl"  # one line per turn: what was typed, what was read, what the audit changed

UPDATE_REPO = "treystar3/dnd_ai"            # "owner/repo" of the public GitHub repository whose releases carry the installer; empty turns the update check off
