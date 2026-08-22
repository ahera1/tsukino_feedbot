# Tsukino Feedbot (月乃 フィードボット)

AIを活用したフィード要約・Mastodon投稿ボット

## セットアップ

### Docker環境（推奨）

1. 設定ファイルの準備:
```bash
copy .env.example .env
copy feeds.example.json feeds.json
copy ai_config.example.json data\ai_config.json
```

2. 環境変数の設定:
`.env` ファイルを編集してAPIキー等を設定
- `AI_CONFIG_FILE`: AIフォールバック設定ファイル（デフォルト: `data/ai_config.json`）
- `OPENROUTER_API_KEY`, `OPENAI_API_KEY`: AI設定から参照するAPIキー
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
- AI要約生成（OpenAI互換Chat Completions／Responses API）
- プロバイダとモデルをまたいだ設定順フォールバック
- Mastodonへの自動投稿
- 既読記事管理

## ドキュメント

- `README.md`: 機能、設定、セットアップ、実行方法
- `FLOWCHART.md`: 主要な処理フローと設計判断
- `AGENTS.md`: 自動コーディングエージェントおよびAI支援開発ツール向けの、ベンダー非依存な開発ガイド

コントリビューション時の実装方針、安全上の制約、Dockerでの検証方法は `AGENTS.md` を参照してください。

## 設定ファイル構成

- `.env`: 環境変数（APIキー、認証情報など）
- `config.py`: メイン設定ファイル（汎用的な設定読み込み処理、Git管理対象）
- `feeds.json`: フィード設定専用ファイル（監視するRSSフィードの一覧、JSON形式）
- `data/ai_config.json`: AIプロバイダ、モデル、API形式、フォールバック順
- 個人設定ファイルには `.example` 版があり、これをコピーして使用します
- `.env`, `feeds.json`, `data/` は個人設定または実行データのため .gitignore で管理対象外になっています

## AIフォールバック設定

data/ai_config.json の providers に接続先を定義し、fallbacks へ試行順に候補を列挙します。同じプロバイダの異なるモデルを複数回指定することもできます。モデル、接続先、API形式、生成パラメータ、リトライ設定はこのファイルだけで管理し、`.env` にはAPIキーなどの秘密情報だけを設定します。AI設定ファイルが存在しない場合、アプリケーションは起動時にエラーになります。

~~~json
{
  "providers": {
    "openai": {
      "base_url": "https://api.openai.com/v1",
      "auth": {
        "type": "bearer",
        "api_key_env": "OPENAI_API_KEY"
      }
    },
    "ollama": {
      "base_url": "http://host.docker.internal:11434/v1",
      "auth": {"type": "none"}
    }
  },
  "fallbacks": [
    {
      "id": "openai-primary",
      "provider": "openai",
      "model": "gpt-5-nano",
      "api": "responses",
      "parameters": {
        "max_output_tokens": 8000,
        "store": false
      }
    },
    {
      "id": "ollama-local",
      "provider": "ollama",
      "model": "qwen3.5:2b",
      "api": "responses",
      "parameters": {
        "max_output_tokens": 8000,
        "temperature": 0.3
      }
    }
  ]
}
~~~

- api: responses または chat_completions
- base_url: /v1 までを指定。API形式に応じたパスは自動追加
- parameters: 各API・モデルへ渡す追加パラメータ
- retry: 全体または候補ごとの timeout、max_attempts、base_delay
- auth.type: bearer、header、none

対象はOpenAI互換形式を提供するプロバイダです。OllamaのResponses APIは0.13.3以降が必要です。Dockerからホスト上のOllamaへ接続する例では host.docker.internal を使用しています。ローカルで直接実行する場合は localhost へ変更してください。

## 設定可能項目

- フィード取得間隔
- フィード取得タイムアウト（`FEED_FETCH_TIMEOUT`: サーバー無応答時にスキップするまでの秒数、デフォルト: 30秒）
- フィード取得User-Agent（`FEED_USER_AGENT`: WAF等による遮断を軽減するためのUser-Agent設定）
- 記事の保持期間
- AI要約プロンプト
- AIプロバイダ、モデル、API形式、フォールバック順
- Mastodon投稿設定
  - **公開範囲**: 投稿の公開レベル（public: 公開, unlisted: 未収載, private: フォロワーのみ, direct: ダイレクト）
- **時間帯制限**: 投稿を行わない時間帯の設定（生活時間帯を考慮）
  - `ENABLE_QUIET_HOURS`: 時間帯制限の有効/無効
  - `QUIET_HOURS_START`: 投稿禁止開始時刻（24時間形式）
  - `QUIET_HOURS_END`: 投稿禁止終了時刻（24時間形式）
- **ウェイト設定**: 連続投稿を防ぐための待機時間
  - `POST_WAIT`: 投稿処理間の待機時間（秒、デフォルト: 60秒）
- **ログ設定**: コンソール(docker logs)とファイルで異なるレベルを設定可能
  - `LOG_LEVEL`: コンソールログレベル（デフォルト: INFO）
  - `LOG_TO_FILE`: ファイルログの有効/無効（デフォルト: true）
  - `LOG_FILE_LEVEL`: ファイルログレベル（デフォルト: DEBUG）
  - `LOG_FILE_RETENTION_DAYS`: ログファイル保持日数（デフォルト: 14日）

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
