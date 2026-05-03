#!/usr/bin/env python3
"""capitaine-agent — Captain's AI first mate for capitaine.ai.
Voyage logging, crew coordination, maritime Q&A via PLATO.
"""

import json, time
from typing import List, Dict, Optional

class CapitaineAgent:
    def __init__(self, vessel: str = "fleet-default", plato_url="http://147.224.38.131:8847"):
        self.vessel = vessel
        self.plato_url = plato_url
        self.voyages: List[Dict] = []
        self.crew: List[Dict] = []
    
    def log_voyage(self, destination: str, distance_nm: float, duration_hours: float, conditions: str="", notes: str=""):
        voyage = {
            "destination": destination,
            "distance_nm": distance_nm,
            "duration_hours": duration_hours,
            "conditions": conditions,
            "notes": notes,
            "time": time.time()
        }
        self.voyages.append(voyage)
        self._submit(f"Voyage to {destination}", f"{distance_nm}nm in {duration_hours}h. Conditions: {conditions}. {notes}")
        return voyage
    
    def add_crew(self, name: str, role: str, status: str="active"):
        member = {"name": name, "role": role, "status": status, "joined": time.time()}
        self.crew.append(member)
        self._submit(f"Crew member: {name}", f"Role: {role}. Status: {status}")
        return member
    
    def get_voyage_log(self) -> Dict:
        if not self.voyages: return {"error": "No voyages logged"}
        total_distance = sum(v["distance_nm"] for v in self.voyages)
        total_hours = sum(v["duration_hours"] for v in self.voyages)
        return {"vessel": self.vessel, "total_voyages": len(self.voyages), "total_distance_nm": round(total_distance, 1), "total_hours": round(total_hours, 1), "crew_count": len(self.crew), "crew": [c["name"] for c in self.crew]}
    
    def get_crew_status(self) -> Dict:
        active = [c for c in self.crew if c["status"] == "active"]
        return {"total_crew": len(self.crew), "active": len(active), "on_leave": len(self.crew) - len(active)}
    
    def _submit(self, q: str, a: str):
        try:
            import urllib.request
            urllib.request.urlopen(urllib.request.Request(f"{self.plato_url}/submit", data=json.dumps({"question": q, "answer": a, "agent": "capitaine-agent", "room": "capitaine"}).encode(), headers={"Content-Type": "application/json"}), timeout=5)
        except: pass

def demo():
    a = CapitaineAgent(vessel="Cocapn-1")
    a.add_crew("Thorne", "Captain", "active")
    a.add_crew("Elara", "Navigator", "active")
    a.add_crew("Skeev", "Scout", "on_leave")
    a.log_voyage("Iron Harbor", 45, 6, "calm seas", "Unloaded grain")
    a.log_voyage("Crimson Cove", 120, 18, "rough weather", "Avoided patrols")
    print(a.get_voyage_log())
    print(a.get_crew_status())

if __name__ == "__main__": demo()
