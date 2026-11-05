# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2026-11-06

### Changed

- `POST /register/environment` — `temperature`, `humidity`, `pressure` and `uptime_s` are now
  optional, since sensors differ in what they can measure. Send `null` or omit the key for a value
  the sensor does not provide; it is stored as null. `sensor_id` is still required.
- `GET /data/environment` — those values may now be `null` in the response.
- Dashboard (`/ui`) — null values are not drawn, and a sensor with no value at all for a metric in
  the period is left out of that chart (and its legend).

## [2.0.0] - 2026-11-01

### Added

- Dashboard (`/ui`) — choose which sensors to show from the URL, comma-separated, as in
  `/ui?sensor_ids=home_1,home_2`. Without the parameter every sensor is shown.
- `GET /data/environment` — optional `sensor_ids` query parameter (comma-separated) to return only
  those sensors. Unknown ids are ignored.

### Changed

- **Breaking:** `POST /register/environment` — `sensor_id` may now only contain URL-unreserved
  characters (letters, digits, `-`, `.`, `_`, `~`) and must not be empty. Anything else gets a 422.
  Stored data with other ids can still be read.

### Internal

- `deploy.bat` — deploy to the server in one command (`deploy.bat <host> [port]`): pulls, syncs
  dependencies, restarts the systemd service over ssh, then polls `GET /` until it answers 200.
- Require Python 3.15 or later.
- Update libraries, including polars 2.

## [1.1.1] - 2026-08-22

### Fixed

- Dashboard (`/ui`) — the time labels on the charts' horizontal axis no longer overlap on narrow
  screens (smartphones). The number of ticks now follows the chart width (3 / 5 / 7 for narrow /
  medium / wide), labels shrink slightly on phones, and any that would still collide are hidden.
  Tick density on desktop is unchanged.

### Internal

- Update libraries.

## [1.1.0] - 2026-07-26

### Added

- Dashboard (`/ui`) — shows the server's API version next to the title, fetched from the ping
  endpoint (`GET /`) on load.
- `GET /data/environment` — optional `max_points` query parameter. When given, each sensor's
  sequence is thinned to at most `max_points` points by every-Nth decimation (the last point is
  always kept); omitting it returns every point as before. The dashboard passes the chart's pixel
  width so long periods (7d ≈ 10k points/sensor) shrink to what the graph can actually show, cutting
  response size and client-side parse cost. Stored Parquet data is untouched.

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
