# 設定ファイル（Docker専用）
# 環境変数から設定を読み込みます

import os
import json

# フィード設定をJSONファイルから読み込み
def load_feed_urls():
    """feeds.jsonからフィード設定を読み込む"""
    try:
        with open('feeds.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("警告: フィード設定ファイル feeds.json が見つかりません。")
        print("feeds.example.json を feeds.json にコピーして使用してください。")
        return []
    except json.JSONDecodeError as e:
        print(f"エラー: feeds.json の形式が正しくありません: {e}")
        return []

FEED_URLS = load_feed_urls()

# 環境変数から設定を読み込み
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")

# Mastodon設定
MASTODON_INSTANCE_URL = os.getenv("MASTODON_INSTANCE_URL")
MASTODON_ACCESS_TOKEN = os.getenv("MASTODON_ACCESS_TOKEN")

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
POST_VISIBILITY = os.getenv("POST_VISIBILITY", "direct")  # public, unlisted, private, direct

# ウェイト設定（秒）
ARTICLE_PROCESS_WAIT = int(os.getenv("ARTICLE_PROCESS_WAIT", "5"))  # 記事処理間の待機時間
MASTODON_POST_WAIT = int(os.getenv("MASTODON_POST_WAIT", "10"))     # Mastodon投稿間の待機時間

# ログ設定
LOG_LEVEL = os.getenv("LOG_LEVEL")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
