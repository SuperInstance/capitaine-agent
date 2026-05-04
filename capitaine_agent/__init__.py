"""
capitaine_agent — Captain's AI First Mate for captaine.ai

Provides voyage logging, crew coordination, and maritime Q&A via PLATO.
Integrates with the PLATO tile system to track voyages and crew interactions.

Usage:
    python -m capitaine_agent              # Interactive first mate session
    python -m capitaine_agent --voyage     # Log a new voyage
    python -m capitaine_agent --crew        # Manage crew roster
    python -m capitaine_agent --qa          # Ask maritime questions
    python -m capitaine_agent --status      # Check current voyage status

Install:
    pip install capitaine-agent
"""

import json
import urllib.request
from fleet_agent import BaseAgent
from fleet_agent.fleet_math import EmergenceDetector, HolonomyConsensus

from datetime import datetime, timezone
from typing import Any, Optional

PLATO_URL = "http://localhost:8847"
ROOM = "capitaine-ai"

class CapitaineAgent:
    """Captain's AI First Mate for PLATO-powered maritime operations."""

        
    def detect_emergence(self, events: list) -> dict:
        """Detect emergence via H1 cohomology."""
        detector = EmergenceDetector()
        edges = [(events[i], events[i+1]) for i in range(len(events)-1)]
        detector.update(events, edges)
        return {"emergence_detected": detector.emergence_detected, "h1_cohomology": detector.h1, "confidence": detector.confidence}

    def check_consensus(self, tile_ids: list[int]) -> bool:
        """Check holonomy consensus across tiles."""
        hc = HolonomyConsensus()
        for tid in tile_ids:
            hc.add_tile(tid)
        return hc.check_consensus([tile_ids])

def __init__(self, vessel: str = "capitaine-agent", domain: str = CAPITAINE_AI_ROOM, plato_url: str = "http://localhost:8847"):
        super().__init__(vessel=vessel, domain=domain, plato_url=plato_url)
        self.room = domain

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(f"{PLATO_URL}{path}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def _post(self, path: str, data: dict) -> dict:
        body = json.dumps(data, default=str).encode()
        req = urllib.request.Request(f"{PLATO_URL}{path}", data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def log(self, msg: str) -> None:
        if self.verbose:
            print(f"[capitaine] {msg}")

    # === Voyage Operations ===

    def log_voyage(
        self,
        departure: str,
        destination: str,
        crew_names: list[str],
        catch_summary: str = "",
        weather_conditions: str = "",
        incidents: str = "",
        notes: str = "",
    ) -> dict:
        """Log a voyage as a tile in PLATO."""
        tile = {
            "domain": ROOM,
            "question": f"Voyage record: {departure} → {destination}",
            "answer": self._build_voyage_answer(
                departure, destination, crew_names, catch_summary,
                weather_conditions, incidents, notes
            ),
            "agent": f"capitaine-agent:{self.captain_id}@{self.vessel}",
        }
        result = self._post("/submit", tile)
        self.log(f"Voyage logged: {result.get('status')}")
        return result

    def _build_voyage_answer(
        self, departure, destination, crew_names, catch_summary,
        weather, incidents, notes
    ) -> str:
        parts = [
            f"Departure: {departure}",
            f"Destination: {destination}",
            f"Crew: {', '.join(crew_names)}",
            f"Catch: {catch_summary}",
            f"Weather: {weather}",
            f"Incidents: {incidents}",
            f"Notes: {notes}",
        ]
        return " | ".join(parts)

    def get_voyage_history(self) -> list[dict]:
        """Fetch all voyage records from PLATO."""
        try:
            room = self._get(f"/rooms/{ROOM}")
            return room.get("tiles", [])
        except Exception as e:
            self.log(f"Could not fetch voyages: {e}")
            return []

    # === Crew Coordination ===

    def log_crew_event(
        self,
        crew_name: str,
        event_type: str,
        description: str,
        severity: str = "low",
    ) -> dict:
        """Log a crew-related event (injury, achievement, issue)."""
        tile = {
            "domain": ROOM,
            "question": f"Crew event: {event_type} — {crew_name}",
            "answer": self._build_crew_event_answer(crew_name, event_type, description, severity),
            "agent": f"capitaine-agent:{self.captain_id}@{self.vessel}",
        }
        result = self._post("/submit", tile)
        self.log(f"Crew event logged: {result.get('status')}")
        return result

    def _build_crew_event_answer(
        self, crew_name, event_type, description, severity
    ) -> str:
        return f"Crew: {crew_name} | Event: {event_type} | Severity: {severity} | Description: {description}"

    def get_crew_roster(self) -> list[dict]:
        """Get crew events from PLATO for roster overview."""
        tiles = self.get_voyage_history()
        crew_events = [t for t in tiles if "Crew event:" in t.get("question", "")]
        return crew_events

    # === Maritime Q&A via PLATO ===

    def ask_maritime_question(self, question: str) -> dict:
        """Query PLATO for maritime knowledge / past incidents."""
        try:
            room = self._get(f"/rooms/{ROOM}")
            tiles = room.get("tiles", [])
            # Simple keyword search in past tiles
            relevant = [
                t for t in tiles
                if any(kw in t.get("answer", "") + t.get("question", "")
                       for kw in question.split() if len(kw) > 3)
            ]
            if relevant:
                return {
                    "status": "found",
                    "matches": len(relevant),
                    "top_result": relevant[0].get("answer", "")[:500],
                    "total_hits": len(tiles),
                }
            return {
                "status": "no_match",
                "question": question,
                "hint": "No maritime records found. Try logging more voyages.",
            }
        except Exception as e:
            self.log(f"Q&A query failed: {e}")
            return {"status": "error", "message": str(e)}

    # === Status ===

    def get_status(self) -> dict:
        """Get current vessel status based on PLATO records."""
        voyages = self.get_voyage_history()
        crew_events = self.get_crew_roster()
        return {
            "vessel": self.vessel,
            "captain_id": self.captain_id,
            "total_voyages": len(voyages),
            "total_crew_events": len(crew_events),
            "last_voyage": voyages[-1].get("question", "unknown") if voyages else None,
        }