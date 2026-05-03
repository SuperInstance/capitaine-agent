"""CLI entry point for capitaine-agent."""
import argparse
import json
import sys
from datetime import datetime, timezone

from capitaine_agent import CapitaineAgent


def interactive_voyage(agent: CapitaineAgent) -> None:
    print("=== Capitaine Agent — Voyage Logger ===")
    print()

    departure = input("Departure port: ").strip()
    destination = input("Destination port: ").strip()
    crew_raw = input("Crew names (comma-separated): ").strip()
    crew_names = [c.strip() for c in crew_raw.split(",") if c.strip()]

    catch_summary = input("Catch summary: ").strip()
    weather_conditions = input("Weather conditions: ").strip()
    incidents = input("Incidents (if any): ").strip()
    notes = input("Additional notes: ").strip()

    print()
    result = agent.log_voyage(
        departure, destination, crew_names, catch_summary,
        weather_conditions, incidents, notes
    )
    print(f"Voyage logged. Tile: {result.get('tile_hash', '?')}")


def interactive_crew_event(agent: CapitaineAgent) -> None:
    print("=== Capitaine Agent — Crew Event ===")
    print()

    crew_name = input("Crew member name: ").strip()
    event_type = input("Event type (injury/achievement/issue/other): ").strip()
    description = input("Description: ").strip()
    severity = input("Severity (low/medium/high): ").strip() or "low"

    print()
    result = agent.log_crew_event(crew_name, event_type, description, severity)
    print(f"Event logged. Tile: {result.get('tile_hash', '?')}")


def handle_qa(agent: CapitaineAgent, question: str) -> None:
    result = agent.ask_maritime_question(question)
    print(json.dumps(result, indent=2, default=str))


def handle_status(agent: CapitaineAgent) -> None:
    status = agent.get_status()
    print(json.dumps(status, indent=2, default=str))


def handle_voyage_history(agent: CapitaineAgent) -> None:
    voyages = agent.get_voyage_history()
    for i, v in enumerate(voyages):
        print(f"[{i+1}] {v.get('question', 'unknown')}")
        print(f"    Answer: {v.get('answer', '')[:200]}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitaine AI First Mate")
    parser.add_argument("--captain", default="default", help="Captain ID")
    parser.add_argument("--vessel", default="unknown", help="Vessel name")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--voyage", action="store_true", help="Log a new voyage")
    parser.add_argument("--crew", action="store_true", help="Log a crew event")
    parser.add_argument("--qa", type=str, help="Ask a maritime question")
    parser.add_argument("--status", action="store_true", help="Show vessel status")
    parser.add_argument("--history", action="store_true", help="Show voyage history")
    args = parser.parse_args()

    agent = CapitaineAgent(captain_id=args.captain, vessel=args.vessel, verbose=args.verbose)

    if args.voyage:
        interactive_voyage(agent)
    elif args.crew:
        interactive_crew_event(agent)
    elif args.qa:
        handle_qa(agent, args.qa)
    elif args.status:
        handle_status(agent)
    elif args.history:
        handle_voyage_history(agent)
    else:
        # Default: interactive menu
        print("Capitaine Agent — AI First Mate")
        print("Use --voyage, --crew, --qa, --status, or --history")
        print("Run with --help for all options")


if __name__ == "__main__":
    main()