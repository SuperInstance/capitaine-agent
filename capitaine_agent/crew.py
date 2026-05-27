"""Crew management — registering and coordinating sub-agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4


class MemberRole(str, Enum):
    SCOUT = "scout"
    WORKER = "worker"
    SPECIALIST = "specialist"
    COORDINATOR = "coordinator"
    OBSERVER = "observer"


class MemberStatus(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class CrewMember:
    """A sub-agent or team member in the crew."""
    id: str = field(default_factory=lambda: uuid4().hex[:8])
    name: str = ""
    role: MemberRole = MemberRole.WORKER
    status: MemberStatus = MemberStatus.AVAILABLE
    capabilities: list[str] = field(default_factory=list)
    current_task: str | None = None
    performance_score: float = 1.0  # 0.0 to 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def can_perform(self, capability: str) -> bool:
        return capability in self.capabilities and self.status == MemberStatus.AVAILABLE

    def assign_task(self, task_id: str) -> None:
        self.current_task = task_id
        self.status = MemberStatus.BUSY

    def clear_task(self) -> None:
        self.current_task = None
        self.status = MemberStatus.AVAILABLE

    def mark_error(self) -> None:
        self.current_task = None
        self.status = MemberStatus.ERROR


class CrewManager:
    """Manages a roster of crew members / sub-agents."""

    def __init__(self) -> None:
        self.members: dict[str, CrewMember] = {}
        self._task_log: list[dict[str, Any]] = []

    # ── Registration ──

    def register(self, member: CrewMember) -> CrewMember:
        """Register a new crew member."""
        if member.name in [m.name for m in self.members.values()]:
            raise ValueError(f"Crew member '{member.name}' already registered")
        self.members[member.id] = member
        return member

    def unregister(self, member_id: str) -> bool:
        if member_id in self.members:
            del self.members[member_id]
            return True
        return False

    def get_member(self, member_id: str) -> CrewMember | None:
        return self.members.get(member_id)

    def get_member_by_name(self, name: str) -> CrewMember | None:
        for m in self.members.values():
            if m.name == name:
                return m
        return None

    # ── Queries ──

    def available(self) -> list[CrewMember]:
        return [m for m in self.members.values() if m.status == MemberStatus.AVAILABLE]

    def by_role(self, role: MemberRole) -> list[CrewMember]:
        return [m for m in self.members.values() if m.role == role]

    def by_capability(self, capability: str) -> list[CrewMember]:
        return [m for m in self.members.values() if capability in m.capabilities]

    # ── Task assignment ──

    def assign_task(self, task_id: str, member_id: str) -> bool:
        member = self.members.get(member_id)
        if not member or member.status != MemberStatus.AVAILABLE:
            return False
        member.assign_task(task_id)
        self._task_log.append({
            "task_id": task_id,
            "member_id": member_id,
            "action": "assigned",
        })
        return True

    def complete_task(self, member_id: str, success: bool = True) -> bool:
        member = self.members.get(member_id)
        if not member or member.status != MemberStatus.BUSY:
            return False
        task_id = member.current_task
        if success:
            member.clear_task()
            self._task_log.append({"task_id": task_id, "member_id": member_id, "action": "completed"})
        else:
            member.mark_error()
            self._task_log.append({"task_id": task_id, "member_id": member_id, "action": "failed"})
        return True

    def best_for_task(self, required_capabilities: list[str]) -> CrewMember | None:
        """Find the best available member for a task requiring given capabilities.

        Selection: available → has all capabilities → highest performance score.
        """
        candidates = self.available()
        for cap in required_capabilities:
            candidates = [m for m in candidates if cap in m.capabilities]
        if not candidates:
            return None
        return max(candidates, key=lambda m: m.performance_score)

    # ── Summary ──

    def roster(self) -> list[dict[str, Any]]:
        return [
            {
                "id": m.id,
                "name": m.name,
                "role": m.role.value,
                "status": m.status.value,
                "capabilities": m.capabilities,
                "performance": m.performance_score,
            }
            for m in self.members.values()
        ]

    def summary(self) -> dict[str, Any]:
        members = list(self.members.values())
        return {
            "total_members": len(members),
            "available": sum(1 for m in members if m.status == MemberStatus.AVAILABLE),
            "busy": sum(1 for m in members if m.status == MemberStatus.BUSY),
            "offline": sum(1 for m in members if m.status == MemberStatus.OFFLINE),
            "error": sum(1 for m in members if m.status == MemberStatus.ERROR),
            "tasks_assigned": len(self._task_log),
        }
