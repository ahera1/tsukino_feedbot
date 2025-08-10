# Tsukino Feedbot

AIを活用したフィード要約・Mastodon投稿ボット

## セットアップ

### Docker環境（推奨）

1. 設定ファイルの準備:
```bash
copy .env.example .env
copy config.example.py config.py
```

2. 環境変数の設定:
`.env` ファイルを編集してAPIキー等を設定
- `OPENROUTER_API_KEY`: OpenRouter APIキー
- `MASTODON_INSTANCE_URL`: MastodonインスタンスURL
- `MASTODON_ACCESS_TOKEN`: Mastodonアクセストークン

3. フィード設定の調整（オプション）:
`config.py` のFEED_URLSを編集して監視するフィードを設定

4. 実行:

**インタラクティブモード（メニュー操作）:**
```bash
docker-compose up --build
```

**デーモンモード（バックグラウンド自動実行）:**
```bash
docker-compose --profile daemon up -d --build
```

**ワンショット実行（一回だけチェック）:**
```bash
docker-compose --profile once up --build
```

**ステータス確認:**
```bash
docker-compose --profile status up --build
```

**データクリーンアップ:**
```bash
docker-compose --profile cleanup up --build
```

## 機能

- RSSフィードの定期監視
- AI要約生成（OpenRouter API）
- Mastodonへの自動投稿
- 既読記事管理

## 設定可能項目

- フィード取得間隔
- 記事の保持期間
- AI要約プロンプト
- Mastodon投稿設定
- **時間帯制限**: 投稿を行わない時間帯の設定（生活時間帯を考慮）
  - `ENABLE_QUIET_HOURS`: 時間帯制限の有効/無効
  - `QUIET_HOURS_START`: 投稿禁止開始時刻（24時間形式）
  - `QUIET_HOURS_END`: 投稿禁止終了時刻（24時間形式）

## Docker実行モード

- **インタラクティブモード**: メニュー操作で手動実行
  ```bash
  docker-compose up --build
  ```

- **デーモンモード**: バックグラウンドで自動継続実行
  ```bash
  docker-compose --profile daemon up -d --build
  # ログ確認: docker-compose logs -f tsukino-feedbot-daemon
  # 停止: docker-compose --profile daemon down
  ```

- **ワンショット実行**: 一回だけフィードをチェック
  ```bash
  docker-compose --profile once up --build
  ```

- **ステータス確認**: 現在の状況を表示
  ```bash
  docker-compose --profile status up --build
  ```

- **データクリーンアップ**: 古いデータを削除
  ```bash
  docker-compose --profile cleanup up --build
  ```

### インタラクティブモードで入力ができない場合

Docker環境では`input()`が正常に動作しない場合があります。その場合は上記のプロファイル指定での実行をご利用ください。
