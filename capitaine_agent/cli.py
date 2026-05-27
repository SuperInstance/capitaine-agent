"""CLI entry point for capitaine-agent."""

import argparse
import json
import sys

from capitaine_agent.agent import CapitaineAgent, AgentConfig
from capitaine_agent.mission import Priority


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitaine Agent — autonomous captain for multi-agent coordination")
    parser.add_argument("--name", default="capitaine", help="Agent name")
    parser.add_argument("--vessel", default="flagship", help="Vessel name")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show agent status")

    create_p = sub.add_parser("create-mission", help="Create a new mission")
    create_p.add_argument("mission_name", help="Mission name")
    create_p.add_argument("--description", default="", help="Mission description")
    create_p.add_argument("--priority", choices=["low", "medium", "high", "critical"], default="medium")

    plan_p = sub.add_parser("plan", help="Plan a mission execution order")
    plan_p.add_argument("mission_id", help="Mission ID")

    sub.add_parser("missions", help="List all missions")

    crew_p = sub.add_parser("add-crew", help="Register a crew member")
    crew_p.add_argument("name", help="Crew member name")
    crew_p.add_argument("--role", default="worker", help="Role (scout/worker/specialist/coordinator/observer)")
    crew_p.add_argument("--capabilities", nargs="*", default=[], help="Capabilities")

    debrief_p = sub.add_parser("debrief", help="Generate debrief report")
    debrief_p.add_argument("mission_id", help="Mission ID")

    args = parser.parse_args()

    config = AgentConfig(name=args.name, vessel=args.vessel, verbose=args.verbose)
    agent = CapitaineAgent(config)

    # For demo: auto-register some crew so status is interesting
    from capitaine_agent.crew import CrewMember, MemberRole
    agent.crew.register(CrewMember(name="Scout-1", role=MemberRole.SCOUT, capabilities=["recon", "navigation"]))
    agent.crew.register(CrewMember(name="Worker-1", role=MemberRole.WORKER, capabilities=["execution", "processing"]))

    if args.command == "status":
        print(json.dumps(agent.status(), indent=2))
    elif args.command == "create-mission":
        prio = Priority(args.priority)
        m = agent.create_mission(args.mission_name, args.description, prio)
        print(json.dumps(m.summary(), indent=2))
    elif args.command == "missions":
        for m in agent.missions.values():
            print(f"  [{m.status.value}] {m.name} ({m.id}) — {m.progress():.0%}")
    elif args.command == "plan":
        waves = agent.plan_mission(args.mission_id)
        for i, wave in enumerate(waves, 1):
            titles = [o.title for o in wave]
            print(f"  Wave {i}: {titles}")
    elif args.command == "add-crew":
        from capitaine_agent.crew import MemberRole
        role = MemberRole(args.role)
        member = CrewMember(name=args.name, role=role, capabilities=args.capabilities)
        agent.crew.register(member)
        print(f"Registered: {member.name} ({member.role.value})")
    elif args.command == "debrief":
        report = agent.debrief(args.mission_id)
        print(json.dumps(report.summary(), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
