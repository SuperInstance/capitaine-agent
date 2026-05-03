# capitaine-agent

**Captain's AI First Mate** for [capitaine.ai](https://capitaine.ai) — voyage logging, crew coordination, and maritime Q&A powered by PLATO.

## Features

- **Voyage Logging**: Record departures, destinations, crew, catch, weather, and incidents
- **Crew Coordination**: Log crew events (injuries, achievements, issues) with severity tracking
- **Maritime Q&A**: Query PLATO for past maritime knowledge and similar incidents
- **Status Overview**: Get a quick snapshot of vessel activity

## Installation

```bash
pip install capitaine-agent
```

## Usage

```bash
# Interactive voyage logger
capitaine --voyage

# Log a crew event
capitaine --crew

# Ask a maritime question
capitaine --qa "What incidents were logged near Cape Cod?"

# Check vessel status
capitaine --status

# View voyage history
capitaine --history
```

## PLATO Integration

Communicates with PLATO tile server at `http://localhost:8847`. Each voyage and crew event is logged as a tile in the `capitaine-ai` room.

## License

MIT
## Related

- [capitaine.ai](https://capitaine.ai) — Live site
- [capitaine-ai-pages](https://github.com/SuperInstance/capitaine-ai-pages) — GitHub Pages source
