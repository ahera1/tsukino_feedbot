# 設定ファイル（Docker専用）
# 環境変数から設定を読み込みます

import os
import json
import logging

_config_logger = logging.getLogger(__name__)

# フィード設定をJSONファイルから読み込み
def load_feed_urls():
    """feeds.jsonからフィード設定を読み込む"""
    try:
        with open('feeds.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        _config_logger.warning("フィード設定ファイル feeds.json が見つかりません。feeds.example.json をコピーして使用してください。")
        return []
    except json.JSONDecodeError as e:
        _config_logger.error(f"feeds.json の形式が正しくありません: {e}")
        return []

FEED_URLS = load_feed_urls()

# AI統合プロンプト設定
def _decode_env_escapes(value: str) -> str:
    """環境変数値のエスケープシーケンス（\\n等）を実際の文字に変換"""
    return value.replace("\\n", "\n").replace("\\t", "\t")

# システムプロンプト（AI全体で統一使用）
_raw_system_prompt = os.getenv("AI_SYSTEM_PROMPT_TEMPLATE", "")
AI_SYSTEM_PROMPT_TEMPLATE = _decode_env_escapes(
    os.getenv(
        "AI_SYSTEM_PROMPT_TEMPLATE",
        "あなたは技術ニュースを要約する専門家です。以下のルールに従って要約を作成してください：\n"
        "- 140文字以内で簡潔にまとめる\n"
        "- 重要な技術的ポイントを優先する\n"
        "- 専門用語は適切に使用する\n"
        "- 客観的で事実ベースの内容にする\n"
        "- 絵文字は使用しない"
    )
)

# ユーザープロンプトテンプレート（記事本文と最小限の指示）
_raw_user_prompt = os.getenv("AI_USER_PROMPT_TEMPLATE", "")
AI_USER_PROMPT_TEMPLATE = _decode_env_escapes(
    os.getenv(
        "AI_USER_PROMPT_TEMPLATE",
        "以下の記事を要約してください：\n\nタイトル: {title}\n内容: {content}"
    )
)

_config_logger.debug(f"システムプロンプト (raw): {repr(_raw_system_prompt)[:300]}")
_config_logger.debug(f"システムプロンプト (processed): {repr(AI_SYSTEM_PROMPT_TEMPLATE)[:300]}")
_config_logger.debug(f"ユーザープロンプト (raw): {repr(_raw_user_prompt)[:300]}")
_config_logger.debug(f"ユーザープロンプト (processed): {repr(AI_USER_PROMPT_TEMPLATE)[:300]}")

# AIプロバイダ、モデル、API形式、フォールバック順を定義する設定ファイル
AI_CONFIG_FILE = os.getenv("AI_CONFIG_FILE", "data/ai_config.json")

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

# Mastodon投稿設定
POST_TEMPLATE = os.getenv("POST_TEMPLATE", "").replace("\\n", "\n")
POST_VISIBILITY = os.getenv("POST_VISIBILITY", "direct")  # public, unlisted, private, direct

# ウェイト設定（秒）
POST_WAIT = int(os.getenv("POST_WAIT", "60"))  # 投稿処理間の待機時間

# 記事完全性チェック設定
MIN_TITLE_LENGTH = int(os.getenv("MIN_TITLE_LENGTH", "3"))  # 最小タイトル長
MIN_CONTENT_LENGTH = int(os.getenv("MIN_CONTENT_LENGTH", "10"))  # 最小本文長

# 記事遅延処理設定
FEED_INITIAL_DELAY_MINUTES = int(os.getenv("FEED_INITIAL_DELAY_MINUTES", "5"))  # 新着記事の初期遅延時間（分）

# フィード取得タイムアウト設定
FEED_FETCH_TIMEOUT = int(os.getenv("FEED_FETCH_TIMEOUT", "30"))  # フィード取得のHTTPタイムアウト（秒）

# フィード取得User-Agent設定
FEED_USER_AGENT = os.getenv("FEED_USER_AGENT", "TsukinoFeedBot/1.0 (+https://github.com/feedbot)")

# ログ設定
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"
LOG_FILE_LEVEL = os.getenv("LOG_FILE_LEVEL", "DEBUG")
LOG_FILE_RETENTION_DAYS = int(os.getenv("LOG_FILE_RETENTION_DAYS", "14"))
