# capitaine-agent

**Captain's AI First Mate** for [capitaine.ai](https://capitaine.ai) — voyage logging, crew coordination, and maritime Q&A powered by PLATO.

## What This Gives You

- **Voyage logging** — record departures, destinations, crew, catch, weather, and incidents
- **Crew coordination** — log crew events with severity tracking
- **Maritime Q&A** — query PLATO for past maritime knowledge and similar incidents
- **CLI interface** — interactive voyage logger with `capitaine` command

## Installation

```bash
pip install capitaine-agent
```

## Quick Start

```bash
# Interactive voyage logger
capitaine --voyage

# Log a crew event
capitaine --crew

# Ask a maritime question
capitaine --qa "What incidents were logged near Cape Cod?"

# Check vessel status
capitaine --status
```

## Python API

```python
from capitaine_agent import log_voyage, log_crew_event, query_maritime

log_voyage(departure="Boston Harbor", destination="Georges Bank", crew=5)
log_crew_event("Alice", "injury", "slipped on deck", severity="moderate")
results = query_maritime("weather delays Cape Cod")
```

## PLATO Integration

Each voyage and crew event is logged as a tile in the `capitaine-ai` room on the PLATO tile server (`localhost:8847`).

## Testing

```bash
pip install -e .
pytest
```

## How It Fits
- [OpenConstruct Documentation](https://github.com/SuperInstance/openconstruct-docs) — ecosystem-wide docs and guides

Domain agent in the Cocapn Fleet. Works alongside `capitaine-ai` (crew orchestration engine) and `capitaineai-com-pages` (landing site).

## License

MIT
