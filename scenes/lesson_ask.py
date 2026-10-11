"""The model's two small parts of a lesson: reading the request, and naming and describing what the engine planned."""
from engine import lessons
from llm import prompts
from llm.contracts import LessonNames, LessonWant
from llm.gateway import LLMError, generate


def read_request(c, request: str) -> lessons.Want:
    """What the player is after. The model reads it; a word list does if the model cannot."""
    try:
        read = generate("lesson_want", prompts.WANT_SYSTEM, prompts.want_user(c, request), LessonWant, max_tokens=120,
                        temperature=0.1, retries=1)
        return lessons.from_model(read, request)
    except LLMError:
        return lessons.from_words(request)


def write(c, request: str, slots: list[dict]) -> list:
    """Abilities and passives for the planned slots. Strict wording checks first, then a lenient retry (the engine's plan stands).
    Raises LLMError if the model cannot produce names at all."""
    reserved = [a.name for a in c.actives] + [p.name for p in c.passives]
    user = prompts.lesson_user(c, request, lessons.slot_lines(slots))
    try:
        names = generate("generate_lessons", prompts.LESSON_SYSTEM, user, LessonNames, max_tokens=1400,
                         validation_context={"slots": slots, "strict": True, "reserved_names": reserved})
    except LLMError:
        names = generate("generate_lessons", prompts.LESSON_SYSTEM, user, LessonNames, max_tokens=1400, retries=1,
                         validation_context={"slots": slots, "strict": False, "reserved_names": reserved})
    return lessons.build(slots, names)
