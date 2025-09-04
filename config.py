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

def get_optional_int(env_var: str, default: str = None) -> int:
    """環境変数から整数を取得。空文字の場合はNoneを返す"""
    value = os.getenv(env_var, default or "")
    if not value or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None

def get_optional_float(env_var: str, default: str = None) -> float:
    """環境変数から浮動小数点数を取得。空文字の場合はNoneを返す"""
    value = os.getenv(env_var, default or "")
    if not value or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None

# AI統合プロンプト設定
# システムプロンプト（AI全体で統一使用）
AI_SYSTEM_PROMPT_TEMPLATE = os.getenv(
    "AI_SYSTEM_PROMPT_TEMPLATE",
    "あなたは技術ニュースを要約する専門家です。以下のルールに従って要約を作成してください：\n"
    "- 140文字以内で簡潔にまとめる\n"
    "- 重要な技術的ポイントを優先する\n"
    "- 専門用語は適切に使用する\n"
    "- 客観的で事実ベースの内容にする\n"
    "- 絵文字は使用しない"
).replace("\\n", "\n")

# ユーザープロンプトテンプレート（記事本文と最小限の指示）
AI_USER_PROMPT_TEMPLATE = os.getenv(
    "AI_USER_PROMPT_TEMPLATE", 
    "以下の記事を要約してください：\n\nタイトル: {title}\n内容: {content}"
).replace("\\n", "\n")

# 後方互換性のため SUMMARY_PROMPT も維持
SUMMARY_PROMPT = AI_USER_PROMPT_TEMPLATE

# AI API設定（優先順位順）
AI_CONFIGS = [
    {
        "name": "OpenRouter",
        "api_key": None,  # .envファイルで設定
        "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b"),
        "max_tokens": get_optional_int("AI_MAX_TOKENS", "8000"),  # モデル仕様に合わせて大幅増加
        "temperature": get_optional_float("AI_TEMPERATURE", "0.3"),
        "timeout": int(os.getenv("AI_TIMEOUT", "120")),  # 処理時間も延長
        "max_retries": int(os.getenv("AI_MAX_RETRIES", "3")),
        "retry_delay": int(os.getenv("AI_RETRY_DELAY", "10")),
        "extra_params": {
            "system_prompt": AI_SYSTEM_PROMPT_TEMPLATE  # 統合システムプロンプト使用
        }
    },
    {
        "name": "OpenAI",
        "api_key": None,  # .envファイルで設定
        "model": os.getenv("OPENAI_MODEL", "gpt-5-nano"),
        "max_tokens": get_optional_int("AI_MAX_TOKENS", "8000"),  # モデル仕様に合わせて大幅増加
        "temperature": get_optional_float("AI_TEMPERATURE", "0.3"),
        "timeout": int(os.getenv("AI_TIMEOUT", "120")),  # 処理時間も延長
        "max_retries": int(os.getenv("AI_MAX_RETRIES", "3")),
        "retry_delay": int(os.getenv("AI_RETRY_DELAY", "10")),
        "extra_params": {
            "system_prompt": AI_SYSTEM_PROMPT_TEMPLATE  # 統合システムプロンプト使用
        }
    },
    {
        "name": "Ollama",
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/chat"),
        "model": os.getenv("OLLAMA_MODEL", "llama2"),
        "max_tokens": get_optional_int("AI_MAX_TOKENS", "8000"),  # モデル仕様に合わせて大幅増加
        "temperature": get_optional_float("AI_TEMPERATURE", "0.3"),
        "timeout": int(os.getenv("AI_TIMEOUT", "180")),  # Ollamaはさらに長めに調整
        "max_retries": int(os.getenv("AI_MAX_RETRIES", "3")),
        "retry_delay": int(os.getenv("AI_RETRY_DELAY", "10")),
        "extra_params": {
            "system_prompt": AI_SYSTEM_PROMPT_TEMPLATE  # 統合システムプロンプト使用
        }
    }
]

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

# AI統合プロンプト設定
# システムプロンプト（AI全体で統一使用）
AI_SYSTEM_PROMPT_TEMPLATE = os.getenv(
    "AI_SYSTEM_PROMPT_TEMPLATE",
    "あなたは技術ニュースを要約する専門家です。以下のルールに従って要約を作成してください：\n"
    "- 140文字以内で簡潔にまとめる\n"
    "- 重要な技術的ポイントを優先する\n"
    "- 専門用語は適切に使用する\n"
    "- 客観的で事実ベースの内容にする\n"
    "- 絵文字は使用しない"
).replace("\\n", "\n")

# ユーザープロンプトテンプレート（記事本文と最小限の指示）
AI_USER_PROMPT_TEMPLATE = os.getenv(
    "AI_USER_PROMPT_TEMPLATE", 
    "以下の記事を要約してください：\n\nタイトル: {title}\n内容: {content}"
).replace("\\n", "\n")

# 後方互換性のため SUMMARY_PROMPT も維持
SUMMARY_PROMPT = AI_USER_PROMPT_TEMPLATE

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

# ログ設定
LOG_LEVEL = os.getenv("LOG_LEVEL")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
