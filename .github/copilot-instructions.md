# GitHub Copilot Instructions

## プロジェクト概要
AIを活用したフィード要約・Mastodon投稿ボット - Python

## 実装方針

### シンプルさを重視
- 複雑な設計パターンは不要
- 実用最小限の機能実装
- 実績のあるライブラリを積極活用

### コーディングスタイル
- 関数は短く単一責任に
- わかりやすい変数名
- 必要最小限のコメント
- dataclassを活用してデータ構造を明確に

### データ管理
- JSONファイルで永続化
- dataclassで投稿を管理
- IDは記事URLベースのハッシュで自動生成

### エラーハンドリング
- 基本的なtry-exceptのみ
- API呼び出しとファイル操作のエラー処理
- ネットワークエラーに対する基本的な対応

## ファイル構成
```
main.py              - CLIメニューと主要ロジック
models.py            - FeedItem, FeedSource dataclass定義
storage.py           - JSON読み書き機能
feed_reader.py       - RSSフィード取得
ai_manager.py        - AI APIマネージャー（複数API対応・フォールバック機能）
ai_base.py           - AI API基底クラス
ai_openrouter.py     - OpenRouter API連携
ai_openai.py         - OpenAI API連携
ai_ollama.py         - Ollama API連携（ローカルLLM対応）
ai_service.py        - 旧AI APIサービス（互換性維持）
mastodon_service.py  - Mastodon API連携
config.py            - 設定ファイル（環境変数読み込み）
.env.example         - 環境変数設定例
feeds.example.json   - フィード設定例
```

## 機能一覧
1. RSSフィードの定期監視
2. AI要約生成（複数AI API対応・自動フォールバック機能）
   - OpenRouter API（プライマリ）
   - OpenAI API（セカンダリ）
   - Ollama API（ローカルLLM、ターシャリ）
3. Mastodonへの自動投稿
4. 既読記事管理（読み取り日時付き）
5. 古い記事の自動削除（段階的クリーンアップ）
6. 時間帯制限機能（投稿を行わない時間帯の設定）
7. Docker対応（デーモンモード・ワンショット実行対応）
8. 設定の外部ファイル化（JSON・環境変数）

## 使用ライブラリ
- requests - HTTP通信
- feedparser - RSSパース
- Mastodon.py - Mastodon API
- python-dotenv - 環境変数（オプション）

## 設定管理
- 環境変数で設定を管理（.envファイル使用）
- .env.example を .env にコピーして使用
- APIキーやアクセストークンは.envファイルで管理
- フィード設定は feeds.json で管理（feeds.example.json をコピー）
- 汎用的な設定処理は config.py で管理（Git管理対象）
- 個人設定ファイル（.env と feeds.json）は .gitignore で除外

## 動作設定
- フィード取得間隔は設定可能（デフォルト60分）
- 記事保持期間は設定可能（デフォルト7日）
- 読み取り記録のみの保持期間（デフォルト3日、JSONファイル肥大化防止）
- AI要約プロンプトは設定ファイルでカスタマイズ可能
- 時間帯制限機能（生活時間帯を考慮した投稿禁止時間帯の設定）
- ウェイト設定（連続投稿を防ぐための待機時間設定）
