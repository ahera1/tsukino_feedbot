# Tsukino Feedbot (月乃 フィードボット)

AIを活用したフィード要約・Mastodon投稿ボット

## セットアップ

### Docker環境（推奨）

1. 設定ファイルの準備:
```bash
copy .env.example .env
copy feeds.example.json feeds.json
```

2. 環境変数の設定:
`.env` ファイルを編集してAPIキー等を設定
- `OPENROUTER_API_KEY`: OpenRouter APIキー
- `MASTODON_INSTANCE_URL`: MastodonインスタンスURL
- `MASTODON_ACCESS_TOKEN`: Mastodonアクセストークン
- `POST_VISIBILITY`: Mastodon投稿の公開範囲（public/unlisted/private/direct）

3. フィード設定の調整:
`feeds.json` ファイルで監視するRSSフィードを設定
- JSONファイル形式で、プログラムを変更せずに設定変更が可能
- 各フィードにはURLと表示名を設定
- 例: `{"url": "https://example.com/feed", "name": "Example Blog"}`

4. 実行:

**デーモンモード（常時稼働 - デフォルト）:**
```bash
docker-compose up -d --build
```

**ワンショット実行（一回だけチェック）:**
```bash
docker-compose run --rm feedbot-once
```

**ステータス確認:**
```bash
docker-compose run --rm feedbot-status
```

**停止:**
```bash
docker-compose down
```

**ログ確認:**
```bash
docker-compose logs -f
```

## 機能

- RSSフィードの定期監視
- AI要約生成（OpenRouter API）
- Mastodonへの自動投稿
- 既読記事管理

## 設定ファイル構成

- `.env`: 環境変数（APIキー、認証情報など）
- `config.py`: メイン設定ファイル（汎用的な設定読み込み処理、Git管理対象）
- `feeds.json`: フィード設定専用ファイル（監視するRSSフィードの一覧、JSON形式）
- 個人設定ファイル（`.env` と `feeds.json`）には `.example` 版があり、これをコピーして使用します
- `.env` と `feeds.json` は個人設定のため .gitignore で管理対象外になっています

## 設定可能項目

- フィード取得間隔
- 記事の保持期間
- AI要約プロンプト
- Mastodon投稿設定
  - **公開範囲**: 投稿の公開レベル（public: 公開, unlisted: 未収載, private: フォロワーのみ, direct: ダイレクト）
- **時間帯制限**: 投稿を行わない時間帯の設定（生活時間帯を考慮）
  - `ENABLE_QUIET_HOURS`: 時間帯制限の有効/無効
  - `QUIET_HOURS_START`: 投稿禁止開始時刻（24時間形式）
  - `QUIET_HOURS_END`: 投稿禁止終了時刻（24時間形式）
- **ウェイト設定**: 連続投稿を防ぐための待機時間
  - `POST_WAIT`: 投稿処理間の待機時間（秒、デフォルト: 60秒）

## Docker実行モード

### 常時稼働（デフォルト）
```bash
# バックグラウンドで起動
docker-compose up -d --build

# ログ確認
docker-compose logs -f

# 停止
docker-compose down
```

### メンテナンスコマンド

**ワンショット実行**（一回だけフィードをチェック）:
```bash
docker-compose run --rm feedbot-once
```

**ステータス確認**（現在の状況を表示）:
```bash
docker-compose run --rm feedbot-status
```

**データクリーンアップ**（デーモン内で自動実行されるため、通常は不要）:
- 古い記事は自動的にクリーンアップされます
- 記事保持期間: `ARTICLE_RETENTION_DAYS`（デフォルト7日）
- 読み取り記録保持期間: `READ_RECORD_RETENTION_DAYS`（デフォルト3日）

### ローカル実行（開発・テスト用）

インタラクティブメニューでの実行:
```bash
python main.py
```

環境変数で実行モードを指定:
```bash
# ワンショット実行
$env:RUN_MODE="once"; python main.py

# デーモンモード
$env:RUN_MODE="daemon"; python main.py

# ステータス確認
$env:RUN_MODE="status"; python main.py
```
