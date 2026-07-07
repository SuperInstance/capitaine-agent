# EDUCATIONAL_NOTES — capitaine-agent README rewrite

Notes on the specific choices made in this rewrite, and — more importantly —
the mismatches found between the old `README.md`, the actual source, and the
org's stated status of `capitaine.ai`. A human should read the "Discrepancies"
section and decide which document is stale; I did not silently reconcile them.

## How I verified things

I read every file under `capitaine_agent/` (`agent.py`, `mission.py`, `crew.py`,
`tactics.py`, `debrief.py`, `cli.py`, `__init__.py`), the full test suite
(`tests/test_capitaine_agent.py`), `pyproject.toml`, and the `.spark/` notes,
and grepped the whole tree for `PLATO`, `tile`, `localhost:8847`,
`log_voyage`, `--voyage`, etc. Every install command, CLI subcommand/flag,
class name, method name, enum value, and weighting in the new README was taken
directly from that source.

## The big finding: the old README described a product that isn't in the code

The old README's headline features did not match the implementation. This is
not a wording problem; the claims were about an imagined surface that does not
exist in the repo.

| Old README claimed | What the code actually has |
|---|---|
| `capitaine --voyage` / `--crew` / `--qa` / `--status` flags | No such flags. Real CLI is subcommands: `status`, `create-mission`, `plan`, `missions`, `add-crew`, `debrief`, with global `--name` / `--vessel` / `--verbose`. |
| `from capitaine_agent import log_voyage, log_crew_event, query_maritime` | These functions do not exist. `__init__.py` exports `CapitaineAgent`, `Mission`, `Objective`, `Constraint`, `SuccessCriterion`, `CrewManager`, `CrewMember`, `TacticsEngine`, `Strategy`, `DebriefReport`, `Outcome`. |
| `log_voyage(departure=…, destination=…, crew=5)` | No concept of departure/destination/catch/weather anywhere. The library has no maritime data model at all. |
| "logged as a tile in the `capitaine-ai` room on the PLATO tile server (`localhost:8847`)" | No PLATO client, no network code, no `localhost:8847`. `pyproject.toml` has `dependencies = []`. Zero network imports in the package. |
| "Captain's AI First Mate for capitaine.ai — voyage logging, maritime Q&A" | The code is a **generic multi-agent orchestration library** (mission planning, crew delegation, tactical strategy scoring, debrief) wearing a maritime metaphor. |

**Decision:** Per `STYLE_BRIEF.md` ("don't invent a new claim, feature, or
capability"; "this is explanation added, not content removed"), I did **not**
reproduce any unimplemented feature as if it were real. The new README
describes what the code actually does, using the repo's own maritime vocabulary
as the concrete example layer — because that vocabulary is load-bearing in the
API (`vessel`, `crew`, `mission`, `debrief`) and the brief explicitly favors one
well-chosen concrete example over abstract general statements.

## The PLATO question, handled honestly

The brief asked me to define "PLATO tile" verified against the real source
("don't assume"). I could **not** verify a PLATO mechanism from this repo's
source — the only places PLATO appears are prose (`AGENT.md`, `.spark/SHELL.md`,
`.spark/domain/concept-001.md`, the `pyproject.toml` description/keywords, and
the old README). There is no code that defines, calls, or documents a tile
protocol.

What I *could* verify, and used: the `.spark/` directory is itself a working,
local instance of the "rooms hold discrete knowledge pieces" pattern — each
file's frontmatter has `room:` / `type:` / `id:`. So I defined **room** and
**tile** from that concrete evidence (a room is a named category; a tile is one
record within it), described PLATO as the intended fleet-wide, server-backed
version of that same pattern, and stated plainly that the connection is not
implemented in code. I deliberately did **not** repeat "`localhost:8847`" or
"the `capitaine-ai` room" as fact, because nothing in the source substantiates
those specifics and the old README is the document under suspicion.

**Flag for a human:** the `pyproject.toml` description and keywords still
advertise PLATO integration, fishing, and voyage logging
(`keywords = ["plato", "maritime", "captain", "fishing", "voyage", "crew"]`).
If the orchestration-only reading is correct, those strings overclaim too. I
left `pyproject.toml` alone (out of scope for a README pass) but note it here.

## The capitaine.ai / product-readiness mismatch

The brief states a design decision made earlier this session: `capitaine.ai` is
reserved for a future crew-coordination surface and is **explicitly not built
as a product yet**, with `purplepincher/capitaine-family-worker` as the honest
placeholder currently live on the domain.

The old README's framing ("Captain's AI First Mate **for capitaine.ai**", with
working install + Q&A examples) implied exactly the kind of real-world
readiness that placeholder admits isn't there yet. I flagged this in the new
README's "Status and where this fits" section rather than smoothing it over:
the package is Beta, `capitaine.ai` is reserved/not-a-product, and nothing here
means "log into capitaine.ai and use this."

**Flag for a human:** `capitaine.ai` itself is not in this repo and I could not
fetch the placeholder worker from here, so I'm relying on the brief's account
of that decision. If the placeholder worker's README disagrees with the
"reserved, not a product" framing, that's a contradiction a human should
resolve — I did not invent facts to make the two agree.

## Pedagogical choices (per STYLE_BRIEF.md)

1. **Motivate before mechanize.** Opened with the brief's coordination parable
   (captain's log only the captain reads; midnight decision lost by dawn; new
   watch is blind) before any class name appears. The parable is what makes
   "why would I want a shared memory layer?" land before PLATO is named.
2. **One document, not two tiers.** No TL;DR / ELI5 bolt-on. The newcomer and
   the engineer read the same five-piece walkthrough; precision (dependency
   resolution, wave planning, the `0.7 × success_rate + 0.3 × crew` weighting,
   the circular-dependency break behavior) is kept inline rather than hidden.
3. **Define every term at first use, inline.** mission, objective, success
   criterion, constraint, crew member, role, capability, status, strategy,
   tactical context, debrief, outcome, room, tile — each gets a one-clause
   definition the moment it's needed, not a glossary.
4. **Build concepts in the order they're needed.** Mission → Crew → Tactics →
   Captain (which composes them) → Debrief (which closes the loop) → PLATO
   (the not-yet layer). Tactics is introduced *after* Crew because the scoring
   functions reference crew size; Debrief is last because it consumes the
   outcomes of everything before it.
5. **One concrete example throughout.** The `Site Survey` mission (scout →
   base/comms with dependencies) is drawn from `test_full_workflow` in the test
   suite, so it's known-good against the real API, and it carries across all
   five sections instead of five disconnected snippets.
6. **No precision lost to approachability.** Every real method name, enum
   value, flag, and numeric weighting from the source is present. The only
   things removed were the false claims listed in the table above — which is
   accuracy *gained*, not detail lost.

## Small choices worth naming

- **Install command:** the old README led with `pip install capitaine-agent`
  (implying a published PyPI package). I could not verify publication, and the
  repo's own Testing section uses editable install, so the new README leads
  with the verified `pip install -e .` and notes the `capitaine` console script
  that `pyproject.toml`'s `[project.scripts]` registers.
- **CLI caveat:** the CLI holds state only within a single process (no
  persistence layer), so `create-mission` then `plan <id>` in two separate
  runs won't share state. I called this out explicitly so an engineer isn't
  surprised, and pointed stateful use at the Python API.
- **`AgentConfig` / `TacticalContext` import path:** these are defined in their
   submodules and intentionally *not* re-exported by `__init__.py`, so the API
   table notes they must be imported from `capitaine_agent.agent` /
   `capitaine_agent.tactics`. The code example imports `AgentConfig` from
   `capitaine_agent.agent` accordingly — the top-level import the old README
   style implied would not work for these two.
- **Scope:** I rewrote `README.md` only. I did not touch `AGENT.md`,
  `pyproject.toml`, `.spark/`, or the source, even though several of them
  repeat the same overclaims — that's a broader cleanup a human should
  sequence, not something to fold into a README pedagogy pass.
