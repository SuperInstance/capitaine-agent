# capitaine-agent

## The problem this models

Picture a crew working a long voyage. The captain keeps the log — and the log
lives on the captain's chart table, where only the captain reads it. A decision
gets made on the midnight watch ("we'll divert around the storm"); by dawn it's
a memory in one person's head, and the crew member who just came on watch has
no record that the decision was ever made, let alone why.

Now swap "person" for "program." One agent decides something; another agent is
supposed to act on it an hour later; the second one is flying blind because the
first never wrote anything down anywhere the second could read. That is the
shape of problem this repository is built around, and it splits cleanly in two:

1. **Coordination.** One lead agent (the *captain*) has to break a goal into
   steps, hand each step to the right sub-agent (a *crew member*), choose a
   sensible way to run them all, and then look back and ask "did that work?"
   **This is what the code in this repo actually implements today.**
2. **Shared memory.** Every agent ought to be able to read what the others
   decided and did, and to ask questions of the accumulated record. That half
   is the fleet's *PLATO* idea. This repo is *designed* to plug into it but
   does **not** wire it up in the current code — see
   [Where PLATO fits (and where it doesn't, yet)](#where-plato-fits-and-where-it-doesnt-yet)
   for the honest version.

`capitaine-agent` is a small Python library (no runtime dependencies, Python
≥ 3.10) for layer 1. It uses a maritime vocabulary on purpose — `vessel`,
`crew`, `mission`, `debrief` — because those words map neatly onto the pieces
of a coordination problem. Read the sailing terms as **labels for coordination
ideas, not as a claim that this software tracks real ships.** There is no
fishing-vessel data, no weather feed, no GPS in here; "vessel" is just the name
the library gives to the coordinator's workspace.

## The five pieces, in the order you need them

A coordination problem has a natural shape, and the code follows it. You define
what you want done, you line up who can do it, you decide how to run it, and you
check the result. Each of those is one module under `capitaine_agent/`.

The example below runs through all five: a `Site Survey` mission where one
*scout* inspects an area and two dependent tasks follow once the scout reports.

### 1. A `Mission` is a goal broken into `Objective`s

A **mission** is a named goal (`Mission`) made of smaller steps. Each step is
an **objective** (`Objective`) — a single piece of work that can *depend on*
other objectives finishing first. An objective can carry **success criteria**
(`SuccessCriterion`), machine-checkable rules like "the count must be greater
than 5" or "the result must contain `ok`," so "is this step done?" is a real
question with a real answer rather than a vibe. A mission can also carry
**constraints** (`Constraint`) — boundary conditions ("finish under one hour",
"stay in budget") it can be checked against. ⚠️ **The default
`Constraint.evaluate()` is a stub** — it always returns `(True, "passed")`.
The hook exists and is called by `Mission.check_constraints()`, but no
built-in constraint does real evaluation. To get real checking you must
subclass `Constraint` and override `evaluate`.

Dependencies are the load-bearing idea. They are what let the captain ask "given
what's finished, what's *ready to start* right now?" — the question at the heart
of layer 1.

### 2. A `Crew` is a roster of sub-agents

A **crew member** (`CrewMember`) is one sub-agent: it has a name, a **role**
(`MemberRole` — `scout`, `worker`, `specialist`, `coordinator`, `observer`), a
set of **capabilities** (free-form strings, e.g. `["recon", "scan"]`), a
**status** (`MemberStatus` — `available`, `busy`, `offline`, `error`), and a
**performance score** from 0.0 to 1.0. The `CrewManager` holds the roster and
answers the questions coordination needs: *who's free?*, *who can do X?*, and
— for a task needing certain capabilities — *who's the best pick?*
(`best_for_task` filters to available members that have every required
capability, then takes the one with the highest performance score).

### 3. `Tactics` picks *how* to run the steps

Once you know *what* and *who*, there's still a choice about *how*: run
everything at once, one careful step at a time, hand it all off, push hard,
or pause and reassess. A **strategy** (`Strategy`) is one such rule. The
`TacticsEngine` keeps six built-in strategies (`full_parallel`,
`sequential_careful`, `delegate_all`, `adaptive_hybrid`, `conservative_hold`,
`aggressive_push`) and scores each one 0.0–1.0 against a **tactical context**
(`TacticalContext`) — a snapshot of time pressure, resource availability, risk,
crew size, how far along the mission is, and how much has failed. "Conservative"
scores high when things are going badly and resources are low; "parallel" scores
high when the crew is big, risk is low, and the clock is ticking. The engine
returns the strategies ranked, so the captain can ask for the single best
(`recommend`) or the whole scored list (`analyze_tactics`).

### 4. The `CapitaineAgent` ties them together

`CapitaineAgent` owns a `CrewManager`, a `TacticsEngine`, and a dictionary of
missions, and provides the verbs that connect them:

- `create_mission` / `add_goal` — build the goal graph.
- `activate_mission(mission_id)` / `get_active_mission()` — set and query the
  active mission. (Not re-exported from the top level; call on the agent
  instance directly.)
- `plan_mission(mission_id)` — turns the dependency graph into **waves**:
  batches of objectives whose dependencies are all satisfied, where everything
  in a batch can run in parallel and each batch must finish before the next.
  (A circular dependency is broken rather than deadlocking — the engine takes
  the first remaining objective and moves on.)
- `delegate_objective` / `delegate_all_ready` — hand ready objectives to the
  best-matching available crew member. **Implementation detail worth knowing:**
  `delegate_objective` derives "required capabilities" by splitting the
  objective's `description` into whitespace-separated words — so the words in
  the description *are* the capability filter. If `description` is empty (as in
  many of the examples above), no capability filtering happens and the engine
  simply picks the available member with the highest `performance_score`.
  There is no separate `required_capabilities` field on `Objective` today;
  if you need precise capability matching, put the capability keywords in the
  description.
- `analyze_tactics` / `recommend_strategy` — read the situation and score
  strategies against it.
- `status` — a JSON-serializable snapshot of the agent, its crew, and its
  active mission.

### 5. A `Debrief` closes the loop

When the objectives are done, `debrief(mission_id)` produces a `DebriefReport`
that rolls the results up: each objective gets an **outcome** (`Outcome` —
`success`, `partial_success`, `failure`, `aborted`, `inconclusive`), crew
members get performance scores, and the whole mission gets a derived outcome
plus a numeric `overall_score` (weighted `0.7 × success_rate + 0.3 × average
crew performance`). This is the after-action record — the thing that, in the
opening story, the next watch would want to read.

### The whole loop in code

```python
from capitaine_agent import CapitaineAgent
from capitaine_agent.agent import AgentConfig
from capitaine_agent.crew import CrewMember, MemberRole

captain = CapitaineAgent(AgentConfig(name="lead", vessel="alpha", verbose=True))

captain.crew.register(CrewMember(
    name="Scout-1", role=MemberRole.SCOUT,
    capabilities=["recon", "scan"], performance_score=0.85,
))
captain.crew.register(CrewMember(
    name="Worker-1", role=MemberRole.WORKER,
    capabilities=["build", "repair"], performance_score=0.9,
))

mission = captain.create_mission("Site Survey", "Survey then service the site")
recon = captain.add_goal(mission.id, "Recon the area")
base  = captain.add_goal(mission.id, "Set up base",  dependencies=[recon.id])
comms = captain.add_goal(mission.id, "Repair comms", dependencies=[recon.id])

waves = captain.plan_mission(mission.id)     # [[recon], [base, comms]]
captain.delegate_all_ready(mission.id)       # hands the ready objective(s) to crew
print(captain.recommend_strategy(mission.id).name)
print(captain.debrief(mission.id).summary())
```

This is the entire surface area of layer 1. Everything else in the library is a
helper around these verbs.

## 🔮 Where PLATO fits (and where it doesn't, yet)

Layer 2 — the *shared memory* half of the opening problem — is where **PLATO**
comes in. PLATO is the fleet's name for a knowledge store that many agents are
meant to read and write together, so that "the log only the captain can read"
becomes "a record every agent can query." The mental model is visible right
inside this repo, in the `.spark/` directory: each file there has frontmatter
declaring a **room** (`room: domain`, `room: decisions`, … — a named category)
and a **type** and **id**, and the file *itself* is one discrete piece of
knowledge in that room. A **tile** is one such piece — one record in a room.
`.spark/` is a local, file-on-disk instance of that pattern; PLATO is intended
to be the shared, server-backed version the whole fleet writes to.

Honest status, verified against the current source:

- The *concept* of PLATO, and the claim that this agent "connects to PLATO for
  fleet coordination," appear in this repo's design notes (`.spark/SHELL.md`,
  `.spark/domain/concept-001.md`, `AGENT.md`) and in the package's own
  description string. An earlier version of this README asserted that every
  event was "logged as a tile in the `capitaine-ai` room on the PLATO tile
  server (`localhost:8847`)."
- **None of that is implemented in the code.** There is no PLATO client, no
  network call, no `localhost:8847`, and no tile-writing logic anywhere under
  `capitaine_agent/` — `pyproject.toml` declares zero runtime dependencies.
  The orchestration layer (layer 1) works standalone and is tested; the
  shared-memory layer (layer 2) is an aspiration referenced in prose, not a
  feature you can call today. Treat any PLATO "integration" as a design intent,
  not a capability, until code for it lands.

## Capability verification

Every claim below was traced to working code and/or a passing test (76 tests,
all green). Markers follow this org's convention:

- ✅ **real today** — traced to working code
- ⚠️ **real but conditional** — works, but needs something external
- 🔮 **aspirational / later phase** — described as a direction, not implemented

### ✅ Real today

| Capability | Where in code |
|------------|---------------|
| Mission/Objective modeling with dependency graphs | `mission.py` — `Mission`, `Objective` |
| `SuccessCriterion` with 6 comparators (eq, gt, lt, gte, lte, contains) | `mission.py` — tested in `TestSuccessCriterion` |
| Wave-based dependency resolution (`plan_mission`) | `agent.py::plan_mission` — tested in `test_plan_mission` |
| Circular-dependency break (takes first remaining, doesn't deadlock) | `agent.py::plan_mission` — the `if not wave` branch |
| Crew roster: register, available, by_role, by_capability | `crew.py::CrewManager` |
| `best_for_task` — filter by capabilities → highest performance | `crew.py::CrewManager.best_for_task` |
| 6 built-in tactical strategies with weighted scoring | `tactics.py::TacticsEngine` — 6 `_score_*` methods |
| `recommend` / `recommend_with_score` / `analyze_tactics` | `tactics.py` + `agent.py` |
| Custom strategy registration (`register_strategy`) | `tactics.py::TacticsEngine` |
| Delegation: `delegate_objective` / `delegate_all_ready` | `agent.py` — tested in `test_delegate_*` |
| Debrief: outcomes, `success_rate`, `overall_score` (0.7×SR + 0.3×crew) | `debrief.py::DebriefReport` |
| `DebriefReport.full_report()` / `lessons_learned` | `debrief.py` — tested in `test_full_report` |
| CLI: 6 subcommands, stateless (no persistence) | `cli.py` |
| `status()` — JSON-serializable agent snapshot | `agent.py::status` |

### ⚠️ Real but conditional

| Capability | Condition |
|------------|-----------|
| `Constraint.evaluate()` | The hook exists and `check_constraints` calls it, but the **default implementation always returns `(True, "passed")`**. Real checking requires subclassing and overriding `evaluate`. No built-in subclass exists. |
| `AgentConfig.max_retries` | The field exists on `AgentConfig` and is tested for round-tripping, but **no retry logic uses it** anywhere in the codebase. It's a reserved config slot, not active behavior. |
| Delegation capability matching | Works correctly, but matches on `description.split()` (whitespace words). An objective described as `"Build the base"` looks for capabilities `["Build", "the", "base"]` — case-sensitive, word-by-word. Use capability keywords in the description if you need precise matching. |

### 🔮 Aspirational / later phase

| Claimed direction | Status |
|-------------------|--------|
| PLATO shared-memory integration | No client, no network call, no `localhost:8847`, zero runtime dependencies. Referenced only in prose (`.spark/`, `AGENT.md`). See [Where PLATO fits](#where-plato-fits-and-where-it-doesnt-yet). |
| `capitaine.ai` product surface | Domain reserved, deliberately not built as a product yet. |

## Installation

Install locally in editable mode (this is the command the repo's own test
instructions use, and the one this README can stand behind):

```bash
git clone https://github.com/SuperInstance/capitaine-agent.git
cd capitaine-agent
pip install -e .
```

The package metadata also defines a `capitaine` console script, so after
installing, the `capitaine` command is available.

## Command-line interface

The CLI is a thin, in-process inspector over the Python API — **state lives
only for the duration of one command**, so a mission you `create-mission` in
one run is not visible to `plan` in the next. It is handy for poking at the
models, not for real sessions. For anything stateful, use the Python API.

```bash
capitaine status                                         # JSON snapshot of the agent + crew
capitaine --verbose create-mission "Site Survey" --priority high
capitaine missions                                       # list missions (in this process)
capitaine add-crew Scout-1 --role scout --capabilities recon scan
capitaine plan <mission-id>                              # print execution waves
capitaine debrief <mission-id>                           # print a debrief summary
```

Global flags: `--name`, `--vessel`, `--verbose`. (`status` always shows a
`Scout-1` and `Worker-1` because the CLI auto-registers two demo crew members
on every run.)

## Python API

The public surface, re-exported from `capitaine_agent`:

| Symbol | What it is |
|--------|------------|
| `CapitaineAgent` | The coordinator. Owns the crew, tactics engine, and missions. |
| `Mission`, `Objective`, `Constraint`, `SuccessCriterion` | Goal modeling (layer 1, piece 1). |
| `CrewManager`, `CrewMember` | The sub-agent roster (piece 2). |
| `TacticsEngine`, `Strategy` | Strategy selection (piece 3). |
| `DebriefReport`, `Outcome` | After-action rollup (piece 5). |

The following methods are real and tested but **not re-exported at the top
level** — import from the submodule or call them on an existing instance:

| Where | Symbol | What it does |
|-------|--------|-------------|
| `TacticsEngine` | `recommend_with_score(ctx)` | Like `recommend` but also returns the numeric score. |
| `TacticsEngine` | `register_strategy(s)` / `remove_strategy(name)` / `get_strategy(name)` | Add, remove, or look up a custom `Strategy`. A custom strategy's `suitability_fn` must match a built-in scorer name (`*_default`) to get a real score; otherwise it gets a flat 0.5. |
| `Strategy` | `priority_boost` field | A float added on top of the suitability score — lets a custom strategy always win. |
| `DebriefReport` | `full_report()` | Like `summary()` but includes the per-objective outcomes, `lessons_learned`, `crew_performance`, and `metadata`. |
| `DebriefReport` | `add_lesson(text)` / `lessons_learned` | Record free-text after-action lessons. Populated by callers, not auto-derived. |
| `Mission` | `check_constraints(ctx)` / `all_constraints_met(ctx)` | Evaluate every constraint; returns `(constraint, passed, message)` triples. |
| `Mission` | `ready_objectives()` | Objectives whose dependencies are all `COMPLETED` and whose own status is `PLANNED`. Used internally by `delegate_all_ready`. |
| `CrewManager` | `complete_task(member_id, success=)` | Mark a busy member's task done (success → available, failure → error). |
| `CrewManager` | `roster()` | Full member list as dicts (id, name, role, status, capabilities, performance). |
| `CrewMember` | `can_perform(cap)` / `clear_task()` / `mark_error()` | Capability check and lifecycle helpers. |

Supporting types live in their modules and are imported from there
(`AgentConfig` and `TacticalContext` are *not* re-exported at the top level):
`MissionStatus`/`Priority` (`mission`), `MemberRole`/`MemberStatus` (`crew`),
`StrategyType`/`TacticalContext` (`tactics`), `ObjectiveOutcome` (`debrief`),
`AgentConfig` (`agent`).

## Testing

```bash
pip install -e ".[dev]"   # pulls pytest, pytest-asyncio, httpx
pytest
```

## Status and where this fits

- **Maturity:** `0.2.0`, declared `Development Status :: 4 - Beta`. A
  coordination library you can run and test today; **not** a shipped product.
- **`capitaine.ai`:** reserved within this org for a future crew-coordination
  surface and deliberately **not built as a product yet**. Nothing in this
  repository should be read as "log into capitaine.ai and use this."
- **Fleet context, stated honestly:** this repo's `AGENT.md` carries an
  inherited "Fleet Neighbors" table (`tminus-dispatcher`, `fleet-bridge`,
  `symphony-runtime`, `composite-headspace`, `i2i-bottle-agent`). Those are
  sketchbook design personas, **not verified integrations** — this package has
  zero runtime dependencies and no code that talks to any of them. The same
  caution applies as with PLATO above: a name appearing in prose is a design
  intent, not a capability. Ecosystem background reading:
  [OpenConstruct Documentation](https://github.com/SuperInstance/openconstruct-docs).

## License

MIT
