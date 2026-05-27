"""Debrief report — summarizing mission outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from datetime import datetime, timezone


class Outcome(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ABORTED = "aborted"
    INCONCLUSIVE = "inconclusive"


@dataclass
class ObjectiveOutcome:
    """Result of a single objective."""
    objective_id: str
    objective_title: str
    outcome: Outcome
    notes: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class DebriefReport:
    """Comprehensive debrief summarizing mission outcomes."""
    mission_id: str = ""
    mission_name: str = ""
    mission_outcome: Outcome = Outcome.INCONCLUSIVE
    objective_outcomes: list[ObjectiveOutcome] = field(default_factory=list)
    lessons_learned: list[str] = field(default_factory=list)
    crew_performance: dict[str, float] = field(default_factory=dict)  # name -> score
    strategy_used: str = ""
    strategy_effective: bool = False
    duration_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Building ──

    def add_objective_outcome(self, outcome: ObjectiveOutcome) -> None:
        self.objective_outcomes.append(outcome)

    def add_lesson(self, lesson: str) -> None:
        self.lessons_learned.append(lesson)

    def set_crew_performance(self, name: str, score: float) -> None:
        self.crew_performance[name] = round(max(0.0, min(1.0, score)), 2)

    # ── Computed ──

    def success_rate(self) -> float:
        """Fraction of objectives that succeeded."""
        if not self.objective_outcomes:
            return 0.0
        successes = sum(
            1 for o in self.objective_outcomes
            if o.outcome in (Outcome.SUCCESS, Outcome.PARTIAL_SUCCESS)
        )
        return round(successes / len(self.objective_outcomes), 2)

    def overall_score(self) -> float:
        """Weighted score combining success rate and crew performance."""
        sr = self.success_rate()
        avg_crew = (
            sum(self.crew_performance.values()) / len(self.crew_performance)
            if self.crew_performance
            else 0.5
        )
        return round(0.7 * sr + 0.3 * avg_crew, 2)

    def determine_outcome(self) -> Outcome:
        """Auto-determine mission outcome from objective results."""
        if not self.objective_outcomes:
            return Outcome.INCONCLUSIVE
        total = len(self.objective_outcomes)
        successes = sum(1 for o in self.objective_outcomes if o.outcome == Outcome.SUCCESS)
        failures = sum(1 for o in self.objective_outcomes if o.outcome == Outcome.FAILURE)

        if successes == total:
            return Outcome.SUCCESS
        if failures == total:
            return Outcome.FAILURE
        if successes > 0 and failures > 0:
            return Outcome.PARTIAL_SUCCESS
        if successes > 0:
            return Outcome.SUCCESS
        return Outcome.FAILURE

    # ── Output ──

    def summary(self) -> dict[str, Any]:
        if self.mission_outcome == Outcome.INCONCLUSIVE:
            self.mission_outcome = self.determine_outcome()
        return {
            "mission_id": self.mission_id,
            "mission_name": self.mission_name,
            "outcome": self.mission_outcome.value,
            "success_rate": self.success_rate(),
            "overall_score": self.overall_score(),
            "objectives_total": len(self.objective_outcomes),
            "objectives_succeeded": sum(
                1 for o in self.objective_outcomes if o.outcome == Outcome.SUCCESS
            ),
            "strategy_used": self.strategy_used,
            "strategy_effective": self.strategy_effective,
            "lessons_count": len(self.lessons_learned),
            "crew_count": len(self.crew_performance),
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp,
        }

    def full_report(self) -> dict[str, Any]:
        base = self.summary()
        base["objective_outcomes"] = [
            {
                "id": o.objective_id,
                "title": o.objective_title,
                "outcome": o.outcome.value,
                "notes": o.notes,
                "metrics": o.metrics,
            }
            for o in self.objective_outcomes
        ]
        base["lessons_learned"] = self.lessons_learned
        base["crew_performance"] = self.crew_performance
        base["metadata"] = self.metadata
        return base
