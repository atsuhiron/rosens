# rosens

Room Sensoring System.

日本語版は [README.ja.md](README.ja.md) を参照してください.

## Overview

Rosens is a FastAPI server that receives room environment readings (temperature, humidity,
pressure) and event counts (e.g. motion sensor triggers) from sensors over HTTP and persists them
to daily [Parquet](https://parquet.apache.org/) files. It also serves a built-in web dashboard that
plots the collected readings.

- **Register endpoints** for sensors to POST readings; the server timestamps each reading itself
  (JST), so sensors do not need a clock.
- **Data endpoints** to query readings over a time period, grouped per sensor.
- **Dashboard** at `/ui` — temperature / humidity / pressure line charts and a motion count bar
  chart, no build step, works offline (Apache ECharts is vendored).

Timestamps are handled in JST (UTC+9). Data is stored under `data/<kind>/YYYY-MM-DD.parquet`,
one file per calendar day.

## Requirements

- Python >= 3.15
- [uv](https://docs.astral.sh/uv/) for dependency management and running

Dependencies (fastapi, polars, pydantic, uvicorn, and `tzdata` on Windows) are installed
automatically by `uv sync`.

## Running the server

```bash
uv sync                    # install dependencies and the rosens package itself
uv run rosens-server       # start the server on 0.0.0.0:8000
```

`rosens-server` binds to `0.0.0.0:8000`, so other devices on the LAN can reach it at
`http://<host-ip>:8000`. The dashboard is at `http://<host-ip>:8000/ui`; to show only some sensors,
list them comma-separated, as in `http://<host-ip>:8000/ui?sensor_ids=home_1,home_2`.

For development with auto-reload:

```bash
uv run uvicorn rosens.api:app --reload
```

Configuration is read from `config.json` in the working directory (currently only `data_dir`,
default `data`). If the file is absent, defaults are used.

Interactive API docs (Swagger UI) are available at `http://<host-ip>:8000/docs`.

For running as a long-lived service on Ubuntu (systemd, journalctl), see `operation.md`.

## API

All timestamps use ISO 8601. A timezone-aware value is used as-is; a naive value is interpreted
as JST.

### `GET /`

Health check.

**Response** — `version` is the running server's version:

```json
{ "status": "ok", "version": "2.2.0" }
```

### `POST /register/environment`

Submit a single environment reading. Called by sensors.

**Request body**

| Field         | Type    | Required | Description                      |
| ------------- | ------- | -------- | -------------------------------- |
| `sensor_id`   | string  | yes      | Unique identifier for the sensor |
| `temperature` | float   | no       | Temperature in Celsius           |
| `humidity`    | float   | no       | Humidity in percent              |
| `pressure`    | float   | no       | Atmospheric pressure in hPa      |
| `uptime_s`    | integer | no       | Sensor uptime in seconds         |

`sensor_id` may only contain letters, digits, `-`, `.`, `_` and `~`. Anything else is rejected
with 422.

The measured values are optional because sensors differ in what they can measure: send `null` or
omit the key for a value the sensor does not provide. It is stored as null.

```json
{
  "sensor_id": "living",
  "temperature": 24.5,
  "humidity": 55.0,
  "pressure": 1008.3,
  "uptime_s": 3600
}
```

**Response** — the server records the receive time (JST) and returns it:

```json
{ "msg": "received", "received_at": "2026-07-20T13:14:37.649965+09:00" }
```

### `GET /data/environment`

Return readings in a time period, grouped per sensor.

**Query parameters**

| Parameter    | Required | Description                                                                        |
| ------------ | -------- | --------------------------------------------------------------------------------- |
| `start`      | yes      | Start of the period (inclusive)                                                   |
| `end`        | no       | End of the period (inclusive); defaults to now (JST)                              |
| `max_points` | no       | Max points per sensor; excess is thinned by every-Nth decimation. Omit for all points |
| `sensor_ids` | no       | Comma-separated sensors to return (e.g. `home_1,home_2`). Omit for all sensors    |

**Response** — one entry per sensor; each `sequence` is ordered oldest first. A value the sensor
did not provide is `null`:

```json
{
  "data": [
    {
      "sensor_id": "living",
      "sequence": [
        {
          "temperature": 24.5,
          "humidity": 55.0,
          "pressure": 1008.3,
          "uptime_s": 3600,
          "received_at": "2026-07-20T13:14:37.649965+09:00"
        }
      ]
    }
  ]
}
```

Example:

```bash
curl "http://localhost:8000/data/environment?start=2026-07-20T00:00:00"
```

### `POST /register/count`

Submit how many times something happened during a counting period (e.g. motion sensor
triggers). Called by sensors.

**Request body**

| Field        | Type    | Description                                                         |
| ------------ | ------- | ------------------------------------------------------------------- |
| `sensor_id`  | string  | Unique identifier for the sensor (same character rules as above)    |
| `count_type` | string  | What is being counted. Currently only `"motion"` is accepted        |
| `count`      | integer | Number of occurrences during the period (0 or more)                 |
| `duration_s` | integer | Length of the counting period in seconds, ending at receipt (> 0)   |

A `count_type` other than the accepted ones, a negative `count` or a `duration_s` of 0 or less is
rejected with 422.

```json
{
  "sensor_id": "living",
  "count_type": "motion",
  "count": 3,
  "duration_s": 300
}
```

**Response** — same as `POST /register/environment`; `received_at` is the end of the counting
period:

```json
{ "msg": "received", "received_at": "2026-07-20T13:14:37.649965+09:00" }
```

### `GET /data/count`

Return counts in a time period, grouped per sensor and count type.

**Query parameters**

| Parameter     | Required | Description                                                                         |
| ------------- | -------- | ----------------------------------------------------------------------------------- |
| `start`       | yes      | Start of the period (inclusive)                                                     |
| `end`         | no       | End of the period (inclusive); defaults to now (JST)                                |
| `sensor_ids`  | no       | Comma-separated sensors to return (e.g. `home_1,home_2`). Omit for all sensors      |
| `count_types` | no       | Comma-separated count types to return (e.g. `motion`). Omit for all types           |
| `bucket_s`    | no       | Sum counts into `bucket_s`-second buckets (> 0). Omit to return the raw counts      |

Counts are never thinned (there is no `max_points`), since dropping a row would lose
occurrences. To shrink a long period, use `bucket_s` instead: buckets are aligned to JST midnight
(e.g. `bucket_s=21600` gives 0/6/12/18 JST buckets), and each count goes to the bucket holding the
middle of its `duration_s` window. A bucket is returned in the same shape as a raw count —
`count` is the bucket total, `duration_s` is `bucket_s` and `received_at` is the end of the bucket
(in the future for the bucket still in progress). Buckets with no data are left out.

**Response** — one entry per sensor and count type; each `sequence` is ordered oldest first:

```json
{
  "data": [
    {
      "sensor_id": "living",
      "count_type": "motion",
      "sequence": [
        {
          "count": 3,
          "duration_s": 300,
          "received_at": "2026-07-20T13:14:37.649965+09:00"
        }
      ]
    }
  ]
}
```

Example (hourly totals):

```bash
curl "http://localhost:8000/data/count?start=2026-07-20T00:00:00&bucket_s=3600"
```
