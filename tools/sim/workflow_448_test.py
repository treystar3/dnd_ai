"""(f448) The rebuild's workflow (.claude/workflows/meravia-bundle.js): survey, design and review modes for a bundle. The script's shape
is checked here in Python (its meta a plain literal, every phase it names declared), and when Node is installed each mode is run with
stand-in agents that answer in the shape their schemas ask for: how many agents each mode starts, that a defect two reviewers found is
kept once with both lenses, that what a limit leaves out is returned and never dropped, that a tie between designs is told to the one
who merges them, and that bad arguments stop it with a clear message."""
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

SCRIPT = Path(".claude/workflows/meravia-bundle.js")
src = SCRIPT.read_text(encoding="utf-8")

# ---- the shape, without running anything
check("the script begins with its meta", src.startswith("export const meta = {"))
meta = src[:src.index("\n}\n") + 2]
check("...a plain literal: no interpolation, calls or spreads", not re.search(r"\$\{|\.\.\.|\(\s*\)|=>", meta), meta[:200])
declared = set(re.findall(r"title: '([^']+)'", meta))
used = set(re.findall(r"phase\('([^']+)'\)", src)) | set(re.findall(r"phase: '([^']+)'", src[len(meta):]))
check("every phase the script uses is declared in its meta", used <= declared and used, (sorted(used - declared), sorted(declared)))
check("...and nothing in it reads the clock or rolls dice (a run must resume)", not re.search(r"Date\.now|Math\.random|new Date\(\)", src))
check("the agents are told they are read-only and must not run the suite", "read-only" in src and "run no test" in src)

# ---- every mode, run with stand-in agents
DRY = r"""
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const body = new AsyncFunction('args', 'agent', 'parallel', 'pipeline', 'log', 'phase', src)
const out = {}
let calls = [], logs = [], prompts = []
const fake = async (prompt, opts = {}) => {
  calls.push(opts.label); prompts.push(prompt)
  const t = opts.schema && opts.schema.required && opts.schema.required[0]
  if (!opts.schema) return 'report'
  if (t === 'sites') return { sites: opts.label.startsWith('gap') ? [{ file: 'npc/x.py', line: 3, symbol: 'CACHE', what: 'w', why: 'y', risk: 'high' }]
    : [{ file: 'engine/a.py', line: 1, symbol: 'A', what: 'w', why: 'y', risk: 'low' }, { file: `engine/${opts.label}.py`, line: 2, symbol: 'B', what: 'w', why: 'y', risk: 'medium' }] }
  if (t === 'gaps') return { gaps: calls.filter((c) => c && c.startsWith('gaps')).length === 1 ? [1, 2, 3, 4].map((i) => ({ where: `mod${i}`, look_for: 'globals' })) : [] }
  if (t === 'angle') return { angle: /design:(\w+)/.exec(opts.label)[1], summary: 's', steps: [{ what: 'w', files: ['f'], test: 't' }], risks: [], owner_questions: ['q'], size: 'small' }
  if (t === 'scores') return { scores: ['smallest', 'replay', 'player'].map((a, i) => ({ angle: a, score: opts.label.includes('goals') ? 5 + i : 9 - i, strengths: '', flaws: '' })) }
  if (t === 'findings') return { findings: opts.label === 'find:failure'
    ? [{ file: 'llm/gateway.py', line: 151, claim: 'c', scenario: 's', severity: 'minor' }, { file: 'x.py', line: 9, claim: 'c', scenario: 's', severity: 'minor' }]
    : opts.label === 'find:cost' ? [{ file: 'llm/gateway.py', line: 151, claim: 'c2', scenario: 's', severity: 'blocker' }, ...[1, 2, 3, 4].map((i) => ({ file: `y${i}.py`, line: i, claim: 'c', scenario: 's', severity: 'major' }))] : [] }
  if (t === 'verdict') return { verdict: ['confirmed', 'unsure', 'refuted'][calls.length % 3], reason: 'r' }
  throw new Error('unknown schema')
}
const parallel = async (thunks) => Promise.all(thunks.map((t) => t().catch(() => null)))
for (const [name, args] of [['survey', { mode: 'survey', goal: 'g', plan: 'p' }], ['design', { mode: 'design', goal: 'g' }], ['review', { mode: 'review', goal: 'g', base: 'abc' }]]) {
  calls = []; logs = []; prompts = []
  const r = await body(args, fake, parallel, null, (m) => logs.push(m), () => {})
  out[name] = { agents: calls.length, logs, result: r, sawPlan: prompts.some((p) => p.includes('The rebuild plan for it:\np')), tiedTold: prompts.some((p) => p.includes('The judges tied between')) }
}
try { await body({ mode: 'nope' }, fake, parallel, null, () => {}, () => {}); out.bad = 'ran' } catch (e) { out.bad = e.message }
console.log(JSON.stringify(out))
"""
node = shutil.which("node")
if not node:
    print("note: Node is not installed here, so the modes were not run (the checks above still hold)")
else:
    with tempfile.TemporaryDirectory() as d:
        dry = Path(d) / "dry.mjs"
        dry.write_text(DRY, encoding="utf-8")
        run = subprocess.run([node, str(dry), str(SCRIPT.resolve())], capture_output=True, text=True, timeout=60)
    check("every mode runs with stand-in agents", run.returncode == 0, (run.stdout + run.stderr)[-600:])
    if run.returncode == 0:
        o = json.loads(run.stdout.strip().splitlines()[-1])
        s, dz, rv = o["survey"], o["design"], o["review"]
        check("a survey starts ten agents with the defaults: five readers, a critic, three gap searches, a report", s["agents"] == 10, s)
        check("...the plan pasted in reaches the agents", s["sawPlan"])
        check("...and the gap past the limit is returned, not dropped", [g["where"] for g in s["result"]["unsearched"]] == ["mod4"], s["result"]["unsearched"])
        check("...with the sites found once each", len(s["result"]["sites"]) == len({(x["file"], x["symbol"]) for x in s["result"]["sites"]}) == 7, s["result"]["sites"])
        check("a design starts six agents: three designs, two judges, one to merge", dz["agents"] == 6, dz)
        check("...and a tie between designs is told to the one who merges them", dz["tiedTold"], dz["logs"])
        check("a review starts nine agents: five lenses, four skeptics", rv["agents"] == 9, rv)
        r = rv["result"]
        kept = r["confirmed"] + r["unsure"] + r["refuted"]
        both = next((f for f in kept if f["file"] == "llm/gateway.py"), None)
        check("...a defect two lenses found is kept once, with both lenses and the graver severity", both is not None and both["lenses"] == ["failure", "cost"]
              and both["severity"] == "blocker" and sum(1 for f in kept + r["unverified"] if f["file"] == "llm/gateway.py") == 1, both)
        check("...the most severe are verified first, and the rest come back unverified", len(kept) == 4 and [f["file"] for f in r["unverified"]] == ["y4.py", "x.py"]
              and all(f["severity"] != "minor" for f in kept), (kept, r["unverified"]))
        check("bad arguments stop it with a clear message", o["bad"].startswith("args needs"), o["bad"])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
