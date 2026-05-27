"""CapitaineAgent — autonomous captain that leads and coordinates other agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from capitaine_agent.mission import Mission, Objective, MissionStatus, Priority, Constraint, SuccessCriterion
from capitaine_agent.crew import CrewManager, CrewMember, MemberRole, MemberStatus
from capitaine_agent.tactics import TacticsEngine, TacticalContext, Strategy
from capitaine_agent.debrief import DebriefReport, ObjectiveOutcome, Outcome


@dataclass
class AgentConfig:
    """Configuration for a CapitaineAgent instance."""
    name: str = "capitaine"
    vessel: str = "flagship"
    max_retries: int = 3
    verbose: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class CapitaineAgent:
    """Autonomous captain agent that leads and coordinates other agents.

    Responsibilities:
    - Set goals and create missions
    - Plan objective sequences with dependency resolution
    - Delegate work to crew members / sub-agents
    - Select tactical strategies based on context
    - Generate debrief reports on mission completion
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        self.config = config or AgentConfig()
        self.id: str = uuid4().hex[:12]
        self.crew = CrewManager()
        self.tactics = TacticsEngine()
        self.missions: dict[str, Mission] = {}
        self._active_mission: Mission | None = None
        self._log: list[dict[str, Any]] = []

    # ── Logging ──

    def _log_event(self, event: str, details: dict[str, Any] | None = None) -> None:
        entry = {"event": event, "details": details or {}}
        self._log.append(entry)
        if self.config.verbose:
            print(f"[capitaine] {event}: {details}")

    # ── Mission lifecycle ──

    def create_mission(
        self,
        name: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        constraints: list[Constraint] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Mission:
        """Create a new mission and register it."""
        mission = Mission(
            name=name,
            description=description,
            priority=priority,
            constraints=constraints or [],
            metadata=metadata or {},
        )
        self.missions[mission.id] = mission
        self._log_event("mission_created", {"mission_id": mission.id, "name": name})
        return mission

    def activate_mission(self, mission_id: str) -> bool:
        """Set a mission as the active mission."""
        mission = self.missions.get(mission_id)
        if not mission:
            return False
        mission.status = MissionStatus.ACTIVE
        self._active_mission = mission
        self._log_event("mission_activated", {"mission_id": mission_id})
        return True

    def get_active_mission(self) -> Mission | None:
        return self._active_mission

    # ── Goal setting & planning ──

    def add_goal(
        self,
        mission_id: str,
        title: str,
        description: str = "",
        assignee: str = "",
        priority: Priority = Priority.MEDIUM,
        success_criteria: list[SuccessCriterion] | None = None,
        dependencies: list[str] | None = None,
    ) -> Objective | None:
        """Add a goal/objective to a mission."""
        mission = self.missions.get(mission_id)
        if not mission:
            return None
        obj = Objective(
            title=title,
            description=description,
            assignee=assignee,
            priority=priority,
            success_criteria=success_criteria or [],
            dependencies=dependencies or [],
        )
        mission.add_objective(obj)
        self._log_event("goal_added", {"mission_id": mission_id, "objective_id": obj.id, "title": title})
        return obj

    def plan_mission(self, mission_id: str) -> list[list[Objective]]:
        """Plan execution order for a mission's objectives.

        Returns list of waves (batches that can run in parallel).
        Respects dependency ordering.
        """
        mission = self.missions.get(mission_id)
        if not mission:
            return []

        waves: list[list[Objective]] = []
        remaining = {o.id: o for o in mission.objectives}
        completed: set[str] = set()

        while remaining:
            # Find objectives whose deps are all completed (or already done)
            wave = [
                o for o in remaining.values()
                if all(d in completed for d in o.dependencies)
            ]
            if not wave:
                # Circular dependency — break it by taking first remaining
                wave = [next(iter(remaining.values()))]
            for o in wave:
                del remaining[o.id]
                completed.add(o.id)
            waves.append(wave)

        self._log_event("mission_planned", {"mission_id": mission_id, "waves": len(waves)})
        return waves

    # ── Delegation ──

    def delegate_objective(self, mission_id: str, objective_id: str) -> CrewMember | None:
        """Assign an objective to the best available crew member."""
        mission = self.missions.get(mission_id)
        if not mission:
            return None
        obj = mission.get_objective(objective_id)
        if not obj:
            return None

        # Determine required capabilities from objective metadata
        required = obj.description.split() if obj.description else []
        best = self.crew.best_for_task(required)
        if not best:
            # Try any available member
            available = self.crew.available()
            best = available[0] if available else None

        if best:
            obj.assignee = best.name
            self.crew.assign_task(objective_id, best.id)
            self._log_event("objective_delegated", {
                "objective_id": objective_id,
                "crew_member": best.name,
            })
        return best

    def delegate_all_ready(self, mission_id: str) -> list[tuple[Objective, CrewMember | None]]:
        """Delegate all ready (dependency-satisfied) objectives."""
        mission = self.missions.get(mission_id)
        if not mission:
            return []
        results = []
        for obj in mission.ready_objectives():
            member = self.delegate_objective(mission_id, obj.id)
            results.append((obj, member))
        return results

    # ── Tactics ──

    def analyze_tactics(self, mission_id: str) -> list[tuple[Strategy, float]]:
        """Analyze current tactical situation and score strategies."""
        mission = self.missions.get(mission_id)
        if not mission:
            return []

        ctx = TacticalContext(
            time_pressure=0.5,
            resource_availability=len(self.crew.available()) / max(len(self.crew.members), 1),
            risk_level=0.3,
            crew_size=len(self.crew.members),
            objective_count=len(mission.objectives),
            completed_ratio=mission.progress(),
            failure_count=sum(
                1 for o in mission.objectives if o.status == MissionStatus.FAILED
            ),
        )
        return self.tactics.score_strategies(ctx)

    def recommend_strategy(self, mission_id: str) -> Strategy | None:
        mission = self.missions.get(mission_id)
        if not mission:
            return None
        ctx = TacticalContext(
            time_pressure=0.5,
            resource_availability=len(self.crew.available()) / max(len(self.crew.members), 1),
            risk_level=0.3,
            crew_size=len(self.crew.members),
            objective_count=len(mission.objectives),
            completed_ratio=mission.progress(),
        )
        return self.tactics.recommend(ctx)

    # ── Debrief ──

    def debrief(self, mission_id: str) -> DebriefReport:
        """Generate a debrief report for a completed mission."""
        mission = self.missions.get(mission_id)
        if not mission:
            return DebriefReport(mission_id=mission_id)

        report = DebriefReport(
            mission_id=mission.id,
            mission_name=mission.name,
        )

        for obj in mission.objectives:
            if obj.is_complete():
                obj_outcome = Outcome.SUCCESS
            elif obj.status == MissionStatus.FAILED:
                obj_outcome = Outcome.FAILURE
            elif obj.status == MissionStatus.ABORTED:
                obj_outcome = Outcome.ABORTED
            else:
                obj_outcome = Outcome.INCONCLUSIVE

            report.add_objective_outcome(ObjectiveOutcome(
                objective_id=obj.id,
                objective_title=obj.title,
                outcome=obj_outcome,
            ))

        # Crew performance from roster
        for member in self.crew.members.values():
            report.set_crew_performance(member.name, member.performance_score)

        strategy = self.recommend_strategy(mission_id)
        if strategy:
            report.strategy_used = strategy.name

        report.mission_outcome = report.determine_outcome()
        self._log_event("mission_debriefed", {"mission_id": mission_id, "outcome": report.mission_outcome.value})
        return report

    # ── Utility ──

    def status(self) -> dict[str, Any]:
        return {
            "agent_id": self.id,
            "name": self.config.name,
            "vessel": self.config.vessel,
            "missions_total": len(self.missions),
            "crew_summary": self.crew.summary(),
            "active_mission": self._active_mission.summary() if self._active_mission else None,
            "log_entries": len(self._log),
        }
