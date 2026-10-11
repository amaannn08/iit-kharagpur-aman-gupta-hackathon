.PHONY: setup demo api frontend record test eval

setup:
	uv sync && (cd frontend && npm ci)

frontend:
	cd frontend && npm run build

api:
	uv run uvicorn sentinel.api.app:app --port 8000

record:
	uv run python scripts/live/record_live.py --interval 300

test:
	uv run ruff check . && uv run pytest -q && (cd frontend && npm test)

eval:
	uv run python scripts/run_evaluation.py --write-readme

demo:
	bash scripts/dev/demo.sh
