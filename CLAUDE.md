# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Rosens is a Room Sensoring System: a FastAPI server that receives room environment readings
(temperature, humidity, pressure) from sensors over HTTP and persists them to daily Parquet files.

## Commands

Run `check.bat` to format, lint, type-check, and test in one go — this is the standard way to
validate a change before considering it done. It runs, in order:

```
uv run ruff format
uv run ruff check --fix
uv run ty check
uv run pytest
```

Individual commands:

- `uv sync` — install/update dependencies (also (re)installs the `rosens` package itself, required
  for `rosens.*` imports to resolve — see Packaging note below).
- `uv run ruff format` / `uv run ruff check --fix` — formatting and lint (ruff selects `ALL` rules,
  see `ruff.toml` for the ignore list).
- `uv run ty check` — static type checking (`ty.toml` scopes it to `src` and `tests`).
- `uv run pytest` — run all tests; `uv run pytest tests/test_storage.py::test_save_creates_new_file`
  to run a single test.
- `uv run uvicorn rosens.api:app --reload` — run the dev server.

## Architecture

- `src/rosens/api.py` — FastAPI app and routes, organized per data kind ("dataset"):
  `POST /register/environment` receives a reading, `GET /data/environment` returns readings in a
  period grouped per sensor. Handlers are `async def`; the actual file I/O is dispatched via
  `asyncio.to_thread` because Parquet I/O in `storage.py` is blocking and would otherwise stall the
  event loop.
- `src/rosens/datasets.py` — `Dataset[RecordT]` descriptor: one per data kind, bundling the
  subdirectory name under `data_dir` and the parquet `schema_overrides` (e.g. Float32/Int32).
  See "API extension policy" below for how new kinds are added.
- `src/rosens/storage.py` — persistence layer, exposed as the `Storage` class (constructed with a
  `data_dir`); `save(dataset, data, received_at)` / `load(dataset, start, end)` are generic over
  the dataset. The app obtains the shared instance via `get_storage()` (`lru_cache`d so there is
  exactly one instance — and one lock — per process). Parquet has no native append mode, so writing
  a reading means: read the existing daily file (if any), concatenate the new row with polars, and
  rewrite the whole file. An instance-level `threading.Lock` serializes this read-modify-write so
  concurrent requests (FastAPI runs work in a thread pool) don't race on the same file. Files are
  named `{data_dir}/{dataset}/YYYY-MM-DD.parquet`, one per calendar day (JST), e.g.
  `data/environment/2026-07-19.parquet`.
- `src/rosens/config.py` — defines `Config` (currently just `data_dir`) and `get_config()`, which
  loads `config.json` from the working directory (`lru_cache`d). Falls back to defaults if the file
  doesn't exist. This is the only source of runtime configuration — there are no environment-variable
  overrides.
- `src/rosens/models/` — pydantic schemas: `environment.py` (the inbound environment reading and
  its stored-row TypedDict) and `api_models.py` (response bodies).
- `src/rosens/frontend/` — static dashboard served at `/ui` via FastAPI's `app.frontend()`
  (requires fastapi >= 0.138). Plain HTML/JS, no build step; `echarts.min.js` is a vendored copy of
  Apache ECharts (from jsDelivr) so the page works without internet access. The directory is
  resolved from `api.py`'s `__file__`, not the working directory.
- `src/rosens/util.py` — shared constants; `TZ` is a fixed JST (UTC+9) offset used to timestamp
  incoming readings server-side (sensors do not send their own timestamp).

## API extension policy

The API grows by adding new data kinds ("datasets"), not by widening existing schemas. Decisions
already made (with the user) that future work should follow:

- **One path per kind, no type discriminator**: new kinds get their own endpoints
  (`POST /register/<kind>`, `GET /data/<kind>`) with their own pydantic models, mirroring
  `/register/environment` and `/data/environment`. Do not fold multiple kinds into one endpoint
  with a `type` field.
- **Adding a new kind** takes three steps, in this order — `storage.py` must not need changes:
  1. `src/rosens/models/<kind>.py`: the inbound pydantic model and the stored-row `TypedDict`.
  2. `src/rosens/datasets.py`: one `Dataset[<KindRecord>]` entry (directory name +
     parquet `schema_overrides`).
  3. `src/rosens/api.py`: the two endpoints, following the environment handlers as the template.
- **Storage model is uniform**: every kind is "rows with a server-side `received_at`, appended to
  a daily parquet file under `data/<kind>/`". This covers periodic readings (CO2, illuminance, …)
  and irregular event data (door open/close, motion) alike — event kinds just post whenever the
  event happens. Kind-specific response shaping (like the per-sensor grouping for environment)
  lives in the API layer, not in storage.
- **Shared response models stay kind-independent**: `PingResponse` / `RegisterResponse` in
  `api_models.py` are reused by every register endpoint; per-kind response models are named after
  the kind (`GetEnvironmentDataResponse`, …).
- **No compatibility burden yet**: the system is not in production, so schema/endpoint changes may
  be made freely without migration code — delete stale parquet files instead. Revisit this rule
  once real deployments exist.

## Things to know

- **Packaging**: the project has a `[build-system]` (hatchling) so `uv sync`/`uv run` installs
  `rosens` itself in editable mode. Without this, `import rosens` fails — if that ever regresses,
  re-running `uv sync` after any `pyproject.toml` packaging change fixes it.
- **`tzdata` on Windows**: `tzdata` is a required dependency on Windows (`sys_platform == 'win32'`)
  because polars converts timezone-aware datetimes through `zoneinfo` internally, and Windows has
  no system IANA tz database. Without it, reading back a parquet file with tz-aware columns raises
  `ZoneInfoNotFoundError`.
- Storage is tested against a temp directory by constructing `Storage(data_dir=tmp_path)` directly
  (see `tests/test_storage.py`) rather than touching the real `config.json`/`data`.
