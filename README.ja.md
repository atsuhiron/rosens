# rosens

Room Sensoring System(部屋の環境センシングシステム).

For the English version, see [README.md](README.md).

## 概要

Rosens は、センサーから HTTP 経由で部屋の環境データ(温度・湿度・気圧)を受け取り、日付ごとの
[Parquet](https://parquet.apache.org/) ファイルに永続化する FastAPI サーバーです。収集したデータを
グラフ表示するダッシュボードも内蔵しています。

- **登録エンドポイント**: センサーが読み取り値を POST する。受信時刻はサーバー側(JST)で付与する
  ため、センサーは時計を持つ必要がありません。
- **取得エンドポイント**: 期間を指定して読み取り値を取得する(センサーごとにグルーピング)。
- **ダッシュボード**(`/ui`): 温度・湿度・気圧の折れ線グラフ。ビルド不要、オフラインでも動作
  (Apache ECharts を同梱)。

時刻はすべて JST(UTC+9)で扱います。データは `data/<種別>/YYYY-MM-DD.parquet` に、1日1ファイルで
保存されます。

## 必要要件

- Python >= 3.13
- 依存管理と実行に [uv](https://docs.astral.sh/uv/)

依存パッケージ(fastapi, polars, pydantic, uvicorn、Windows では `tzdata`)は `uv sync` で自動的に
インストールされます。

## サーバーの起動

```bash
uv sync                    # 依存関係と rosens パッケージ自体をインストール
uv run rosens-server       # 0.0.0.0:8000 でサーバーを起動
```

`rosens-server` は `0.0.0.0:8000` で待ち受けるため、LAN 内の他の端末から
`http://<ホストのIP>:8000` でアクセスできます。ダッシュボードは `http://<ホストのIP>:8000/ui` です。

開発時に自動リロードを使う場合:

```bash
uv run uvicorn rosens.api:app --reload
```

設定は作業ディレクトリの `config.json` から読み込まれます(現状は `data_dir` のみ、既定値は
`data`)。ファイルが無い場合は既定値が使われます。

対話的な API ドキュメント(Swagger UI)は `http://<ホストのIP>:8000/docs` で確認できます。

Ubuntu 上で常時稼働のサービスとして動かす方法(systemd、journalctl)は `operation.md` を参照して
ください。

## API 仕様

時刻はすべて ISO 8601 形式です。タイムゾーン付きの値はそのまま使われ、タイムゾーンなし(naive)の
値は JST として解釈されます。

### `GET /`

ヘルスチェック。

**レスポンス**

```json
{ "status": "ok", "version": "1.0.0" }
```

### `POST /register/environment`

環境データを1件登録する。センサーが呼び出すエンドポイント。

**リクエストボディ**

| フィールド    | 型      | 説明                     |
| ------------- | ------- | ------------------------ |
| `sensor_id`   | string  | センサーの一意な識別子   |
| `temperature` | float   | 温度(摂氏)             |
| `humidity`    | float   | 湿度(%)                 |
| `pressure`    | float   | 気圧(hPa)               |
| `uptime_s`    | integer | センサーの稼働時間(秒) |

```json
{
  "sensor_id": "living",
  "temperature": 24.5,
  "humidity": 55.0,
  "pressure": 1008.3,
  "uptime_s": 3600
}
```

**レスポンス** — サーバーが受信時刻(JST)を記録して返します:

```json
{ "msg": "received", "received_at": "2026-07-20T13:14:37.649965+09:00" }
```

### `GET /data/environment`

期間を指定して読み取り値を取得する(センサーごとにグルーピング)。

**クエリパラメータ**

| パラメータ | 必須 | 説明                                            |
| ---------- | ---- | ----------------------------------------------- |
| `start`    | はい | 期間の開始(この時刻を含む)                    |
| `end`      | いいえ | 期間の終了(この時刻を含む)。省略時は現在時刻(JST) |

**レスポンス** — センサーごとに1エントリ。各 `sequence` は古い順に並びます:

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

例:

```bash
curl "http://localhost:8000/data/environment?start=2026-07-20T00:00:00"
```
