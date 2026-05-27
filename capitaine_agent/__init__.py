"""
capitaine_agent — Autonomous captain agent that leads and coordinates other agents.

Provides mission planning, crew coordination, tactical decision-making,
and debrief reporting for multi-agent operations.
"""

from capitaine_agent.agent import CapitaineAgent
from capitaine_agent.mission import Mission, Objective, Constraint, SuccessCriterion
from capitaine_agent.crew import CrewManager, CrewMember
from capitaine_agent.tactics import TacticsEngine, Strategy
from capitaine_agent.debrief import DebriefReport, Outcome

__version__ = "0.2.0"
__all__ = [
    "CapitaineAgent",
    "Mission",
    "Objective",
    "Constraint",
    "SuccessCriterion",
    "CrewManager",
    "CrewMember",
    "TacticsEngine",
    "Strategy",
    "DebriefReport",
    "Outcome",
]
