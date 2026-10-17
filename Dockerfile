# syntax=docker/dockerfile:1
#
# Builds the React terminal, then serves it + the FastAPI API from one process.
# Runs entirely from the data and models committed to the repo (no network calls,
# no API keys) per the project's offline-runtime policy — see docs/verification.md.

FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
WORKDIR /app

# Install the backend first so this layer only rebuilds when deps/source change,
# not when data/models change. Editable install matters here: sentinel.config
# derives base_dir (and therefore data_dir) from its own file's location on disk,
# so a regular `pip install .` (copied into site-packages) would silently break
# every data path. `-e` keeps config.py at /app/src/sentinel/config.py.
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

COPY data/ ./data/
COPY models/ ./models/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Render (and most PaaS) inject $PORT; default to 8000 for `docker run` elsewhere.
CMD ["sh", "-c", "uvicorn sentinel.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
