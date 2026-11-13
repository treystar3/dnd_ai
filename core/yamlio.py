"""(f558) The one place a game file reads YAML: libyaml's C loader when PyYAML has it, else the pure-Python SafeLoader."""
import yaml

_Loader = getattr(yaml, "CSafeLoader", None) or yaml.SafeLoader


def safe_load(stream):
    """yaml.safe_load, on the fastest safe loader available."""
    return yaml.load(stream, Loader=_Loader)


def row(model, raw, where: str = ""):
    """(f622) One row of an authored file as its model. A key the model does not know is refused, at any depth of the row: left to
    itself the model drops it in silence. The model is not made strict, since a save's older row is read into the same one.
    where: the file, for a loader that collects no problems of its own; the refusal then names it, the row and the key."""
    from pydantic import ValidationError
    try:
        return model.model_validate(raw, extra="forbid")
    except ValidationError as e:
        if not where:
            raise
        rid = (raw.get("id") or raw.get("name") or "") if isinstance(raw, dict) else ""
        said = "; ".join(f"{'.'.join(map(str, x['loc'])) or 'row'}: {x['msg']}" for x in e.errors())
        raise ValueError(f"{where}{' ' + str(rid) if rid else ''}: {said}") from None
