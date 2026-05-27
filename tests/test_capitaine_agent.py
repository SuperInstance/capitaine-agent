"""Comprehensive tests for capitaine_agent."""

import pytest
from datetime import datetime

from capitaine_agent.agent import CapitaineAgent, AgentConfig
from capitaine_agent.mission import (
    Mission, Objective, Constraint, SuccessCriterion,
    MissionStatus, Priority,
)
from capitaine_agent.crew import CrewManager, CrewMember, MemberRole, MemberStatus
from capitaine_agent.tactics import TacticsEngine, TacticalContext, Strategy, StrategyType
from capitaine_agent.debrief import DebriefReport, ObjectiveOutcome, Outcome


# ════════════════════════════════════════════
# Mission tests
# ════════════════════════════════════════════

class TestSuccessCriterion:
    def test_eq(self):
        c = SuccessCriterion(name="count", description="", metric="items", target=5, comparator="eq")
        assert c.is_met(5) is True
        assert c.is_met(4) is False

    def test_gt(self):
        c = SuccessCriterion(name="score", description="", target=80, comparator="gt")
        assert c.is_met(81) is True
        assert c.is_met(80) is False

    def test_lt(self):
        c = SuccessCriterion(name="errors", description="", target=3, comparator="lt")
        assert c.is_met(2) is True
        assert c.is_met(3) is False

    def test_gte(self):
        c = SuccessCriterion(name="min", description="", target=10, comparator="gte")
        assert c.is_met(10) is True
        assert c.is_met(9) is False

    def test_lte(self):
        c = SuccessCriterion(name="max", description="", target=100, comparator="lte")
        assert c.is_met(100) is True
        assert c.is_met(101) is False

    def test_contains(self):
        c = SuccessCriterion(name="has", description="", target="ok", comparator="contains")
        assert c.is_met("everything is ok") is True
        assert c.is_met("nope") is False
        assert c.is_met(None) is False

    def test_bad_comparator(self):
        c = SuccessCriterion(name="x", description="", target=1, comparator="unknown")
        assert c.is_met(1) is True  # falls back to eq

    def test_type_error(self):
        c = SuccessCriterion(name="x", description="", target="string", comparator="gt")
        assert c.is_met(42) is False


class TestConstraint:
    def test_default_evaluate(self):
        c = Constraint(name="budget", description="Stay under budget")
        passed, msg = c.evaluate({})
        assert passed is True
        assert "budget" in msg

    def test_strict_flag(self):
        c = Constraint(name="safety", description="No injuries", strict=True)
        assert c.strict is True


class TestObjective:
    def test_default_status(self):
        o = Objective(title="Test")
        assert o.status == MissionStatus.PLANNED

    def test_is_complete_with_criteria(self):
        c = SuccessCriterion(name="done", description="", target=True, comparator="eq")
        o = Objective(title="T", success_criteria=[c], result=True, status=MissionStatus.COMPLETED)
        assert o.is_complete() is True

    def test_is_complete_no_criteria(self):
        o = Objective(title="T", status=MissionStatus.COMPLETED)
        assert o.is_complete() is True
        o.status = MissionStatus.PLANNED
        assert o.is_complete() is False


class TestMission:
    def test_create_mission(self):
        m = Mission(name="Op Alpha")
        assert m.name == "Op Alpha"
        assert m.status == MissionStatus.PLANNED
        assert m.objectives == []

    def test_add_remove_objective(self):
        m = Mission(name="Test")
        o = Objective(title="Do thing")
        m.add_objective(o)
        assert len(m.objectives) == 1
        assert m.remove_objective(o.id) is True
        assert len(m.objectives) == 0
        assert m.remove_objective("nonexistent") is False

    def test_get_objective(self):
        m = Mission(name="Test")
        o = Objective(title="Find me")
        m.add_objective(o)
        assert m.get_objective(o.id) is o
        assert m.get_objective("nope") is None

    def test_ready_objectives_no_deps(self):
        m = Mission(name="Test")
        o1 = Objective(title="A")
        o2 = Objective(title="B")
        m.add_objective(o1)
        m.add_objective(o2)
        ready = m.ready_objectives()
        assert len(ready) == 2

    def test_ready_objectives_with_deps(self):
        m = Mission(name="Test")
        o1 = Objective(title="A")
        o2 = Objective(title="B", dependencies=[o1.id])
        o3 = Objective(title="C", dependencies=[o1.id, o2.id])
        m.add_objective(o1)
        m.add_objective(o2)
        m.add_objective(o3)

        # Only o1 is ready
        ready = m.ready_objectives()
        assert len(ready) == 1
        assert ready[0].id == o1.id

        # Complete o1
        o1.status = MissionStatus.COMPLETED
        ready = m.ready_objectives()
        assert len(ready) == 1
        assert ready[0].id == o2.id

    def test_progress(self):
        m = Mission(name="Test")
        assert m.progress() == 0.0
        o1 = Objective(title="A")
        o2 = Objective(title="B")
        m.add_objective(o1)
        m.add_objective(o2)
        assert m.progress() == 0.0
        o1.status = MissionStatus.COMPLETED
        assert m.progress() == 0.5
        o2.status = MissionStatus.COMPLETED
        assert m.progress() == 1.0

    def test_is_complete(self):
        m = Mission(name="Test")
        assert m.is_complete() is False
        o1 = Objective(title="A")
        m.add_objective(o1)
        assert m.is_complete() is False
        o1.status = MissionStatus.COMPLETED
        assert m.is_complete() is True

    def test_constraints(self):
        c = Constraint(name="time", description="Under 1 hour")
        m = Mission(name="Test", constraints=[c])
        results = m.check_constraints({})
        assert len(results) == 1
        assert m.all_constraints_met({}) is True

    def test_summary(self):
        m = Mission(name="Op Alpha", priority=Priority.HIGH)
        m.add_objective(Objective(title="A"))
        s = m.summary()
        assert s["name"] == "Op Alpha"
        assert s["priority"] == "high"
        assert s["objectives_total"] == 1


# ════════════════════════════════════════════
# Crew tests
# ════════════════════════════════════════════

class TestCrewMember:
    def test_can_perform(self):
        m = CrewMember(name="Rex", capabilities=["fight", "scout"])
        assert m.can_perform("fight") is True
        assert m.can_perform("cook") is False

    def test_can_perform_busy(self):
        m = CrewMember(name="Rex", capabilities=["fight"])
        m.assign_task("t1")
        assert m.can_perform("fight") is False

    def test_assign_and_clear(self):
        m = CrewMember(name="Rex")
        m.assign_task("t1")
        assert m.status == MemberStatus.BUSY
        assert m.current_task == "t1"
        m.clear_task()
        assert m.status == MemberStatus.AVAILABLE
        assert m.current_task is None

    def test_mark_error(self):
        m = CrewMember(name="Rex")
        m.assign_task("t1")
        m.mark_error()
        assert m.status == MemberStatus.ERROR
        assert m.current_task is None


class TestCrewManager:
    def test_register(self):
        cm = CrewManager()
        m = CrewMember(name="Alice", role=MemberRole.SPECIALIST)
        cm.register(m)
        assert cm.get_member(m.id) is m

    def test_register_duplicate_name(self):
        cm = CrewManager()
        cm.register(CrewMember(name="Alice"))
        with pytest.raises(ValueError):
            cm.register(CrewMember(name="Alice"))

    def test_unregister(self):
        cm = CrewManager()
        m = CrewMember(name="Bob")
        cm.register(m)
        assert cm.unregister(m.id) is True
        assert cm.unregister("nonexistent") is False

    def test_get_by_name(self):
        cm = CrewManager()
        m = CrewMember(name="Carol")
        cm.register(m)
        assert cm.get_member_by_name("Carol") is m
        assert cm.get_member_by_name("Nobody") is None

    def test_available(self):
        cm = CrewManager()
        m1 = CrewMember(name="A")
        m2 = CrewMember(name="B")
        m2.assign_task("t1")
        cm.register(m1)
        cm.register(m2)
        avail = cm.available()
        assert len(avail) == 1
        assert avail[0].name == "A"

    def test_by_role(self):
        cm = CrewManager()
        cm.register(CrewMember(name="S", role=MemberRole.SCOUT))
        cm.register(CrewMember(name="W", role=MemberRole.WORKER))
        scouts = cm.by_role(MemberRole.SCOUT)
        assert len(scouts) == 1

    def test_by_capability(self):
        cm = CrewManager()
        cm.register(CrewMember(name="A", capabilities=["nav", "fight"]))
        cm.register(CrewMember(name="B", capabilities=["cook"]))
        navs = cm.by_capability("nav")
        assert len(navs) == 1

    def test_assign_task(self):
        cm = CrewManager()
        m = CrewMember(name="A")
        cm.register(m)
        assert cm.assign_task("task-1", m.id) is True
        assert m.status == MemberStatus.BUSY
        # Can't assign again
        assert cm.assign_task("task-2", m.id) is False
        # Unknown member
        assert cm.assign_task("task-1", "nobody") is False

    def test_complete_task(self):
        cm = CrewManager()
        m = CrewMember(name="A")
        cm.register(m)
        cm.assign_task("t1", m.id)
        assert cm.complete_task(m.id, success=True) is True
        assert m.status == MemberStatus.AVAILABLE
        # Can't complete non-busy member
        assert cm.complete_task(m.id) is False

    def test_complete_task_failure(self):
        cm = CrewManager()
        m = CrewMember(name="A")
        cm.register(m)
        cm.assign_task("t1", m.id)
        cm.complete_task(m.id, success=False)
        assert m.status == MemberStatus.ERROR

    def test_best_for_task(self):
        cm = CrewManager()
        m1 = CrewMember(name="Rookie", capabilities=["fight"], performance_score=0.5)
        m2 = CrewMember(name="Vet", capabilities=["fight", "lead"], performance_score=0.9)
        cm.register(m1)
        cm.register(m2)
        best = cm.best_for_task(["fight"])
        assert best is m2  # higher performance

    def test_best_for_task_none_available(self):
        cm = CrewManager()
        m = CrewMember(name="A", capabilities=["fight"])
        m.assign_task("t1")
        cm.register(m)
        assert cm.best_for_task(["fight"]) is None

    def test_best_for_task_no_capability_match(self):
        cm = CrewManager()
        cm.register(CrewMember(name="A", capabilities=["cook"]))
        assert cm.best_for_task(["fight"]) is None

    def test_roster_and_summary(self):
        cm = CrewManager()
        cm.register(CrewMember(name="A", role=MemberRole.SCOUT))
        cm.register(CrewMember(name="B", role=MemberRole.WORKER))
        assert len(cm.roster()) == 2
        s = cm.summary()
        assert s["total_members"] == 2
        assert s["available"] == 2


# ════════════════════════════════════════════
# Tactics tests
# ════════════════════════════════════════════

class TestTacticsEngine:
    def test_builtin_strategies(self):
        te = TacticsEngine()
        assert len(te.strategies) >= 6

    def test_register_custom_strategy(self):
        te = TacticsEngine()
        s = Strategy("custom", StrategyType.SEQUENTIAL, "My strategy")
        te.register_strategy(s)
        assert te.get_strategy("custom") is s

    def test_remove_strategy(self):
        te = TacticsEngine()
        assert te.remove_strategy("full_parallel") is True
        assert te.remove_strategy("nonexistent") is False

    def test_score_strategies_returns_sorted(self):
        te = TacticsEngine()
        ctx = TacticalContext(crew_size=5, resource_availability=0.9, risk_level=0.1, time_pressure=0.8)
        scored = te.score_strategies(ctx)
        assert len(scored) == len(te.strategies)
        # Check sorted descending
        for i in range(len(scored) - 1):
            assert scored[i][1] >= scored[i + 1][1]

    def test_parallel_favored_with_resources(self):
        te = TacticsEngine()
        ctx = TacticalContext(
            crew_size=5, resource_availability=1.0, risk_level=0.1,
            time_pressure=0.8, objective_count=4
        )
        scored = te.score_strategies(ctx)
        top_name = scored[0][0].name
        assert top_name in ("full_parallel", "aggressive_push")

    def test_conservative_favored_on_failure(self):
        te = TacticsEngine()
        ctx = TacticalContext(
            risk_level=0.9, failure_count=3, resource_availability=0.2,
            completed_ratio=0.1
        )
        scored = te.score_strategies(ctx)
        top_name = scored[0][0].name
        assert top_name in ("conservative_hold", "sequential_careful")

    def test_recommend(self):
        te = TacticsEngine()
        ctx = TacticalContext()
        s = te.recommend(ctx)
        assert isinstance(s, Strategy)

    def test_recommend_with_score(self):
        te = TacticsEngine()
        ctx = TacticalContext()
        s, score = te.recommend_with_score(ctx)
        assert isinstance(s, Strategy)
        assert 0.0 <= score <= 1.0

    def test_scores_bounded(self):
        te = TacticsEngine()
        ctx = TacticalContext(
            time_pressure=1.0, resource_availability=1.0,
            risk_level=1.0, crew_size=10, objective_count=20,
            failure_count=10, completed_ratio=0.5
        )
        for _, score in te.score_strategies(ctx):
            assert 0.0 <= score <= 1.0

    def test_custom_strategy_with_boost(self):
        te = TacticsEngine()
        s = Strategy("boosted", StrategyType.ADAPTIVE, "Always wins",
                     suitability_fn="adaptive_default", priority_boost=10.0)
        te.register_strategy(s)
        ctx = TacticalContext()
        scored = te.score_strategies(ctx)
        # boosted may exceed 1.0 due to boost, but original scores are capped
        assert scored[0][0].name == "boosted"


# ════════════════════════════════════════════
# Debrief tests
# ════════════════════════════════════════════

class TestDebriefReport:
    def test_empty_report(self):
        r = DebriefReport(mission_id="m1", mission_name="Test")
        assert r.success_rate() == 0.0
        assert r.overall_score() >= 0.0
        assert r.determine_outcome() == Outcome.INCONCLUSIVE

    def test_all_success(self):
        r = DebriefReport(mission_id="m1")
        r.add_objective_outcome(ObjectiveOutcome("o1", "Task A", Outcome.SUCCESS))
        r.add_objective_outcome(ObjectiveOutcome("o2", "Task B", Outcome.SUCCESS))
        assert r.success_rate() == 1.0
        assert r.determine_outcome() == Outcome.SUCCESS

    def test_mixed_results(self):
        r = DebriefReport(mission_id="m1")
        r.add_objective_outcome(ObjectiveOutcome("o1", "A", Outcome.SUCCESS))
        r.add_objective_outcome(ObjectiveOutcome("o2", "B", Outcome.FAILURE))
        assert r.success_rate() == 0.5
        assert r.determine_outcome() == Outcome.PARTIAL_SUCCESS

    def test_all_failure(self):
        r = DebriefReport(mission_id="m1")
        r.add_objective_outcome(ObjectiveOutcome("o1", "A", Outcome.FAILURE))
        assert r.determine_outcome() == Outcome.FAILURE

    def test_crew_performance(self):
        r = DebriefReport(mission_id="m1")
        r.set_crew_performance("Alice", 0.9)
        r.set_crew_performance("Bob", 0.5)
        assert r.crew_performance["Alice"] == 0.9
        # Clamped
        r.set_crew_performance("Charlie", 2.0)
        assert r.crew_performance["Charlie"] == 1.0

    def test_overall_score(self):
        r = DebriefReport(mission_id="m1")
        r.add_objective_outcome(ObjectiveOutcome("o1", "A", Outcome.SUCCESS))
        r.set_crew_performance("Alice", 1.0)
        score = r.overall_score()
        assert 0.0 <= score <= 1.0

    def test_lessons(self):
        r = DebriefReport(mission_id="m1")
        r.add_lesson("Always check weather first")
        r.add_lesson("Bring backup comms")
        assert len(r.lessons_learned) == 2

    def test_summary(self):
        r = DebriefReport(mission_id="m1", mission_name="Op Alpha", strategy_used="full_parallel")
        r.add_objective_outcome(ObjectiveOutcome("o1", "A", Outcome.SUCCESS))
        s = r.summary()
        assert s["mission_name"] == "Op Alpha"
        assert s["strategy_used"] == "full_parallel"
        assert s["outcome"] == "success"

    def test_full_report(self):
        r = DebriefReport(mission_id="m1")
        r.add_objective_outcome(ObjectiveOutcome("o1", "A", Outcome.SUCCESS))
        r.add_lesson("Plan better")
        report = r.full_report()
        assert "objective_outcomes" in report
        assert "lessons_learned" in report
        assert "crew_performance" in report


# ════════════════════════════════════════════
# CapitaineAgent integration tests
# ════════════════════════════════════════════

class TestCapitaineAgent:
    @pytest.fixture
    def agent(self):
        config = AgentConfig(name="TestCaptain", vessel="TestShip", verbose=False)
        return CapitaineAgent(config)

    def test_create_agent(self, agent):
        assert agent.config.name == "TestCaptain"
        assert agent.config.vessel == "TestShip"
        assert len(agent.crew.members) == 0

    def test_create_mission(self, agent):
        m = agent.create_mission("Op Alpha", "First mission", Priority.HIGH)
        assert m.name == "Op Alpha"
        assert m.priority == Priority.HIGH
        assert m.id in agent.missions

    def test_activate_mission(self, agent):
        m = agent.create_mission("Test")
        assert agent.activate_mission(m.id) is True
        assert agent.get_active_mission() is m
        assert m.status == MissionStatus.ACTIVE
        assert agent.activate_mission("nonexistent") is False

    def test_add_goal(self, agent):
        m = agent.create_mission("Test")
        obj = agent.add_goal(m.id, "Secure perimeter")
        assert obj is not None
        assert obj.title == "Secure perimeter"
        assert len(m.objectives) == 1

    def test_add_goal_nonexistent_mission(self, agent):
        assert agent.add_goal("nonexistent", "Goal") is None

    def test_plan_mission(self, agent):
        m = agent.create_mission("Test")
        o1 = agent.add_goal(m.id, "Step 1")
        o2 = agent.add_goal(m.id, "Step 2", dependencies=[o1.id])
        o3 = agent.add_goal(m.id, "Step 3", dependencies=[o1.id])
        waves = agent.plan_mission(m.id)
        assert len(waves) == 2
        assert len(waves[0]) == 1  # o1 first
        assert o1.id in [o.id for o in waves[0]]
        assert len(waves[1]) == 2  # o2 and o3 parallel

    def test_plan_nonexistent_mission(self, agent):
        assert agent.plan_mission("nonexistent") == []

    def test_delegate_objective(self, agent):
        from capitaine_agent.crew import CrewMember, MemberRole
        agent.crew.register(CrewMember(
            name="Worker-1", role=MemberRole.WORKER,
            capabilities=["execution"], performance_score=0.8
        ))
        m = agent.create_mission("Test")
        obj = agent.add_goal(m.id, "Do the thing")
        member = agent.delegate_objective(m.id, obj.id)
        assert member is not None
        assert member.name == "Worker-1"
        assert obj.assignee == "Worker-1"

    def test_delegate_no_crew(self, agent):
        m = agent.create_mission("Test")
        obj = agent.add_goal(m.id, "Do the thing")
        member = agent.delegate_objective(m.id, obj.id)
        assert member is None

    def test_delegate_all_ready(self, agent):
        from capitaine_agent.crew import CrewMember, MemberRole
        agent.crew.register(CrewMember(name="W1", role=MemberRole.WORKER, capabilities=["a"]))
        agent.crew.register(CrewMember(name="W2", role=MemberRole.WORKER, capabilities=["b"]))
        m = agent.create_mission("Test")
        o1 = agent.add_goal(m.id, "Task A")
        o2 = agent.add_goal(m.id, "Task B")
        results = agent.delegate_all_ready(m.id)
        assert len(results) == 2

    def test_debrief(self, agent):
        m = agent.create_mission("Test")
        o1 = agent.add_goal(m.id, "Task A")
        o2 = agent.add_goal(m.id, "Task B")
        o1.status = MissionStatus.COMPLETED
        o2.status = MissionStatus.FAILED
        report = agent.debrief(m.id)
        assert report.mission_outcome == Outcome.PARTIAL_SUCCESS
        assert len(report.objective_outcomes) == 2

    def test_debrief_nonexistent(self, agent):
        report = agent.debrief("nonexistent")
        assert report.mission_id == "nonexistent"

    def test_analyze_tactics(self, agent):
        from capitaine_agent.crew import CrewMember, MemberRole
        agent.crew.register(CrewMember(name="W1", role=MemberRole.WORKER))
        m = agent.create_mission("Test")
        agent.add_goal(m.id, "A")
        scored = agent.analyze_tactics(m.id)
        assert len(scored) > 0
        # Check sorted
        for i in range(len(scored) - 1):
            assert scored[i][1] >= scored[i + 1][1]

    def test_recommend_strategy(self, agent):
        from capitaine_agent.crew import CrewMember, MemberRole
        agent.crew.register(CrewMember(name="W1", role=MemberRole.WORKER))
        m = agent.create_mission("Test")
        s = agent.recommend_strategy(m.id)
        assert s is not None
        assert isinstance(s, Strategy)

    def test_status(self, agent):
        s = agent.status()
        assert s["name"] == "TestCaptain"
        assert s["vessel"] == "TestShip"
        assert s["missions_total"] == 0

    def test_full_workflow(self, agent):
        """End-to-end: create mission → add goals → add crew → plan → delegate → debrief."""
        from capitaine_agent.crew import CrewMember, MemberRole

        # Register crew
        agent.crew.register(CrewMember(
            name="Scout-1", role=MemberRole.SCOUT,
            capabilities=["recon", "scan"], performance_score=0.85
        ))
        agent.crew.register(CrewMember(
            name="Worker-1", role=MemberRole.WORKER,
            capabilities=["build", "repair"], performance_score=0.9
        ))

        # Create and activate mission
        m = agent.create_mission("Deep Ops", "Complex operation", Priority.CRITICAL)
        agent.activate_mission(m.id)

        # Add goals with dependencies
        recon = agent.add_goal(m.id, "Recon area", assignee="Scout-1")
        build = agent.add_goal(m.id, "Build base", dependencies=[recon.id])
        repair = agent.add_goal(m.id, "Repair comms", dependencies=[recon.id])

        # Plan
        waves = agent.plan_mission(m.id)
        assert len(waves) == 2

        # Analyze tactics
        scored = agent.analyze_tactics(m.id)
        assert len(scored) > 0

        # Complete objectives
        recon.status = MissionStatus.COMPLETED
        build.status = MissionStatus.COMPLETED
        repair.status = MissionStatus.FAILED

        # Debrief
        report = agent.debrief(m.id)
        assert report.mission_outcome == Outcome.PARTIAL_SUCCESS
        assert report.success_rate() == pytest.approx(2/3, abs=0.01)

        # Check full report
        full = report.full_report()
        assert full["outcome"] == "partial_success"
        assert len(full["objective_outcomes"]) == 3

    def test_verbose_logging(self):
        config = AgentConfig(name="V", verbose=True, max_retries=5)
        agent = CapitaineAgent(config)
        m = agent.create_mission("Verbose Test")
        assert len(agent._log) >= 1
        entry = agent._log[0]
        assert entry["event"] == "mission_created"
