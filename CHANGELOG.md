# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-20

First release. A FastAPI server that receives room environment readings from sensors over HTTP,
persists them to daily Parquet files, and visualizes them in a built-in dashboard.

### Added

- `POST /register/environment` — receive a reading (`sensor_id`, `temperature`, `humidity`,
  `pressure`, `uptime_s`); the server timestamps it with `received_at` (JST).
- `GET /data/environment` — return readings in a period (`start` required, `end` optional,
  defaulting to now), grouped per sensor and sorted oldest first.
- `GET /` — ping endpoint reporting API status and version.
- Dashboard at `/ui` (FastAPI `app.frontend()`): temperature / humidity / pressure line charts per
  sensor with period selector (1h/6h/24h/7d), manual refresh, 60s auto-refresh, and zoom.
  Plain HTML/JS with a vendored Apache ECharts — no build step, works offline.
- Storage layer generic over data kinds ("datasets"): rows are appended to
  `data/<kind>/YYYY-MM-DD.parquet` (daily files, JST buckets) with explicit parquet column types
  (readings as Float32, `uptime_s` as Int32). New kinds plug in via a `Dataset` descriptor without
  storage changes.
- `rosens-server` console command to run the server on `0.0.0.0:8000`.
- Configuration via `config.json` in the working directory (currently `data_dir`).
- Debug helper `etc/dump_data.py` to print one daily parquet file.
