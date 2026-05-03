"""Tests for capitaine_agent."""
import pytest
from unittest.mock import patch

from capitaine_agent import CapitaineAgent, ROOM


class TestCapitaineAgent:
    """Tests for CapitaineAgent class."""

    @pytest.fixture
    def agent(self):
        return CapitaineAgent(captain_id="test-captain", vessel="Sea Hawk", verbose=False)

    # === _build_voyage_answer ===

    def test_build_voyage_answer_basic(self, agent):
        ans = agent._build_voyage_answer(
            departure="Boston",
            destination="Cape Cod",
            crew_names=["Alice", "Bob"],
            catch_summary="500lb cod",
            weather="sunny",
            incidents="none",
            notes="Good day",
        )
        assert "Departure: Boston" in ans
        assert "Destination: Cape Cod" in ans
        assert "Crew: Alice, Bob" in ans
        assert "Catch: 500lb cod" in ans
        assert "Weather: sunny" in ans
        assert " | " in ans

    def test_build_voyage_answer_empty(self, agent):
        ans = agent._build_voyage_answer("", "", [], "", "", "", "")
        assert "Departure:" in ans

    # === _build_crew_event_answer ===

    def test_build_crew_event_answer(self, agent):
        ans = agent._build_crew_event_answer(
            "Alice", "injury", "slipped on deck", "medium"
        )
        assert "Crew: Alice" in ans
        assert "Event: injury" in ans
        assert "Severity: medium" in ans
        assert "slipped on deck" in ans

    # === log_voyage ===

    @patch.object(CapitaineAgent, "_post")
    def test_log_voyage_calls_post(self, mock_post, agent):
        mock_post.return_value = {"status": "ok", "tile_hash": "voy123"}
        result = agent.log_voyage(
            departure="Boston",
            destination="Cape Cod",
            crew_names=["Alice"],
            catch_summary="cod",
            weather="sunny",
            incidents="",
            notes="",
        )
        assert result["status"] == "ok"
        tile = mock_post.call_args[0][1]
        assert tile["domain"] == ROOM
        assert "Boston" in tile["question"]

    # === log_crew_event ===

    @patch.object(CapitaineAgent, "_post")
    def test_log_crew_event_calls_post(self, mock_post, agent):
        mock_post.return_value = {"status": "ok", "tile_hash": "crew123"}
        result = agent.log_crew_event("Bob", "achievement", "safety record", "low")
        assert result["status"] == "ok"
        tile = mock_post.call_args[0][1]
        assert "Crew event:" in tile["question"]
        assert "Bob" in tile["question"]

    # === ask_maritime_question ===

    @patch.object(CapitaineAgent, "_get")
    def test_ask_maritime_question_no_match(self, mock_get, agent):
        mock_get.return_value = {"tiles": []}
        result = agent.ask_maritime_question("bad weather")
        assert result["status"] == "no_match"

    @patch.object(CapitaineAgent, "_get")
    def test_ask_maritime_question_finds_match(self, mock_get, agent):
        mock_get.return_value = {
            "tiles": [
                {"question": "Voyage: Boston → Cape Cod", "answer": "Weather: storm | Incidents: none"},
                {"question": "Crew event: Alice", "answer": "Injury on deck"},
            ]
        }
        result = agent.ask_maritime_question("storm")
        assert result["status"] == "found"
        assert result["matches"] >= 1

    # === get_status ===

    @patch.object(CapitaineAgent, "_get")
    def test_get_status_empty(self, mock_get, agent):
        mock_get.return_value = {"tiles": []}
        status = agent.get_status()
        assert status["vessel"] == "Sea Hawk"
        assert status["total_voyages"] == 0

    @patch.object(CapitaineAgent, "_get")
    def test_get_status_with_voyages(self, mock_get, agent):
        mock_get.return_value = {
            "tiles": [
                {"question": "Voyage: A → B", "answer": "Crew: Alice"},
                {"question": "Crew event: Bob", "answer": "Achievement"},
            ]
        }
        status = agent.get_status()
        assert status["total_voyages"] == 2  # both counted in tiles


class TestCLI:
    """Tests for CLI module."""

    def test_cli_module_exists(self):
        from capitaine_agent import cli
        assert hasattr(cli, "main")