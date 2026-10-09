# Verification

Commands that reproduce every claim in the README and deck.

```bash
uv sync
uv run ruff check .                         # lint
python scripts/verify_hygiene.py            # manifest SHA-256 for every dataset, no secrets/DBs/large files, no network calls in src/
uv run pytest                               # backend tests (contracts, NLP, dedup, stress, API, metrics gates)
(cd frontend && npm ci && npx tsc --noEmit && npm test && npm run build)
uv run python scripts/run_evaluation.py     # regenerate docs/metrics.json
```

Optional, with network access (build time only):

```bash
uv run --group data python scripts/data/fetch_real.py   # real datasets into data/raw/real (checksums in CHECKSUMS.json)
uv run python scripts/data/convert_real.py              # rebuild committed samples; manifest re-registered
uv run python scripts/models/train_event.py             # then train_sentiment.py and train_impact.py
uv run --group data python scripts/backtest_module_a.py
uv run python scripts/live/record_live.py --once        # one live GDELT + SEC 8-K capture cycle
```

Manual end-to-end check: start `uv run uvicorn sentinel.api.app:app --port 8000`, open the terminal, load "Real news: Polygon 2023", step the replay, open the Index Rebalancer tab (weights move with sentiment), and run "PS example" and "Silicon Valley Bank failure" on the Wholesale Stress tab (before/after chart and reconciled waterfall).
