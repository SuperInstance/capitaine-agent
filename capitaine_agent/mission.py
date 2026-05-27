"""Mission definition with objectives, constraints, and success criteria."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class MissionStatus(str, Enum):
    """Lifecycle states for a mission."""
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Constraint:
    """A restriction or boundary condition for the mission."""
    name: str
    description: str
    constraint_type: str = "general"  # time, resource, safety, regulatory, etc.
    strict: bool = False

    def evaluate(self, context: dict[str, Any]) -> tuple[bool, str]:
        """Check if constraint is satisfied in the given context.

        Returns (satisfied, message).
        Subclass or override for custom evaluation logic.
        """
        return True, f"Constraint '{self.name}' passed (default check)"


@dataclass
class SuccessCriterion:
    """Defines what success looks like for an objective or mission."""
    name: str
    description: str
    metric: str = ""
    target: Any = None
    comparator: str = "eq"  # eq, gt, lt, gte, lte, contains

    def is_met(self, value: Any) -> bool:
        """Evaluate whether the given value meets this criterion."""
        ops = {
            "eq": lambda a, b: a == b,
            "gt": lambda a, b: a > b,
            "lt": lambda a, b: a < b,
            "gte": lambda a, b: a >= b,
            "lte": lambda a, b: a <= b,
            "contains": lambda a, b: b in a if a else False,
        }
        op = ops.get(self.comparator, ops["eq"])
        try:
            return op(value, self.target)
        except (TypeError, ValueError):
            return False


@dataclass
class Objective:
    """A discrete goal within a mission."""
    id: str = field(default_factory=lambda: uuid4().hex[:8])
    title: str = ""
    description: str = ""
    assignee: str = ""  # crew member or sub-agent name
    priority: Priority = Priority.MEDIUM
    success_criteria: list[SuccessCriterion] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # objective IDs
    status: MissionStatus = MissionStatus.PLANNED
    result: Any = None

    def is_complete(self) -> bool:
        """Check if all success criteria are met against the stored result."""
        if not self.success_criteria:
            return self.status == MissionStatus.COMPLETED
        return all(c.is_met(self.result) for c in self.success_criteria)


@dataclass
class Mission:
    """A complete mission with objectives, constraints, and success criteria."""
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    name: str = ""
    description: str = ""
    objectives: list[Objective] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    success_criteria: list[SuccessCriterion] = field(default_factory=list)
    status: MissionStatus = MissionStatus.PLANNED
    priority: Priority = Priority.MEDIUM
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Objective management ──

    def add_objective(self, objective: Objective) -> None:
        self.objectives.append(objective)

    def remove_objective(self, objective_id: str) -> bool:
        before = len(self.objectives)
        self.objectives = [o for o in self.objectives if o.id != objective_id]
        return len(self.objectives) < before

    def get_objective(self, objective_id: str) -> Objective | None:
        for o in self.objectives:
            if o.id == objective_id:
                return o
        return None

    def ready_objectives(self) -> list[Objective]:
        """Objectives whose dependencies are all completed."""
        completed_ids = {o.id for o in self.objectives if o.status == MissionStatus.COMPLETED}
        return [
            o for o in self.objectives
            if o.status == MissionStatus.PLANNED
            and all(dep in completed_ids for dep in o.dependencies)
        ]

    # ── Constraint checking ──

    def check_constraints(self, context: dict[str, Any]) -> list[tuple[Constraint, bool, str]]:
        """Evaluate all constraints; returns list of (constraint, passed, message)."""
        return [(c, *c.evaluate(context)) for c in self.constraints]

    def all_constraints_met(self, context: dict[str, Any]) -> bool:
        return all(passed for _, passed, _ in self.check_constraints(context))

    # ── Progress ──

    def progress(self) -> float:
        """Fraction of objectives completed (0.0 to 1.0)."""
        if not self.objectives:
            return 0.0
        completed = sum(1 for o in self.objectives if o.status == MissionStatus.COMPLETED)
        return completed / len(self.objectives)

    def is_complete(self) -> bool:
        return all(o.status == MissionStatus.COMPLETED for o in self.objectives) and bool(self.objectives)

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "priority": self.priority.value,
            "objectives_total": len(self.objectives),
            "objectives_completed": sum(1 for o in self.objectives if o.status == MissionStatus.COMPLETED),
            "progress": round(self.progress(), 2),
            "constraints": len(self.constraints),
        }
