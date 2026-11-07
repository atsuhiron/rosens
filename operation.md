# 運用メモ(Ubuntu サーバー)

rosens を Ubuntu 上で systemd サービスとして常時稼働させるためのメモ。

## 初期セットアップ

`/etc/systemd/system/rosens.service` を作成(User / パス3箇所は環境に合わせる。`uv` の場所は `which uv`):

```ini
[Unit]
Description=Rosens sensor server
After=network.target

[Service]
User=<user>
# config.json と data/ を置くディレクトリ(実行時の作業ディレクトリになる)
WorkingDirectory=/home/<user>/rosens-run
ExecStart=/home/<user>/.local/bin/uv run --project /home/<user>/dev/rosens rosens-server
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

ユニットファイルを作成・変更したら必ず:

```bash
sudo systemctl daemon-reload
```

## デプロイ

手元(Windows)から `deploy.bat` を実行すると、以下を一括で行う:

```bat
deploy.bat <server-ip>          :: ポート省略時は 8000
deploy.bat <user>@<server-ip> 8000
```

1. ssh でサーバーに入り `dev/rosens` で `git pull` → `uv sync --no-dev` → `sudo systemctl restart rosens`
2. `http://<IP>:8000/` を 200 が返るまで最大10回(2秒間隔)ポーリングし、返ってきた JSON
   (バージョン)を表示

どこかで失敗したらそこで止まり、終了コード 1 を返す。サーバー側のディレクトリ・サービス名は
`deploy.bat` 冒頭の変数で変更できる。`sudo` のパスワードを聞かれた場合はその場で入力する
(`ssh -t` で端末を確保している)。

## 起動・停止

```bash
sudo systemctl start rosens          # 起動
sudo systemctl stop rosens           # 停止
sudo systemctl restart rosens        # 再起動(コード更新後はこれ)
systemctl status rosens              # 状態確認(active/failed、直近ログ数行も出る)

sudo systemctl enable rosens         # OS 起動時に自動起動する
sudo systemctl enable --now rosens   # 自動起動の有効化 + 今すぐ起動を一発で
sudo systemctl disable rosens        # 自動起動をやめる
```

SSH 接続を切ってもサービスは動き続ける(systemd 管理下なので SSH セッションと無関係)。

## ログ(journalctl)

サーバーの stdout/stderr は journald に入る。よく使うもの:

```bash
journalctl -u rosens -f              # tail -f 相当。リアルタイムで追いかける
journalctl -u rosens -n 100          # 直近100行
journalctl -u rosens --since today   # 今日の分
journalctl -u rosens --since "2026-07-20 09:00" --until "2026-07-20 12:00"
journalctl -u rosens -p err          # エラー以上のみ
journalctl -u rosens --no-pager      # ページャなしで全部出す(grep したいとき)
```

ディスクを圧迫してきたら `journalctl --disk-usage` で確認し、
`sudo journalctl --vacuum-time=30d` で30日より古いログを削除できる。

## 動作確認

```bash
curl http://localhost:8000/                        # ping(バージョン返却)
curl "http://localhost:8000/data/environment?start=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)"
```

ダッシュボード: ブラウザで `http://<サーバーのIP>:8000/ui`

## 一時的な起動(検証用)

サービス化せず手元で試すだけなら tmux が手軽:

```bash
tmux                                 # セッション開始
uv run --project ~/rosens rosens-server
# Ctrl+B, D でデタッチ → SSH を切っても動き続ける
tmux attach                          # 再接続後に戻る
```
