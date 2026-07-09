# Architecture — capitaine-agent

This document explains the three non-obvious design decisions in this library
at more depth than the README allows. Each was verified against the source
listed in parentheses.

## 1. Wave-based dependency resolution (`agent.py::plan_mission`)

The core planning algorithm turns a flat list of `Objective`s (each optionally
depending on others by ID) into **waves** — ordered batches where everything
in a batch can run in parallel and each batch must finish before the next.

```
Wave 1: [A]           ← no dependencies
Wave 2: [B, C]        ← both depend on A, can run together
Wave 3: [D]           ← depends on B
```

### The algorithm (paraphrased from source)

```
remaining  = all objectives, keyed by id
completed  = {}                          # IDs already placed in a wave

while remaining is not empty:
    wave = [o for o in remaining if every dep of o is in completed]

    if wave is empty:                    # circular dependency!
        wave = [first remaining objective]   # break the cycle

    for each o in wave:
        remove o from remaining
        add o.id to completed

    append wave to result
```

### Why this design?

- **No topological sort library needed.** The algorithm is ~15 lines of plain
  Python with zero dependencies — consistent with the package's `dependencies
  = []` constraint.
- **Parallelism is a first-class output.** Each wave *is* the set of things
  that can run concurrently. A caller doesn't need to re-derive this.
- **Cycle-breaking is deterministic.** When a cycle exists (A→B→A), the
  algorithm doesn't deadlock — it grabs the first remaining objective by
  dict-iteration order and moves it into a wave, then continues. This means
  cycles are *silently broken*, not *detected and reported*. If you need
  cycle detection, you must add it yourself.

### What it does NOT do

- It does not validate that dependency IDs actually exist. If objective X
  depends on `"nonexistent"`, the dependency is simply never in `completed`,
  so X stays unplaceable until the cycle-break kicks in and forces it into a
  wave. No error is raised.
- It does not check whether dependencies form a valid DAG. It just works
  forward.
- `completed` here means "placed in a wave," **not** "mission-status
  COMPLETED." The wave planner is purely structural — it doesn't care about
  runtime status. The *delegation* logic (`delegate_all_ready` →
  `Mission.ready_objectives`) is what respects runtime status.

## 2. The tactics scoring system (`tactics.py`)

The `TacticsEngine` scores six built-in strategies against a `TacticalContext`
(a snapshot of the operational situation). Each strategy has a dedicated
scoring function with specific weights. Understanding these weights is the key
to predicting what the engine will recommend.

### The context dimensions

| Field | Range | Meaning |
|-------|-------|---------|
| `time_pressure` | 0.0–1.0 | 0 = no rush, 1 = critical deadline |
| `resource_availability` | 0.0–1.0 | 0 = depleted, 1 = full |
| `risk_level` | 0.0–1.0 | 0 = safe, 1 = dangerous |
| `crew_size` | int | Number of crew members |
| `objective_count` | int | Number of objectives in the mission |
| `completed_ratio` | 0.0–1.0 | Fraction of objectives done |
| `failure_count` | int | How many objectives have failed |

### The scoring functions (exact weights from source)

Each function starts from a base score and adds weighted terms, capped at 1.0:

| Strategy | Base | Key weights | Thrives when… |
|----------|------|-------------|---------------|
| `full_parallel` | 0.1 | +0.3×resources, +0.2×(1−risk), +0.2 if crew≥3, +0.2 if time_pressure>0.6 | Big crew, low risk, ticking clock |
| `sequential_careful` | 0.3 | +0.3×risk, +0.2×(1−resources), +0.1×(1−completed), +0.2 if crew≤2 | Small crew, high risk, scarce resources |
| `delegate_all` | 0.2 | +0.3 if crew≥2, +0.2×resources, +0.15×(1−time_pressure), +0.15 if objectives≥3 | Specialized crew, no rush, complex mission |
| `adaptive_hybrid` | 0.4 | +min(objectives/10, 0.2), +0.2 if 0.3≤risk≤0.7, +0.2 if failures>0 | Complexity and some adversity (the safe default) |
| `conservative_hold` | 0.1 | +0.3×risk, +min(failures/3, 0.3), +0.2×(1−resources), +0.2 if early & failing | Things going badly |
| `aggressive_push` | 0.1 | +0.4×time_pressure, +0.2×resources, +0.1×(1−risk), +0.2 if completed>0.7 | Near the end with resources and a deadline |

### Design observations

- **`adaptive_hybrid` has the highest base score (0.4).** With no other
  signal, it wins by default. This makes it the engine's "I don't know, let's
  be flexible" fallback — confirmed by the test `test_recommend` which passes
  a default `TacticalContext()` (all zeros) and still gets a valid `Strategy`.
- **Scores are capped at 1.0 inside each function, then `priority_boost` is
  added *after* capping.** A custom strategy with `priority_boost=10.0` will
  always win (tested in `test_custom_strategy_with_boost`), but the displayed
  score may exceed 1.0. The test explicitly checks that the boosted strategy
  ranks first.
- **The agent's `analyze_tactics` hardcodes some context values.**
  `time_pressure=0.5` and `risk_level=0.3` are fixed constants in
  `CapitaineAgent.analyze_tactics`, not derived from mission state. Only
  `resource_availability`, `crew_size`, `objective_count`, `completed_ratio`,
  and `failure_count` are computed from real data. If you need different
  time-pressure or risk readings, construct a `TacticalContext` yourself and
  call `TacticsEngine.score_strategies` directly.

## 3. The delegation algorithm (`agent.py::delegate_objective`)

Delegation assigns an objective to the best-matching crew member. The matching
logic has a non-obvious design that's worth understanding before relying on it.

### Step by step (from source)

1. **Derive required capabilities** from the objective's `description` field:
   `required = obj.description.split()`. This splits on whitespace, so the
   description `"build scan"` becomes `["build", "scan"]`.
2. **Filter crew** via `CrewManager.best_for_task(required)`:
   - Start with all `AVAILABLE` members.
   - For each required capability word, keep only members who have that word
     in their `capabilities` list (case-sensitive, exact match).
   - From the survivors, return the one with the highest `performance_score`.
3. **Fallback**: if `best_for_task` returns `None` (no member has all the
   required capability words), fall back to *any* available member — the first
   one returned by `CrewManager.available()`.
4. If still no member, delegation fails (returns `None`).

### Implications

- **An empty description means no capability filtering.** The `best_for_task`
  loop runs zero iterations, so every available member is a candidate, and the
  highest-performance one wins. This is why the README examples (which use
  `description=""`) work even when crew capabilities don't match the task
  title.
- **Capabilities must match description words exactly.** If a crew member has
  capability `"recon"` and the objective description is `"reconnaissance"`,
  they won't match — `"recon" != "reconnaissance"`.
- **The fallback ignores capabilities entirely.** If no perfect match exists,
  *any* warm body gets the task. There's no "close enough" partial matching.
- **After assignment, the member's status becomes `BUSY`** (via
  `CrewManager.assign_task`), so they won't be picked again until their task
  is completed.
