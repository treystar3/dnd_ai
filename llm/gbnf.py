"""(f527) A contract's schema as the grammar llama-server is sent (the owner's fence choice, 6 Nov: the grammar itself as `grammar`,
never response_format, whose Gemma 4 chat parser writes a ```json fence into every answer: six tokens a call and 7 of 45 answers lost
on the pod).

This is llama.cpp's own converter (common/json-schema.cpp and common/json-schema-to-grammar.cpp at the shipped commit, 39febd2)
written out in Python, rule for rule, so the grammar the game sends is byte for byte the one the server would have built from the
schema itself. Checked against the C++ converter built from that commit on all 88 contract schemas and 24 synthetic ones (6 Nov);
tools/sim/rebless_527_test.py holds seven of those grammars as the C++ wrote them (three contracts, four synthetic schemas) and
compares. The subset is the server's: $ref into the same document, anyOf/oneOf (and a type list), allOf, const, enum, null, boolean, number,
integer with bounds, string with a length or a format (date, time, date-time, uuid), arrays with item bounds, tuples, objects with
properties and additionalProperties. A string pattern is refused here (the C++ translates some patterns and accepts any string for
the rest, which this port does not follow): no contract has one, and the startup check says so if one ever gains one, before a
grammar could quietly differ from the server's.

grammar(schema) is pure: the same schema gives the same text. The game caches it per schema fingerprint (llm/llama.py)."""
from __future__ import annotations

import json

INT64_MIN, INT64_MAX = -(2 ** 63), 2 ** 63 - 1
INT_MAX = 2 ** 31 - 1                     # std::numeric_limits<int>::max(): "no bound" for repetitions and digit counts
RECURSIVE_LIMIT = 128                     # COMMON_RECURSIVE_LIMIT


class SchemaError(ValueError):
    """The schema is outside what the server's converter (and this port) takes."""


# ------------------------------------------------------------------ the normaliser (common/json-schema.cpp)
# Nodes are dicts with a "kind" and the fields the converter reads, built in the C++ builder's own order of decisions.

def _count(schema: dict, key: str, path: str, default: int) -> int:
    if key not in schema:
        return default
    v = schema[key]
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise SchemaError(f"JSON schema error at {path}: {key} must be a non-negative integer")
    return v


def _bound(schema: dict, key: str, path: str, round_up: bool) -> int:
    import math
    v = schema[key]
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise SchemaError(f"JSON schema error at {path}: {key} must be a number")
    if isinstance(v, int):
        return max(INT64_MIN, min(INT64_MAX, v))
    return max(INT64_MIN, min(INT64_MAX, int(math.ceil(v) if round_up else math.floor(v))))   # a bound past int64 is int64's (the C++'s cast is undefined there)


def _format(schema: dict, path: str) -> str:
    if "format" not in schema:
        return ""
    f = schema["format"]
    if not isinstance(f, str):
        raise SchemaError(f"JSON schema error at {path}: format must be a string")
    if f in ("date", "time", "date-time"):
        return f
    if f == "uuid" or (len(f) == 5 and f.startswith("uuid") and f[4] in "12345"):
        return "uuid"
    return ""


class _Builder:
    def __init__(self, root: dict):
        self.root = root
        self.refs: dict[str, dict | None] = {}
        self.depth = 0

    def _resolve(self, ref: str, path: str):
        target = self.root
        tokens = ref[1:].split("/")
        for sel in tokens[1:]:
            if isinstance(target, dict) and sel in target:
                target = target[sel]
            elif isinstance(target, list):
                try:
                    idx = int(sel)
                except ValueError:
                    idx = len(target)
                if idx < 0 or idx >= len(target):
                    raise SchemaError(f"JSON schema error at {path}: cannot resolve $ref {ref}, {sel} is out of range")
                target = target[idx]
            else:
                raise SchemaError(f"JSON schema error at {path}: cannot resolve $ref {ref}, {sel} not found")
        return target

    def _ref(self, value, path: str) -> dict:
        if not isinstance(value, str):
            raise SchemaError(f"JSON schema error at {path}: $ref must be a string")
        if not value.startswith("#/"):
            raise SchemaError(f"JSON schema error at {path}: unsupported $ref {value}, only references into the same document are supported")
        if value not in self.refs:
            self.refs[value] = None                                   # reserved first: a cycle back to this $ref stops here
            self.refs[value] = self.node(self._resolve(value, path), value)
        return {"kind": "ref", "ref": value}

    def _alternatives(self, kind: str, alts, path: str) -> dict:
        if not isinstance(alts, list):
            raise SchemaError(f"JSON schema error at {path}: must be an array of schemas")
        if not alts:
            raise SchemaError(f"JSON schema error at {path}: must not be empty")
        return {"kind": kind, "children": [self.node(a, f"{path}/{i}") for i, a in enumerate(alts)]}

    def _object(self, schema: dict, path: str) -> dict:
        required = {n for n in schema.get("required", []) if isinstance(n, str)} if isinstance(schema.get("required"), list) else set()
        props = []
        if "properties" in schema:
            P = schema["properties"]
            if not isinstance(P, dict):
                raise SchemaError(f"JSON schema error at {path}: properties must be an object")
            for name, prop in P.items():
                props.append((name, self.node(prop, f"{path}/properties/{name}"), name in required))
        additional = None
        if "additionalProperties" in schema:
            a = schema["additionalProperties"]
            if isinstance(a, bool):
                additional = {"kind": "any"} if a else None
            elif isinstance(a, dict):
                additional = self.node(a, f"{path}/additionalProperties")
            else:
                raise SchemaError(f"JSON schema error at {path}: additionalProperties must be a boolean or a schema")
        elif "properties" not in schema:
            additional = {"kind": "any"}                                # {"type": "object"} on its own accepts any object
        return {"kind": "object", "properties": props, "additional": additional}

    def _array(self, schema: dict, path: str) -> dict:
        if "items" in schema or "prefixItems" in schema:
            key = "items" if "items" in schema else "prefixItems"
            items = schema[key]
            if isinstance(items, list):
                return {"kind": "tuple", "items": [self.node(it, f"{path}/{key}/{i}") for i, it in enumerate(items)]}
            item = self.node(items, f"{path}/{key}")
        else:
            item = {"kind": "any"}
        return {"kind": "array", "items": item, "min": _count(schema, "minItems", path, 0), "max": _count(schema, "maxItems", path, -1)}

    def _string(self, schema: dict, path: str) -> dict:
        pattern = ""
        if "pattern" in schema:
            if not isinstance(schema["pattern"], str):
                raise SchemaError(f"JSON schema error at {path}: pattern must be a string")
            pattern = schema["pattern"]
        return {"kind": "string", "pattern": pattern, "format": _format(schema, path),
                "min": _count(schema, "minLength", path, 0), "max": _count(schema, "maxLength", path, -1)}

    def _integer(self, schema: dict, path: str) -> dict:
        lo, hi = INT64_MIN, INT64_MAX
        if "minimum" in schema:
            lo = _bound(schema, "minimum", path, True)
        elif "exclusiveMinimum" in schema:
            lo = _bound(schema, "exclusiveMinimum", path, False) + 1
        if "maximum" in schema:
            hi = _bound(schema, "maximum", path, False)
        elif "exclusiveMaximum" in schema:
            hi = _bound(schema, "exclusiveMaximum", path, True) - 1
        return {"kind": "integer", "min": lo, "max": hi}

    def node(self, schema, path: str) -> dict:
        self.depth += 1
        try:
            if self.depth > RECURSIVE_LIMIT:
                raise SchemaError(f"JSON schema is nested more than {RECURSIVE_LIMIT} levels deep")
            return self._node(schema, path)
        finally:
            self.depth -= 1

    def _node(self, schema, path: str) -> dict:
        if not isinstance(schema, dict):
            raise SchemaError(f"JSON schema error at {path}: schema must be an object")
        if "$ref" in schema:
            return self._ref(schema["$ref"], path)
        if "oneOf" in schema or "anyOf" in schema:
            key = "oneOf" if "oneOf" in schema else "anyOf"
            return self._alternatives("any_of", schema[key], f"{path}/{key}")
        t = schema.get("type")
        if isinstance(t, list):
            if not t:
                raise SchemaError(f"JSON schema error at {path}: type must not be empty")
            return {"kind": "any_of", "children": [self.node({**schema, "type": one}, f"{path}/type/{i}") for i, one in enumerate(t)]}
        if "const" in schema:
            return {"kind": "const", "value": schema["const"]}
        if "enum" in schema:
            values = schema["enum"]
            if not isinstance(values, list) or not values:
                raise SchemaError(f"JSON schema error at {path}: enum must be a non-empty array")
            return {"kind": "enum", "values": list(values)}
        if t is not None and not isinstance(t, str):
            raise SchemaError(f"JSON schema error at {path}: type must be a string or an array of strings")
        type_name = t or ""
        has_properties = "properties" in schema or ("additionalProperties" in schema and schema["additionalProperties"] is not True)
        if not type_name:
            if has_properties:
                return self._object(schema, path)
            if "allOf" in schema:
                return self._alternatives("all_of", schema["allOf"], f"{path}/allOf")
            if "items" in schema or "prefixItems" in schema:
                return self._array(schema, path)
            if "pattern" in schema or "minLength" in schema or "maxLength" in schema or _format(schema, path):
                return self._string(schema, path)
            return {"kind": "any"}
        if type_name == "object":
            if not has_properties and "allOf" in schema:
                return self._alternatives("all_of", schema["allOf"], f"{path}/allOf")
            return self._object(schema, path)
        if type_name == "string":
            if "allOf" in schema:
                return self._alternatives("all_of", schema["allOf"], f"{path}/allOf")
            return self._string(schema, path)
        if type_name == "array":
            return self._array(schema, path)
        if type_name == "integer":
            return self._integer(schema, path)
        if type_name in ("number", "boolean", "null"):
            return {"kind": type_name}
        raise SchemaError(f"JSON schema error at {path}: unrecognized type {type_name}")


# ------------------------------------------------------------------ the converter (common/json-schema-to-grammar.cpp)

SPACE_RULE = '| " " | "\\n"{1,2} [ \\t]{0,20}'

PRIMITIVE_RULES = {
    "boolean": ('("true" | "false")', ()),
    "decimal-part": ("[0-9]{1,16}", ()),
    "integral-part": ("[0] | [1-9] [0-9]{0,15}", ()),
    "number": ('("-"? integral-part) ("." decimal-part)? ([eE] [-+]? integral-part)?', ("integral-part", "decimal-part")),
    "integer": ('("-"? integral-part)', ("integral-part",)),
    "value": ("object | array | string | number | boolean | null", ("object", "array", "string", "number", "boolean", "null")),
    "object": ('"{" space ( string ":" space value ("," space string ":" space value)* )? space "}"', ("string", "value")),
    "array": ('"[" space ( value ("," space value)* )? space "]"', ("value",)),
    "uuid": ('"\\"" [0-9a-fA-F]{8} "-" [0-9a-fA-F]{4} "-" [0-9a-fA-F]{4} "-" [0-9a-fA-F]{4} "-" [0-9a-fA-F]{12} "\\""', ()),
    "char": ('[^"\\\\\\x7F\\x00-\\x1F] | [\\\\] (["\\\\bfnrt] | "u" [0-9a-fA-F]{4})', ()),
    "string": ('"\\"" char* "\\""', ("char",)),
    "null": ('"null"', ()),
}
STRING_FORMAT_RULES = {
    "date": ('[0-9]{4} "-" ( "0" [1-9] | "1" [0-2] ) "-" ( "0" [1-9] | [1-2] [0-9] | "3" [0-1] )', ()),
    "time": ('([01] [0-9] | "2" [0-3]) ":" [0-5] [0-9] ":" [0-5] [0-9] ( "." [0-9]{3} )? ( "Z" | ( "+" | "-" ) ( [01] [0-9] | "2" [0-3] ) ":" [0-5] [0-9] )', ()),
    "date-time": ('date "T" time', ("date", "time")),
    "date-string": ('"\\"" date "\\""', ("date",)),
    "time-string": ('"\\"" time "\\""', ("time",)),
    "date-time-string": ('"\\"" date-time "\\""', ("date-time",)),
}
RESERVED = {"root", *PRIMITIVE_RULES, *STRING_FORMAT_RULES}
_LITERAL_ESCAPES = {"\r": "\\r", "\n": "\\n", '"': '\\"', "\\": "\\\\"}


def dump(value) -> str:
    """nlohmann's dump() of a JSON value: no spaces, non-ASCII as it is, control characters escaped."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def format_literal(literal: str) -> str:
    return '"' + "".join(_LITERAL_ESCAPES.get(c, c) for c in literal) + '"'


def rule_name(name: str) -> str:
    """[^a-zA-Z0-9-]+ -> '-'."""
    out, invalid = [], False
    for c in name:
        if c.isascii() and (c.isalnum() or c == "-"):
            out.append(c)
            invalid = False
        elif not invalid:
            out.append("-")
            invalid = True
    return "".join(out)


def build_repetition(item: str, lo: int, hi: int, separator: str = "") -> str:
    has_max = hi != INT_MAX
    if hi == 0:
        return ""
    if lo == 0 and hi == 1:
        return item + "?"
    if not separator:
        if lo == 1 and not has_max:
            return item + "+"
        if lo == 0 and not has_max:
            return item + "*"
        return item + "{" + str(lo) + "," + (str(hi) if has_max else "") + "}"
    result = item + " " + build_repetition("(" + separator + " " + item + ")", 0 if lo == 0 else lo - 1, hi - 1 if has_max else hi)
    if lo == 0:
        result = "(" + result + ")?"
    return result


def build_min_max_int(lo: int, hi: int, out: list, decimals_left: int = 16, top_level: bool = True) -> None:
    has_min, has_max = lo != INT64_MIN, hi != INT64_MAX

    def digit_range(a: str, b: str) -> None:
        out.append("[" + (a if a == b else a + "-" + b) + "]")

    def more_digits(lo_d: int, hi_d: int) -> None:
        out.append("[0-9]")
        if lo_d == hi_d == 1:
            return
        s = "{" + str(lo_d)
        if hi_d != lo_d:
            s += "," + (str(hi_d) if hi_d != INT_MAX else "")
        out.append(s + "}")

    def uniform_range(a: str, b: str) -> None:
        i = 0
        while i < len(a) and i < len(b) and a[i] == b[i]:
            i += 1
        if i > 0:
            out.append('"' + a[:i] + '"')
        if i < len(a) and i < len(b):
            if i > 0:
                out.append(" ")
            sub_len = len(a) - i - 1
            if sub_len > 0:
                a_sub, b_sub = a[i + 1:], b[i + 1:]
                zeros, nines = "0" * sub_len, "9" * sub_len
                reached = False
                out.append("(")
                if a_sub == zeros:
                    digit_range(a[i], chr(ord(b[i]) - 1))
                    out.append(" ")
                    more_digits(sub_len, sub_len)
                else:
                    out.append("[" + a[i] + "] ")
                    out.append("(")
                    uniform_range(a_sub, nines)
                    out.append(")")
                    if ord(a[i]) < ord(b[i]) - 1:
                        out.append(" | ")
                        if b_sub == nines:
                            digit_range(chr(ord(a[i]) + 1), b[i])
                            reached = True
                        else:
                            digit_range(chr(ord(a[i]) + 1), chr(ord(b[i]) - 1))
                        out.append(" ")
                        more_digits(sub_len, sub_len)
                if not reached:
                    out.append(" | ")
                    digit_range(b[i], b[i])
                    out.append(" ")
                    uniform_range(zeros, b_sub)
                out.append(")")
            else:
                out.append("[" + a[i] + "-" + b[i] + "]")

    if has_min and has_max:
        if lo < 0 and hi < 0:
            out.append('"-" (')
            build_min_max_int(-hi, -lo, out, decimals_left, True)
            out.append(")")
            return
        if lo < 0:
            out.append('"-" (')
            build_min_max_int(0, -lo, out, decimals_left, True)
            out.append(") | ")
            lo = 0
        lo_s, hi_s = str(lo), str(hi)
        for digits in range(len(lo_s), len(hi_s)):
            uniform_range(lo_s, "9" * digits)
            lo_s = "1" + "0" * digits
            out.append(" | ")
        uniform_range(lo_s, hi_s)
        return
    less = max(decimals_left - 1, 1)
    if has_min:
        if lo < 0:
            out.append('"-" (')
            build_min_max_int(INT64_MIN, -lo, out, decimals_left, False)
            out.append(") | [0] | [1-9] ")
            more_digits(0, decimals_left - 1)
        elif lo == 0:
            if top_level:
                out.append("[0] | [1-9] ")
                more_digits(0, less)
            else:
                more_digits(1, decimals_left)
        elif lo <= 9:
            c = chr(ord("0") + lo)
            start = "1" if top_level else "0"
            if c > start:
                digit_range(start, chr(ord(c) - 1))
                out.append(" ")
                more_digits(1, less)
                out.append(" | ")
            digit_range(c, "9")
            out.append(" ")
            more_digits(0, less)
        else:
            lo_s = str(lo)
            c = lo_s[0]
            if c > "1":
                digit_range("1" if top_level else "0", chr(ord(c) - 1))
                out.append(" ")
                more_digits(len(lo_s), less)
                out.append(" | ")
            digit_range(c, c)
            out.append(" (")
            build_min_max_int(int(lo_s[1:]), INT64_MAX, out, less, False)
            out.append(")")
            if c < "9":
                out.append(" | ")
                digit_range(chr(ord(c) + 1), "9")
                out.append(" ")
                more_digits(len(lo_s) - 1, less)
        return
    if has_max:
        if hi >= 0:
            if top_level:
                out.append('"-" [1-9] ')
                more_digits(0, less)
                out.append(" | ")
            build_min_max_int(0, hi, out, decimals_left, True)
        else:
            out.append('"-" (')
            build_min_max_int(-hi, INT64_MAX, out, decimals_left, False)
            out.append(")")
        return
    raise SchemaError("At least one of min_value or max_value must be set")


class _Trie:
    """common_trie: one node per prefix, children by code point in rising order, pattern >= 0 at a word's end."""

    def __init__(self, words: list[str]):
        self.nodes: list[dict] = [{"children": {}, "pattern": -1}]
        for n, w in enumerate(words):
            at = 0
            for ch in w:
                cpt = ord(ch)
                if cpt not in self.nodes[at]["children"]:
                    self.nodes.append({"children": {}, "pattern": -1})
                    self.nodes[at]["children"][cpt] = len(self.nodes) - 1
                at = self.nodes[at]["children"][cpt]
            self.nodes[at]["pattern"] = n


class Converter:
    def __init__(self, dotall: bool = False):
        self.dotall = dotall
        self.rules: dict[str, str] = {"space": SPACE_RULE}
        self.resolving: set[str] = set()
        self.depth = 0
        self.refs: dict[str, dict | None] = {}

    def add_rule(self, name: str, rule: str) -> str:
        esc = rule_name(name)
        if esc not in self.rules or self.rules[esc] == rule:
            self.rules[esc] = rule
            return esc
        i = 0
        while esc + str(i) in self.rules and self.rules[esc + str(i)] != rule:
            i += 1
        key = esc + str(i)
        self.rules[key] = rule
        return key

    def add_primitive(self, name: str, rule: tuple) -> str:
        n = self.add_rule(name, rule[0])
        for dep in rule[1]:
            dep_rule = PRIMITIVE_RULES.get(dep) or STRING_FORMAT_RULES.get(dep)
            if dep_rule is None:
                raise SchemaError(f"Rule {dep} not known")
            if dep not in self.rules:
                self.add_primitive(dep, dep_rule)
        return n

    def union(self, name: str, alts: list) -> str:
        return " | ".join(self.visit(a, name + ("alternative-" if not name else "-") + str(i)) for i, a in enumerate(alts))

    @staticmethod
    def constant(value) -> str:
        return format_literal(dump(value))

    def primitive(self, rule: str, type_: str) -> str:
        return self.add_primitive("root" if rule == "root" else type_, PRIMITIVE_RULES[type_])

    def not_strings(self, strings: list[str]) -> str:
        trie = _Trie(strings)
        char = self.add_primitive("char", PRIMITIVE_RULES["char"])
        out = ['["] ( ']

        def visit(idx: int, depth: int) -> None:
            if depth >= RECURSIVE_LIMIT:
                raise SchemaError(f"JSON schema property name is longer than {RECURSIVE_LIMIT} chars")
            node = trie.nodes[idx]
            rejects, first = "", True
            for cpt in sorted(node["children"]):
                c = chr(cpt)
                rejects += c
                if first:
                    first = False
                else:
                    out.append(" | ")
                out.append("[" + c + "]")
                child = node["children"][cpt]
                if trie.nodes[child]["children"]:
                    out.append(" (")
                    visit(child, depth + 1)
                    out.append(")")
                else:
                    out.append(" " + char + "+")
            if node["children"]:
                out.append(' | [^"' + rejects + "] " + char + "*")
        visit(0, 0)
        out.append(" )")
        if trie.nodes[0]["pattern"] < 0:
            out.append("?")
        out.append(' ["]')
        return "".join(out)

    def resolve_ref(self, node: dict) -> str:
        ref = node["ref"]
        fragment = ref[ref.index("#") + 1:] if "#" in ref else ref
        name = "ref" + rule_name(fragment)
        if name not in self.rules and ref not in self.resolving:
            target = self.refs.get(ref)
            if target is None:
                raise SchemaError(f"Unresolved $ref {ref}")
            self.resolving.add(ref)
            name = self.visit(target, name)
            self.resolving.discard(ref)
        return name

    def object_rule(self, properties: list, required: set, name: str, additional) -> str:
        req, opt, kv, names = [], [], {}, []
        for prop_name, prop in properties:
            prop_rule = self.visit(prop, name + ("-" if name else "") + prop_name)
            kv[prop_name] = self.add_rule(name + ("-" if name else "") + prop_name + "-kv",
                                          format_literal(dump(prop_name)) + ' space ":" space ' + prop_rule)
            (req if prop_name in required else opt).append(prop_name)
            names.append(prop_name)
        if additional is not None:
            sub = name + ("-" if name else "") + "additional"
            value = self.visit(additional, sub + "-value") if additional["kind"] != "any" else self.add_primitive("value", PRIMITIVE_RULES["value"])
            key = self.add_primitive("string", PRIMITIVE_RULES["string"]) if not names else self.add_rule(sub + "-k", self.not_strings(names))
            kv["*"] = self.add_rule(sub + "-kv", key + ' ":" space ' + value)
            opt.append("*")
        if not req and not opt:
            return '"{" space "}"'
        rule = '"{" space '
        for i, k in enumerate(req):
            if i > 0:
                rule += ' "," space '
            rule += kv[k]
        if opt:
            rule += " ("
            if req:
                rule += ' "," space ( '

            def refs(ks: list, first_optional: bool) -> str:
                if not ks:
                    return ""
                k = ks[0]
                comma = '( "," space ' + kv[k] + " )"
                res = comma + ("*" if k == "*" else "?") if first_optional else kv[k] + (" " + comma + "*" if k == "*" else "")
                if len(ks) > 1:
                    res += " " + self.add_rule(name + ("-" if name else "") + k + "-rest", refs(ks[1:], True))
                return res
            for i in range(len(opt)):
                if i > 0:
                    rule += " | "
                rule += refs(opt[i:], False)
            if req:
                rule += " )"
            rule += " )?"
        rule += ' space "}"'
        return rule

    def all_of(self, node: dict, name: str, rule: str) -> str:
        required, properties, enum_values = set(), [], {}

        def add(comp: dict, is_required: bool, depth: int) -> None:
            if depth >= RECURSIVE_LIMIT:
                raise SchemaError(f"JSON schema is nested more than {RECURSIVE_LIMIT} levels deep")
            if comp["kind"] == "ref":
                target = self.refs.get(comp["ref"])
                if target is not None:
                    add(target, is_required, depth + 1)
            elif comp["kind"] == "object":
                for prop_name, prop, _ in comp["properties"]:
                    properties.append((prop_name, prop))
                    if is_required:
                        required.add(prop_name)
            elif comp["kind"] == "enum":
                for v in comp["values"]:
                    c = self.constant(v)
                    enum_values[c] = enum_values.get(c, 0) + 1
        for child in node["children"]:
            if child["kind"] == "any_of":
                for alt in child["children"]:
                    add(alt, False, 0)
            else:
                add(child, True, 0)
        if enum_values:
            meet = [c for c in sorted(enum_values) if enum_values[c] == len(node["children"])]
            if meet:
                return self.add_rule(rule, "(" + " | ".join(meet) + ")")
        return self.add_rule(rule, self.object_rule(properties, required, name, None))

    def visit(self, node: dict, name: str) -> str:
        self.depth += 1
        try:
            if self.depth > RECURSIVE_LIMIT:
                raise SchemaError(f"JSON schema is nested more than {RECURSIVE_LIMIT} levels deep")
            return self._visit(node, name)
        finally:
            self.depth -= 1

    def _visit(self, node: dict, name: str) -> str:
        rule = name + "-" if name in RESERVED else (name or "root")
        sub = name + ("-" if name else "")
        kind = node["kind"]
        if kind == "ref":
            return self.add_rule(rule, self.resolve_ref(node))
        if kind == "any_of":
            return self.add_rule(rule, self.union(name, node["children"]))
        if kind == "all_of":
            return self.all_of(node, name, rule)
        if kind == "const":
            return self.add_rule(rule, self.constant(node["value"]))
        if kind == "enum":
            return self.add_rule(rule, "(" + " | ".join(self.constant(v) for v in node["values"]) + ")")
        if kind == "object":
            add = node["additional"]
            if not node["properties"] and add is not None and add["kind"] == "any":
                return self.add_rule(rule, self.add_primitive("object", PRIMITIVE_RULES["object"]))
            return self.add_rule(rule, self.object_rule([(n, p) for n, p, _ in node["properties"]],
                                                        {n for n, _, r in node["properties"] if r}, name, add))
        if kind == "tuple":
            text = '"[" space '
            for i, item in enumerate(node["items"]):
                if i > 0:
                    text += ' "," space '
                text += self.visit(item, sub + "tuple-" + str(i))
            return self.add_rule(rule, text + ' space "]"')
        if kind == "array":
            if node["items"]["kind"] == "any" and node["min"] == 0 and node["max"] < 0:
                return self.primitive(rule, "array")
            item = self.visit(node["items"], sub + "item")
            hi = INT_MAX if node["max"] < 0 else node["max"]
            return self.add_rule(rule, '"[" space ' + build_repetition(item, node["min"], hi, '"," space') + ' space "]"')
        if kind == "string":
            if node["pattern"]:
                raise SchemaError(f"the string pattern {node['pattern']!r} is not converted here: the server's converter translates some "
                                  "patterns and accepts any string for the rest, which this port does not follow")
            if node["format"] == "uuid":
                return self.primitive(rule, "uuid")
            if node["format"]:
                prim = node["format"] + "-string"
                return self.add_rule(rule, self.add_primitive(prim, STRING_FORMAT_RULES[prim]))
            if node["min"] > 0 or node["max"] >= 0:
                char = self.add_primitive("char", PRIMITIVE_RULES["char"])
                hi = INT_MAX if node["max"] < 0 else node["max"]
                return self.add_rule(rule, '"\\"" ' + build_repetition(char, node["min"], hi) + ' "\\""')
            return self.primitive(rule, "string")
        if kind == "integer":
            if node["min"] == INT64_MIN and node["max"] == INT64_MAX:
                return self.primitive(rule, "integer")
            out = ["("]
            build_min_max_int(node["min"], node["max"], out)
            out.append(")")
            return self.add_rule(rule, "".join(out))
        if kind in ("number", "boolean", "null"):
            return self.primitive(rule, kind)
        if kind == "any":
            return self.add_rule(rule, self.add_primitive("value", PRIMITIVE_RULES["value"]))
        raise SchemaError(f"unknown node kind {kind}")

    def text(self) -> str:
        return "".join(f"{k} ::= {v}\n" for k, v in sorted(self.rules.items()))


def grammar(schema: dict) -> str:
    """The GBNF llama-server's converter builds from this schema (SchemaError when the schema is outside the subset)."""
    b = _Builder(schema)
    root = b.node(schema, "#")
    c = Converter()
    c.refs = b.refs
    c.visit(root, "")
    return c.text()
