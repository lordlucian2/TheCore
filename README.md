# TheCore (MVP Foundation)

This repository now includes a small Python foundation for TheCore concepts from the product structure notes:

- **Study Ghosts** for asynchronous social presence.
- **Local Sync Engine** for offline event capture + burst sync.
- **Tutorial Quest Scaffolding** (Difference Engine, Why Bounty, Socratic Duel).
- **Squad Dashboard** pulse metrics for teachers/guild masters.

## Quickstart

```bash
python -m unittest discover -s tests
```

## Package layout

- `src/thecore/engine.py` — offline events, verification signatures, burst sync, ghost snapshots.
- `src/thecore/quests.py` — quest types and first tutorial quest generation.
- `src/thecore/squad.py` — class-level pulse summaries.

## Next steps

- Add persistent local storage (SQLite or LiteFS-friendly log).
- Expose this domain model via an API (FastAPI).
- Add client-side sync protocol and conflict handling.
