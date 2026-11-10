"""(f558) The one place a game file reads YAML: libyaml's C loader when PyYAML has it, else the pure-Python SafeLoader."""
import yaml

_Loader = getattr(yaml, "CSafeLoader", None) or yaml.SafeLoader


def safe_load(stream):
    """yaml.safe_load, on the fastest safe loader available."""
    return yaml.load(stream, Loader=_Loader)
