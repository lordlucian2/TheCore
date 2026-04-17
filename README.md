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
- `src/thecore/vault.py` — peer resource metadata, voting, tag management.
- `src/thecore/ai.py` — scaffolded Clutch AI query/response modes.
- `src/thecore/room.py` — room presence, timer sync, and offline ghost modeling.
- `src/thecore/storage.py` — SQLite event, room, vault, and AI persistence stores.
- `src/thecore/service.py` — coordinated domain service for events, rooms, Vault, and AI logging.
- `src/thecore/api.py` — FastAPI adapter for event, room, session, vault, and AI endpoints.
- `app.py` — root ASGI application entrypoint for Uvicorn.

## Next steps

- Extend student profile management and room ghost discovery.
- Add client-side sync protocol and conflict handling.
- Build a lightweight frontend or API-driven integration layer.
