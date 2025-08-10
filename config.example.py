# 設定ファイル例（Docker専用）
# このファイルをconfig.pyにコピーして使用してください

import os

# 環境変数から設定を読み込み
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")

# Mastodon設定
MASTODON_INSTANCE_URL = os.getenv("MASTODON_INSTANCE_URL")
MASTODON_ACCESS_TOKEN = os.getenv("MASTODON_ACCESS_TOKEN")

# フィード設定
FEED_URLS = [
    {
        "url": "https://zenn.dev/feed",
        "name": "Zenn"
    },
    {
        "url": "https://qiita.com/popular-items/feed",
        "name": "Qiita人気記事"
    },
    # 環境変数からフィードURLを追加する例
    # {
    #     "url": os.getenv("ADDITIONAL_FEED_URL"),
    #     "name": os.getenv("ADDITIONAL_FEED_NAME")
    # }
]

# 動作設定
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES"))
ARTICLE_RETENTION_DAYS = int(os.getenv("ARTICLE_RETENTION_DAYS"))
READ_RECORD_RETENTION_DAYS = int(os.getenv("READ_RECORD_RETENTION_DAYS"))

# 時間帯制限設定
ENABLE_QUIET_HOURS = os.getenv("ENABLE_QUIET_HOURS", "false").lower() == "true"
QUIET_HOURS_START = int(os.getenv("QUIET_HOURS_START", "23"))
QUIET_HOURS_END = int(os.getenv("QUIET_HOURS_END", "7"))

# AI要約プロンプト
SUMMARY_PROMPT = os.getenv("SUMMARY_PROMPT").replace("\\n", "\n")

# Mastodon投稿設定
POST_TEMPLATE = os.getenv("POST_TEMPLATE", "").replace("\\n", "\n")

# ログ設定
LOG_LEVEL = os.getenv("LOG_LEVEL")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
