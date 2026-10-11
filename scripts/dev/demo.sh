#!/usr/bin/env bash
set -eo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PORT="${PORT:-8000}"
LIVE_MODE=false

for arg in "$@"; do
  case "$arg" in
    --live)
      LIVE_MODE=true
      ;;
    --port=*)
      PORT="${arg#*=}"
      ;;
    *)
      ;;
  esac
done

# Build frontend if dist is missing or older than src
if [ ! -d "frontend/dist" ] || [ ! -f "frontend/dist/index.html" ] || [ "$(find frontend/src -newer frontend/dist/index.html 2>/dev/null | wc -l)" -gt 0 ]; then
  echo "[demo] Building frontend assets..."
  (cd frontend && npm run build)
fi

API_PID=""
RECORDER_PID=""

cleanup() {
  echo ""
  echo "[demo] Shutting down services..."
  if [ -n "$API_PID" ] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID" 2>/dev/null || true
  fi
  if [ -n "$RECORDER_PID" ] && kill -0 "$RECORDER_PID" 2>/dev/null; then
    kill "$RECORDER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "[demo] Starting FastAPI server on port $PORT..."
uv run uvicorn sentinel.api.app:app --host 127.0.0.1 --port "$PORT" &
API_PID=$!

if [ "$LIVE_MODE" = true ]; then
  echo "[demo] Starting live news & SEC recorder (interval: 300s)..."
  uv run python scripts/live/record_live.py --interval 300 &
  RECORDER_PID=$!
fi

# Wait for API health check
echo -n "[demo] Waiting for S&P Sentinel API to become ready..."
READY=false
for _ in {1..30}; do
  if curl -s "http://127.0.0.1:${PORT}/api/health" | grep -q '"status":"ok"' 2>/dev/null; then
    echo " READY."
    READY=true
    break
  fi
  echo -n "."
  sleep 1
done
if [ "$READY" != true ]; then
  echo " FAILED: the API did not become healthy within 30 s." >&2
  exit 1
fi

echo "======================================================================"
echo " S&P Sentinel Risk Intelligence Terminal is running!"
echo " URL: http://127.0.0.1:${PORT}"
echo " Mode: $([ "$LIVE_MODE" = true ] && echo "LIVE INGESTION ACTIVE" || echo "OFFLINE / LOCAL REPLAY")"
echo " Press Ctrl+C to terminate."
echo "======================================================================"

wait "$API_PID"
