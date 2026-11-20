"""(f787) Every file a tracked document or an agent's instructions cite is in git (SUITE-12, docs/design/33_audit_fix_plan/suite.md;
unneeded-files-5 and unneeded-files-14 of docs/design/32_code_audit/findings_tests_data_other.md).

A record that exists only in this working folder is not in a clone, on the remote or in a worktree an agent builds in, and one mistaken
clean from gone: doc 21 cites its seventy faults' causes from docs/play, which was untracked for 91 commits. An instruction that sends
an agent to a path that was never right costs every agent a search (the bundle workflow named data/rules/card_profile.yaml).
Held here, on the tree as it is:
- every docs/ path a tracked text file cites, and every repository path the live instruction files cite (CLAUDE.md and every tracked
  file under .claude/), is in git's index: a file only on disk does not count, and a new document needs no more than `git add`;
- a cited file held back on purpose passes only when a tracked .gitignore ignores it and a comment of its own says why, on the line
  directly above its pattern (a comment over a run of patterns covers the first alone). One ignored by this machine's
  .git/info/exclude alone does not pass (a clone has none).
Read as no citation of a file: a folder git holds a file under (or a .gitignore holds back), a `module.function` name whose module git
holds (storage/statehash.changes; never a name ending in a file's extension, so engine/budget.yaml is no function of engine/budget.py),
and a pattern holding *, <name> or {a,b}; a doc named by its number (docs/design/29) is the file of that number in its folder. The
paths of code an ordinary document names are not read: a design document names the code as it was.
Not covered: a bare file name in an ordinary document (a report naming its sibling `2026-11-18_x_key.md`), so a document a newly
added one cites by bare name alone is found by hand; a path under a top-level folder git holds nothing in; a relative path
(../measure/x.md); this file itself (its made-up cases name paths that are not there).
Second cases, on a made-up repository: each kind above passes or fails as said, and a file only on disk passes once added.
Run: python tools/sim/cited_files_787_test.py"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF = "tools/sim/cited_files_787_test.py"

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


CH = r"[\w./*<>{}\-]"
LEAD = r"(?<![\w./\\*<>{}\-])"                       # nothing path-like before it: a URL or an absolute path is not this repository's
DOCS = re.compile(LEAD + r"(docs/" + CH + r"*)")
EXTS = ("md", "py", "yaml", "yml", "json", "jsonl", "js", "sh", "bat", "txt", "toml", "iss", "db", "zip", "gz", "csv", "png", "jpg",
        "ico", "html", "css", "cfg", "ini")
BARE = re.compile(LEAD + r"([\w\-]+\.(?:" + "|".join(sorted(EXTS, key=len, reverse=True)) + r"))(?![\w/\-]|\.\w)")
MARKS = set("*<>{}")


def git(root: Path, *args: str, stdin: str | None = None, ok: tuple[int, ...] = (0,)) -> str:
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, input=stdin, text=True, encoding="utf-8")
    if r.returncode not in ok:
        raise RuntimeError(f"git {' '.join(args)}: {r.returncode} {r.stderr.strip()}")
    return r.stdout


def live(rel: str) -> bool:
    """The instructions an agent is given: CLAUDE.md and what is tracked under .claude/."""
    return rel == "CLAUDE.md" or rel.startswith(".claude/")


def citations(root: Path, index: list[str]) -> list[tuple[str, str, bool]]:
    """(path, file:line, bare name) for each docs/ path in a tracked text file, and each repository path in an instruction file."""
    tops = sorted({p.split("/")[0] for p in index if "/" in p}, key=len, reverse=True)
    anywhere = re.compile(LEAD + "((?:" + "|".join(map(re.escape, tops)) + ")/" + CH + "*)") if tops else DOCS
    out = []
    for rel in index:
        if rel == SELF:
            continue
        try:
            raw = (root / rel).read_bytes()
        except OSError:
            continue
        if b"\0" in raw:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        rxs = (anywhere, BARE) if live(rel) else (DOCS,)
        for n, line in enumerate(text.splitlines(), 1):
            for rx in rxs:
                for m in rx.finditer(line):
                    tok = m.group(1).rstrip(".")
                    if tok:
                        out.append((tok, f"{rel}:{n}", rx is BARE))
    return out


def said_why(lines: list[str], n: int) -> bool:
    """A comment of a few words stands directly above line n (1-based): each pattern held back says its own why."""
    above = lines[n - 2].strip() if n >= 2 else ""
    return above.startswith("#") and len(above.strip("# -\t").split()) >= 3


def problems(root: Path) -> dict[str, tuple[str, list[str]]]:
    """Each cited path neither in git's index nor held back with a reason: path -> (what is wrong, where it is cited)."""
    index = [p for p in git(root, "ls-files", "-z").split("\0") if p]
    files = set(index)
    folders = {"/".join(p.split("/")[:i]) for p in index for i in range(1, p.count("/") + 1)}
    names = {p.rsplit("/", 1)[-1] for p in index}
    ignores = {g: (root / g).read_text(encoding="utf-8").splitlines() for g in index if g.rsplit("/", 1)[-1] == ".gitignore"}
    named = set()                                    # the plain paths the tracked ignore files hold back, for a doc named by its number
    for g, lines in ignores.items():
        base = g[: -len(".gitignore")]
        named |= {base + s.strip("/") for s in map(str.strip, lines) if s and s[0] not in "#!" and not set(s) & set("*?[")}
    asked: dict[str, list[str]] = {}                 # the path to ask .gitignore about -> where it is cited
    shown: dict[str, str] = {}                       # that path -> the citation as written
    for tok, where, bare in citations(root, index):
        if MARKS & set(tok):
            continue
        p = tok.rstrip("/")
        if bare:
            if p in names:
                continue
        else:
            if p in files or p in folders:
                continue
            suffix = p.rpartition(".")[2]
            if "." in p.rsplit("/", 1)[-1] and suffix.lower() not in EXTS:
                q = p
                while "." in q.rsplit("/", 1)[-1] and q + ".py" not in files:
                    q = q.rsplit(".", 1)[0]
                if q != p and q + ".py" in files:
                    continue
            parent, _, last = p.rpartition("/")
            if re.fullmatch(r"\d+[a-z]?", last):
                by_number = sorted(f for f in files | named if f.startswith(f"{parent}/{last}_") and "/" not in f[len(parent) + 1:])
                if any(f in files for f in by_number):
                    continue
                p = by_number[0] if by_number else p
        asked.setdefault(p, []).append(where)
        shown.setdefault(p, tok)
    held = set()
    if asked:
        ask = [x for p in asked for x in (p, p + "/")]
        out = git(root, "check-ignore", "-v", "-z", "--no-index", "--stdin", stdin="\0".join(ask) + "\0", ok=(0, 1)).split("\0")
        for source, line, pattern, path in zip(out[0::4], out[1::4], out[2::4], out[3::4]):
            if source in ignores and not pattern.startswith("!") and said_why(ignores[source], int(line)):
                held.add(path.rstrip("/"))
    return {shown[p]: ("on disk, not in git" if (root / p).exists() else "not there", where)
            for p, where in sorted(asked.items()) if p not in held}


def shown(found: dict[str, tuple[str, list[str]]]) -> list[str]:
    return [f"{tok}: {why}, cited at {', '.join(where[:3])}{' and more' if len(where) > 3 else ''}" for tok, (why, where) in found.items()]


# ---- the tree as it is
found = problems(ROOT)
check("(f787) every docs/ path a tracked file cites, and every repository path CLAUDE.md and .claude/ cite, is in git or held back by a "
      ".gitignore line saying why", not found, "\n  " + "\n  ".join(shown(found)))

# ---- second cases, on a made-up repository
tmp = Path(tempfile.mkdtemp(prefix="cited_787_"))
try:
    def put(rel: str, text: str | bytes) -> None:
        f = tmp / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))

    git(tmp, "init", "-q")
    put("docs/a.md", "Cited: docs/gone.md and docs/disk.md and docs/staged.md.\n"
                     "A folder: docs/sub/ and docs/sub, a doc by its number: docs/02 and a held one: docs/29.\n"
                     "Held back: docs/held.md, docs/out/deep/x.md; with no reason: docs/nowhy.md; this machine's only: docs/local.md.\n"
                     "Second in a run under one comment: docs/runmate.md. A file's extension is no function: docs/tool.md.\n"
                     "Patterns: docs/x/*.md, docs/<name>.md, docs/{a,b}.md. Code an ordinary document names: engine/gone.py.\n")
    put("docs/sub/x.md", "x\n")
    put("docs/02_thing.md", "x\n")
    put("docs/tool.py", "x = 1\n")
    put("docs/disk.md", "on disk only\n")
    put("docs/staged.md", "added, not committed\n")
    put("docs/held.md", "held back, on disk\n")
    put("tools/t.py", '"""A docstring citing docs/gone2.md."""\n')
    put("tools/sim/x_test.py", "x = 1\n")
    put("storage/statehash.py", "def changes(): pass\n")
    put("engine/turn.py", "x = 1\n")
    put("engine/budget.py", "x = 1\n")
    put("data/measured/card_profile.yaml", "card: x\n")
    put("GOALS.md", "goals\n")
    put("CLAUDE.md", "See storage/statehash.changes, tools/sim and GOALS.md; the card is data/rules/card_profile.yaml; read GOAL.md.\n"
                     "The minute is engine/budget.yaml.\n")
    put(".claude/skills/s/SKILL.md", "Add tools/sim/<name>_<NNN>_test.py; the turn is engine/gone.py.\n")
    put("blob.bin", b"\0docs/gone4.md\0")
    put(".gitignore", "# (f787) awaiting the owner's reading\n/docs/29_plan.md\n# the trial's raw answers, kept out\n/docs/out/\n"
                      "# held back until the owner decides\n/docs/held.md\n/docs/runmate.md\n\n/docs/nowhy.md\n")
    put(".git/info/exclude", "/docs/local.md\n")
    put("notes.md", "Never added: docs/gone3.md\n")
    git(tmp, "add", "docs/a.md", "docs/sub/x.md", "docs/02_thing.md", "docs/tool.py", "docs/staged.md", "tools/t.py", "tools/sim/x_test.py",
        "storage/statehash.py", "engine/turn.py", "engine/budget.py", "data/measured/card_profile.yaml", "GOALS.md", "CLAUDE.md",
        ".claude/skills/s/SKILL.md", "blob.bin", ".gitignore")
    made = problems(tmp)
    check("a cited path that is not there fails, and so does one on disk that git has not been given, each said as such",
          made.get("docs/gone.md", ("",))[0] == "not there" and made.get("docs/disk.md", ("",))[0] == "on disk, not in git", shown(made))
    check("a file added but not committed passes: a new document needs no more than git add", "docs/staged.md" not in made, shown(made))
    check("a folder git holds a file under passes, with or without its slash, and a doc named by its number is the file of that number",
          not {"docs/sub/", "docs/sub", "docs/02"} & set(made), shown(made))
    check("a file held back by a .gitignore line under a comment passes, on disk or not, inside a held folder too, and by its number",
          not {"docs/held.md", "docs/out/deep/x.md", "docs/29"} & set(made), shown(made))
    check("one ignored by a pattern with no comment saying why fails, so does the second of a run under one comment, and so does one "
          "this machine's .git/info/exclude alone ignores", {"docs/nowhy.md", "docs/runmate.md", "docs/local.md"} <= set(made), shown(made))
    check("a path ending in a file's extension is never read as a module.function name: engine/budget.yaml and docs/tool.md fail though "
          "engine/budget.py and docs/tool.py are tracked", {"engine/budget.yaml", "docs/tool.md"} <= set(made), shown(made))
    check("a pattern holding *, <name> or {a,b} is no citation of a file", not {t for t in made if MARKS & set(t)}, shown(made))
    check("every tracked text file is read for docs/ paths (a docstring among them), one never added is not, nor a binary file",
          "docs/gone2.md" in made and "docs/gone3.md" not in made and "docs/gone4.md" not in made, shown(made))
    check("the instructions are read for any repository path: a module.function name and a folder pass, a path never right fails, and "
          "so does a root file named wrong",
          {"data/rules/card_profile.yaml", "GOAL.md"} <= set(made)
          and not {"storage/statehash.changes", "tools/sim", "GOALS.md"} & set(made), shown(made))
    check("the code an ordinary document names is not read; the same path in an instruction file is",
          made.get("engine/gone.py", ("", []))[1] == [".claude/skills/s/SKILL.md:1"], made.get("engine/gone.py"))
    check("nothing else is reported", set(made) == {"docs/gone.md", "docs/disk.md", "docs/nowhy.md", "docs/runmate.md", "docs/local.md",
                                                     "docs/tool.md", "docs/gone2.md", "data/rules/card_profile.yaml", "GOAL.md",
                                                     "engine/budget.yaml", "engine/gone.py"}, shown(made))
    git(tmp, "add", "docs/disk.md")
    check("the file on disk passes once added", "docs/disk.md" not in problems(tmp))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
