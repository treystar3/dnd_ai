export const meta = {
  name: 'meravia-bundle',
  description: 'Survey, design or review one bundle of the Meravia rebuild against GOALS.md, the replay rules and the 3060 budget',
  whenToUse: 'At the start of a rebuild bundle (mode survey, then design) and before pushing its diff (mode review). Not for building, and not for small fixes.',
  phases: [
    { title: 'Survey', detail: 'five readers, each searching a different way, for every site the goal touches' },
    { title: 'Gaps', detail: 'a critic asks what the readers missed; the gaps it names are searched' },
    { title: 'Design', detail: 'three designs from different angles' },
    { title: 'Judge', detail: 'each design scored by two rubrics, its claims checked against the code' },
    { title: 'Review', detail: 'five finders over the diff, one lens each' },
    { title: 'Verify', detail: 'a skeptic tries to refute each of the most severe findings' },
    { title: 'Report', detail: 'one write-up for the main session' },
  ],
}

// (f448) The rebuild's workflow: what one context cannot hold (every site a bundle touches), several designs where the choice is wide,
// and independent skeptics on a bundle's diff before it is pushed. Building, and the suite, stay with the one session that drives.
// Tested by tools/sim/workflow_448_test.py, which runs every mode with stand-in agents.
//
// How to run it (from the main session):
//   Workflow({name: 'meravia-bundle', args: {mode: 'survey', goal: '...', plan: '...'}})
//   Workflow({scriptPath: '.claude/workflows/meravia-bundle.js', args: {...}})      // the same, by path
// args:
//   mode          'survey' | 'design' | 'review'                                     (required)
//   goal          what the bundle is for, in a sentence or two                       (required)
//   plan          the rebuild plan's text for this bundle (the plan is a Claude Doc the agents cannot open: paste it in)
//   survey        a survey's report, for mode design
//   base          the git ref the bundle started from, for mode review (default HEAD~1)
//   rounds        how many times the survey's critic looks for gaps (default 1)
//   maxGaps       how many gaps one round searches (default 3; the rest are returned, never dropped)
//   maxVerify     how many review findings are verified (default 4, the most severe; the rest are returned unverified)
//   sweepModel    a cheaper model for the survey's readers, e.g. 'sonnet' (default: the session's model)
// Agents with the defaults: survey 10, design 6, review 9 (fewer when little is found).

const MODES = ['survey', 'design', 'review']
if (!args || !MODES.includes(args.mode) || !args.goal) {
  throw new Error('args needs {mode: "survey" | "design" | "review", goal: "what this bundle is for"}; see the comment at the top of the script')
}
const MODE = args.mode

const GROUND = `Project: Meravia, a text role-playing game in this repository (Python). A local 12B model through Ollama writes the prose and reads what the player types.
Read GOALS.md first: the owner's pillars and recorded decisions are the standard everything is held to.

What this run is about: ${args.goal}
${args.plan ? `\nThe rebuild plan for it:\n${args.plan}\n` : ''}${args.survey ? `\nWhat a survey of the code already found:\n${args.survey}\n` : ''}
Rules this run needs:
- Every turn is decided by the save, its seed and what was typed (engine/streams.py, f439): no unseeded randomness, uuid4, wall clock, or ordering by id() or set iteration in play.
- A recorded session replays exactly (engine/recording.py, tools/rerun.py).
- When a model call fails every try, the turn rolls back and the player is told in the narrator's words (engine/failures.py); the game goes on.
- The target card is an RTX 3060 and no turn may take over a minute (data/rules/card_profile.yaml).
You are read-only: change no file in the repository, and run no test and not the suite (they write to saves/). Reading files, grep, git log/show/diff and short python -c checks are fine.
Cite every claim as file:line.`

// ---------- schemas

const SITES = {
  type: 'object',
  properties: {
    sites: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          symbol: { type: 'string' },
          what: { type: 'string' },
          why: { type: 'string' },
          risk: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['file', 'symbol', 'what', 'why', 'risk'],
      },
    },
  },
  required: ['sites'],
}
const GAPS = {
  type: 'object',
  properties: {
    gaps: {
      type: 'array',
      items: {
        type: 'object',
        properties: { where: { type: 'string' }, look_for: { type: 'string' } },
        required: ['where', 'look_for'],
      },
    },
  },
  required: ['gaps'],
}
const DESIGN = {
  type: 'object',
  properties: {
    angle: { type: 'string' },
    summary: { type: 'string' },
    steps: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          what: { type: 'string' },
          files: { type: 'array', items: { type: 'string' } },
          test: { type: 'string' },
        },
        required: ['what', 'files', 'test'],
      },
    },
    risks: { type: 'array', items: { type: 'string' } },
    owner_questions: { type: 'array', items: { type: 'string' } },
    size: { type: 'string', enum: ['small', 'medium', 'large'] },
  },
  required: ['angle', 'summary', 'steps', 'risks', 'owner_questions', 'size'],
}
const SCORES = {
  type: 'object',
  properties: {
    scores: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          angle: { type: 'string' },
          score: { type: 'integer', minimum: 1, maximum: 10 },
          strengths: { type: 'string' },
          flaws: { type: 'string' },
        },
        required: ['angle', 'score', 'strengths', 'flaws'],
      },
    },
  },
  required: ['scores'],
}
const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          claim: { type: 'string' },
          scenario: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
        },
        required: ['file', 'claim', 'scenario', 'severity'],
      },
    },
  },
  required: ['findings'],
}
const VERDICT = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['confirmed', 'refuted', 'unsure'] },
    reason: { type: 'string' },
  },
  required: ['verdict', 'reason'],
}

// ---------- survey: everything the goal touches, found several ways, then what was missed

if (MODE === 'survey') {
  const LENSES = [
    { key: 'state', how: 'Search by kind of thing: module-level dicts, lists and sets that change at runtime, `global` statements, class attributes set at runtime, lru_cache and other caches, singletons, and anything else that lives as long as the process rather than one campaign or one turn.' },
    { key: 'path', how: 'Follow the code from its entry points (main.py play(), WorldScene.run, turn and handle in scenes/world.py, CombatScene, the background threads in npc/backfill.py and llm/embed.py) and note every site on the way that the goal touches.' },
    { key: 'data', how: 'Search data/ and engine/data_check.py: what the goal would add to or change in the YAML, and what checks it at startup.' },
    { key: 'tests', how: 'Search tools/sim/*_test.py and simlib.py: which tests exercise or monkeypatch the sites the goal touches, what would break, and what nothing covers.' },
    { key: 'history', how: 'Search the history with git log --oneline and git log -S for the names involved: recent features (f4xx) in this area, the decisions their commit messages record, partial fixes and known bugs.' },
  ]
  const sweep = args.sweepModel ? { model: args.sweepModel } : {}
  const seen = new Map()
  const key = (s) => `${s.file}::${s.symbol}`
  const add = (list) => {
    let fresh = 0
    for (const s of list) {
      if (!seen.has(key(s))) { seen.set(key(s), s); fresh++ }
    }
    return fresh
  }

  phase('Survey')
  const found = await parallel(LENSES.map((l) => () => agent(
    `${GROUND}\n\nYour lens (${l.key}): ${l.how}\nReturn every site your lens finds that this run's goal touches. Completeness matters more than polish: a site missed now is a bug in the rebuild later.`,
    { label: `survey:${l.key}`, phase: 'Survey', schema: SITES, ...sweep })))
  add(found.filter(Boolean).flatMap((r) => r.sites))
  log(`${seen.size} sites from ${found.filter(Boolean).length} of ${LENSES.length} readers`)

  const unsearched = []
  const rounds = args.rounds ?? 1
  const cap = args.maxGaps ?? 3
  for (let r = 0; r < rounds; r++) {
    const listing = [...seen.values()].map((s) => `${s.file}:${s.line ?? ''} ${s.symbol}`).join('\n')
    const critic = await agent(
      `${GROUND}\n\nReaders searched with these lenses: ${LENSES.map((l) => l.key).join(', ')}. They found:\n${listing}\n\nWhat is missing? Name modules nobody read and kinds of site nobody looked for, each as a place to look and what to look for there. If the list is complete, return no gaps; do not pad.`,
      { label: `gaps:${r + 1}`, phase: 'Gaps', schema: GAPS })
    const gaps = (critic && critic.gaps) || []
    if (!gaps.length) { log('the critic found nothing missing'); break }
    if (gaps.length > cap) {
      unsearched.push(...gaps.slice(cap))
      log(`${gaps.length - cap} gaps left unsearched this round (returned in the result): ${gaps.slice(cap).map((g) => g.where).join('; ')}`)
    }
    const more = await parallel(gaps.slice(0, cap).map((g, i) => () => agent(
      `${GROUND}\n\nLook in ${g.where} for: ${g.look_for}\nReturn only sites this run's goal touches.`,
      { label: `gap:${r + 1}.${i + 1}`, phase: 'Gaps', schema: SITES, ...sweep })))
    const fresh = add(more.filter(Boolean).flatMap((m) => m.sites))
    log(`gap round ${r + 1}: ${fresh} new sites`)
    if (!fresh) break
  }

  const sites = [...seen.values()]
  const report = await agent(
    `${GROUND}\n\nEvery site the survey found, as JSON:\n${JSON.stringify(sites)}\n\nWrite the map the main session will plan from. Group the sites by what they are, not by who found them. Mark the high-risk ones. Check any site you doubt against the code, and drop it only if the code shows it is wrong. Say what the plan (if one was given) did not foresee, and list the questions only the owner can answer. Plain markdown.`,
    { label: 'report', phase: 'Report' })
  return { mode: MODE, sites, unsearched, report }
}

// ---------- design: independent designs from different angles, judged, then one plan

if (MODE === 'design') {
  const ANGLES = [
    { key: 'smallest', how: 'the smallest change that fully meets the goal: reuse what exists and touch as few files as possible.' },
    { key: 'replay', how: 'the design whose correctness is easiest to prove: determinism and exact replay kept by construction, every step testable against the stub, and a failed model call rolling the turn back while the game goes on.' },
    { key: 'player', how: 'the design that best serves the pillars in GOALS.md as the player feels them, turn time on the 3060 included.' },
  ]
  phase('Design')
  const designs = (await parallel(ANGLES.map((a) => () => agent(
    `${GROUND}\n\nDesign how to build this, from one angle: ${a.how}\nBreak it into numbered features the way this repo does (each with the test that proves it), say what could go wrong, and list what only the owner can decide. Set angle to "${a.key}".`,
    { label: `design:${a.key}`, phase: 'Design', schema: DESIGN })))).filter(Boolean)
  if (!designs.length) throw new Error('no design came back')

  const RUBRICS = [
    { key: 'goals', how: 'GOALS.md: which design best serves the pillars and keeps every recorded owner decision, and which pulls against a goal.' },
    { key: 'engineering', how: 'engineering: replay and determinism safety, how each step is tested, what happens when a model call fails, the size and risk of the change, and turn time on the 3060.' },
  ]
  const judged = (await parallel(RUBRICS.map((r) => () => agent(
    `${GROUND}\n\nScore each design from 1 to 10 by this rubric only: ${r.how}\nCheck what each design says about the code against the code itself; a design built on a wrong reading of it scores low.\nDesigns:\n${JSON.stringify(designs)}`,
    { label: `judge:${r.key}`, phase: 'Judge', schema: SCORES })))).filter(Boolean)
  const totals = designs.map((d) => ({
    angle: d.angle,
    total: judged.reduce((t, j) => t + ((j.scores.find((s) => s.angle === d.angle) || {}).score || 0), 0),
  })).sort((a, b) => b.total - a.total)
  log(`scores: ${totals.map((t) => `${t.angle} ${t.total}`).join(', ')}`)
  const tied = totals.filter((t) => t.total === totals[0].total).map((t) => t.angle)
  const base = tied.length > 1
    ? `The judges tied between ${tied.join(' and ')}: choose between them on the merits, and say why`
    : `Build on the winner (${totals[0].angle})`

  const plan = await agent(
    `${GROUND}\n\nBelow are ${designs.length} designs and ${judged.length} judges' scores. Write one plan. ${base}, and graft in the others' ideas where the judges found them sound. Keep the numbered features, each with its test. Gather every owner question into one list, merging duplicates. Plain markdown.\nDesigns: ${JSON.stringify(designs)}\nScores: ${JSON.stringify(judged)}`,
    { label: 'synthesis', phase: 'Report' })
  return { mode: MODE, designs, judged, totals, plan }
}

// ---------- review: finders with one lens each over the diff, then a skeptic for the most severe findings

const BASE = args.base || 'HEAD~1'
const DIMENSIONS = [
  { key: 'failure', how: "Failure paths. For every model call, file and network call the diff adds or touches: what happens when it times out, raises an error of a type nobody expects, or returns nonsense? Is the turn rolled back and the player told in the narrator's words (engine/failures.py)? Can anything escape to main.py guarded() and end the game?" },
  { key: 'determinism', how: 'Determinism and replay. Any unseeded randomness, uuid4, wall clock, id() or set ordering, or background-thread timing in play? Would a recording made before this diff still replay with tools/rerun.py? If a golden recording was re-blessed, is that justified?' },
  { key: 'goals', how: 'GOALS.md. Does anything the player now sees break a pillar or a recorded owner decision, show the machinery, or pull against a goal in a way that should have gone to the owner first?' },
  { key: 'conventions', how: "The repo's conventions: feature numbers in comments and commit subjects; numbers and content in data/ with a data_check block; a test in tools/sim for each change that fails without it, not one that passes whatever the code does." },
  { key: 'cost', how: 'Turn cost on the 3060 (data/rules/card_profile.yaml): model calls added per turn, prompt growth, retries and waits. Could any turn now pass a minute?' },
]
const rank = (s) => ({ blocker: 0, major: 1, minor: 2 })[s] ?? 3

phase('Review')
const raw = await parallel(DIMENSIONS.map((d) => () => agent(
  `${GROUND}\n\nReview the change from ${BASE} to HEAD: run git log --oneline ${BASE}..HEAD and git diff ${BASE}..HEAD, and read the changed code in full where you need to.\nYour lens only: ${d.how}\nReport defects that a real input or state can reach, each with that path as its scenario. No style points. If there are none, return no findings.`,
  { label: `find:${d.key}`, phase: 'Review', schema: FINDINGS })))
const merged = new Map()                          // two lenses can find one defect: keep it once, with both lenses
raw.forEach((r, i) => ((r && r.findings) || []).forEach((f) => {
  const k = `${f.file}:${f.line ?? ''}`
  const had = merged.get(k)
  if (had) { had.lenses.push(DIMENSIONS[i].key); if (rank(f.severity) < rank(had.severity)) had.severity = f.severity }
  else merged.set(k, { ...f, lenses: [DIMENSIONS[i].key] })
}))
const all = [...merged.values()].sort((a, b) => rank(a.severity) - rank(b.severity))
const cap = args.maxVerify ?? 4
const unverified = all.slice(cap)
if (unverified.length) log(`${unverified.length} findings not verified (returned as unverified): ${unverified.map((f) => `${f.file}:${f.line ?? ''}`).join(', ')}`)
if (!all.length) return { mode: MODE, base: BASE, confirmed: [], unsure: [], refuted: [], unverified: [] }

const checked = (await parallel(all.slice(0, cap).map((f, i) => () => agent(
  `${GROUND}\n\nA reviewer claims a defect in the change from ${BASE} to HEAD:\n${f.file}:${f.line ?? ''}: ${f.claim}\nScenario: ${f.scenario}\nTry to refute it. Read the code and trace the scenario; a short python -c check is fine if it settles the question. Say refuted only if you showed the claim is wrong, confirmed only if you traced the scenario to the failure, and unsure otherwise.`,
  { label: `verify:${i + 1}`, phase: 'Verify', schema: VERDICT }).then((v) => ({ ...f, verdict: v }))))).filter(Boolean)
const by = (kind) => checked.filter((f) => f.verdict && f.verdict.verdict === kind)
return { mode: MODE, base: BASE, confirmed: by('confirmed'), unsure: by('unsure'), refuted: by('refuted'), unverified }
