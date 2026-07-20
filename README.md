# rosens

Room Sensoring System.

日本語版は [README.ja.md](README.ja.md) を参照してください.

## Overview

Rosens is a FastAPI server that receives room environment readings (temperature, humidity,
pressure) from sensors over HTTP and persists them to daily [Parquet](https://parquet.apache.org/)
files. It also serves a built-in web dashboard that plots the collected readings.

- **Register endpoint** for sensors to POST readings; the server timestamps each reading itself
  (JST), so sensors do not need a clock.
- **Data endpoint** to query readings over a time period, grouped per sensor.
- **Dashboard** at `/ui` — temperature / humidity / pressure line charts, no build step, works
  offline (Apache ECharts is vendored).

Timestamps are handled in JST (UTC+9). Data is stored under `data/<kind>/YYYY-MM-DD.parquet`,
one file per calendar day.

## Requirements

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) for dependency management and running

Dependencies (fastapi, polars, pydantic, uvicorn, and `tzdata` on Windows) are installed
automatically by `uv sync`.

## Running the server

```bash
uv sync                    # install dependencies and the rosens package itself
uv run rosens-server       # start the server on 0.0.0.0:8000
```

`rosens-server` binds to `0.0.0.0:8000`, so other devices on the LAN can reach it at
`http://<host-ip>:8000`. The dashboard is at `http://<host-ip>:8000/ui`.

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

**Response**

```json
{ "status": "ok", "version": "1.0.0" }
```

### `POST /register/environment`

Submit a single environment reading. Called by sensors.

**Request body**

| Field         | Type    | Description                     |
| ------------- | ------- | ------------------------------- |
| `sensor_id`   | string  | Unique identifier for the sensor |
| `temperature` | float   | Temperature in Celsius          |
| `humidity`    | float   | Humidity in percent             |
| `pressure`    | float   | Atmospheric pressure in hPa     |
| `uptime_s`    | integer | Sensor uptime in seconds        |

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

| Parameter | Required | Description                                          |
| --------- | -------- | ---------------------------------------------------- |
| `start`   | yes      | Start of the period (inclusive)                      |
| `end`     | no       | End of the period (inclusive); defaults to now (JST) |

**Response** — one entry per sensor; each `sequence` is ordered oldest first:

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
