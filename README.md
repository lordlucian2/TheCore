# TheCore (MVP Foundation)

This repository contains a Python domain layer for TheCore concepts from the product structure notes:

- **Study Ghosts** for asynchronous social presence.
- **Local Sync Engine** for offline event capture + burst sync.
- **Nonce replay protection** and batch signature verification.
- **Tutorial Quest Scaffolding** (Difference Engine, Why Bounty, Socratic Duel).
- **Squad Dashboard** pulse metrics for teachers/guild masters.
- **Predicted Grade + Monthly Pulse ranking** for motivation loops.

## Quickstart

```bash
python -m unittest discover -s tests
```

## Package layout

- `src/thecore/engine.py` — offline events, validation, signatures, sync batching, ghost snapshots.
- `src/thecore/quests.py` — quest types and first tutorial quest generation.
- `src/thecore/squad.py` — class-level pulse summaries and predicted grades.
- `src/thecore/analytics.py` — ranking and predicted-grade heuristics.

## Next steps

- Add persistent local storage (SQLite or LiteFS-friendly log).
- Expose this domain model via an API (FastAPI).
- Add client-side sync protocol and conflict handling.
- Replace heuristic grade predictions with calibrated model outputs from historical results.
