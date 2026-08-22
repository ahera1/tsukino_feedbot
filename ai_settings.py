from pathlib import Path
from typing import Mapping, Optional
from urllib.parse import urlparse
import json
import logging
import os

from ai_base import AIConfig


logger = logging.getLogger(__name__)

SUPPORTED_API_TYPES = {"chat_completions", "responses"}
SUPPORTED_AUTH_TYPES = {"bearer", "header", "none"}
RESERVED_PARAMETERS = {
    "chat_completions": {"model", "messages", "stream"},
    "responses": {"model", "input", "instructions", "stream"},
}
def load_ai_configs(
    config_file: str,
    system_prompt: str,
    environ: Optional[Mapping[str, str]] = None,
) -> list[AIConfig]:
    """JSON設定ファイルを読み込む。"""
    env = environ if environ is not None else os.environ
    path = Path(config_file)
    if not path.is_file():
        raise ValueError(
            f"AI設定ファイル {path} が見つかりません。"
            "ai_config.example.jsonをコピーして作成してください"
        )
    try:
        with path.open("r", encoding="utf-8") as file:
            document = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(f"AI設定ファイル {path} のJSON形式が不正です: {error}") from error
    logger.info("AI設定ファイルを使用します: %s", path)
    return load_ai_configs_from_dict(document, system_prompt, env)


def load_ai_configs_from_dict(
    document: dict,
    system_prompt: str,
    environ: Optional[Mapping[str, str]] = None,
) -> list[AIConfig]:
    env = environ if environ is not None else os.environ
    if not isinstance(document, dict):
        raise ValueError("AI設定のルートはオブジェクトである必要があります")

    providers = document.get("providers")
    fallbacks = document.get("fallbacks")
    retry_defaults = document.get("retry", {})
    if not isinstance(providers, dict) or not providers:
        raise ValueError("providersには1件以上のプロバイダが必要です")
    if not isinstance(fallbacks, list) or not fallbacks:
        raise ValueError("fallbacksには1件以上の候補が必要です")
    if not isinstance(retry_defaults, dict):
        raise ValueError("retryはオブジェクトである必要があります")

    provider_settings = {
        name: _parse_provider(name, value, env)
        for name, value in providers.items()
    }
    ids = set()
    configs = []
    for fallback in fallbacks:
        if not isinstance(fallback, dict):
            raise ValueError("fallbacksの各要素はオブジェクトである必要があります")
        target_id = _required_string(fallback, "id")
        if target_id in ids:
            raise ValueError(f"フォールバック候補IDが重複しています: {target_id}")
        ids.add(target_id)

        provider_name = _required_string(fallback, "provider")
        if provider_name not in provider_settings:
            raise ValueError(
                f"{target_id}: 未定義のプロバイダを参照しています: {provider_name}"
            )
        provider = provider_settings[provider_name]
        if provider["disabled_reason"]:
            logger.warning(
                "%sをスキップします: %s",
                target_id,
                provider["disabled_reason"],
            )
            continue

        api_type = _required_string(fallback, "api")
        if api_type not in SUPPORTED_API_TYPES:
            raise ValueError(f"{target_id}: 未対応のAPI形式です: {api_type}")
        parameters = fallback.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ValueError(f"{target_id}: parametersはオブジェクトである必要があります")
        reserved = RESERVED_PARAMETERS[api_type].intersection(parameters)
        if reserved:
            names = ", ".join(sorted(reserved))
            raise ValueError(f"{target_id}: parametersで予約済み項目は指定できません: {names}")

        retry_override = fallback.get("retry", {})
        if not isinstance(retry_override, dict):
            raise ValueError(f"{target_id}: retryはオブジェクトである必要があります")
        retry = {**retry_defaults, **retry_override}
        configs.append(
            AIConfig(
                id=target_id,
                provider=provider_name,
                model=_required_string(fallback, "model"),
                api_type=api_type,
                base_url=provider["base_url"],
                api_key=provider["api_key"],
                auth_type=provider["auth_type"],
                auth_header=provider["auth_header"],
                auth_prefix=provider["auth_prefix"],
                headers=provider["headers"],
                parameters=dict(parameters),
                system_prompt=system_prompt,
                timeout=_positive_int(retry, "timeout", 60),
                max_attempts=_positive_int(retry, "max_attempts", 3),
                retry_delay=_non_negative_int(retry, "base_delay", 10),
            )
        )

    if not configs:
        raise ValueError("利用可能なAIフォールバック候補がありません")
    return configs


def _parse_provider(name: str, value: dict, env: Mapping[str, str]) -> dict:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("プロバイダ名は空でない文字列である必要があります")
    if not isinstance(value, dict):
        raise ValueError(f"{name}: プロバイダ設定はオブジェクトである必要があります")

    base_url = _required_string(value, "base_url").rstrip("/")
    _validate_base_url(base_url, name)
    headers = value.get("headers", {})
    if not isinstance(headers, dict) or not all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in headers.items()
    ):
        raise ValueError(f"{name}: headersは文字列のキーと値で指定してください")

    auth = value.get("auth", {"type": "none"})
    if not isinstance(auth, dict):
        raise ValueError(f"{name}: authはオブジェクトである必要があります")
    auth_type = auth.get("type", "none")
    if auth_type not in SUPPORTED_AUTH_TYPES:
        raise ValueError(f"{name}: 未対応の認証方式です: {auth_type}")

    api_key = None
    disabled_reason = None
    auth_header = "Authorization"
    auth_prefix = "Bearer"
    if auth_type != "none":
        api_key_env = _required_string(auth, "api_key_env")
        api_key = env.get(api_key_env)
        if not api_key:
            disabled_reason = f"環境変数 {api_key_env} が設定されていません"
        if auth_type == "header":
            auth_header = _required_string(auth, "header")
            auth_prefix = auth.get("prefix", "")
            if not isinstance(auth_prefix, str):
                raise ValueError(f"{name}: auth.prefixは文字列で指定してください")

    return {
        "base_url": base_url,
        "api_key": api_key,
        "auth_type": auth_type,
        "auth_header": auth_header,
        "auth_prefix": auth_prefix,
        "headers": dict(headers),
        "disabled_reason": disabled_reason,
    }


def _required_string(value: dict, key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"{key}には空でない文字列が必要です")
    return result.strip()


def _positive_int(value: dict, key: str, default: int) -> int:
    result = value.get(key, default)
    if isinstance(result, bool) or not isinstance(result, int) or result <= 0:
        raise ValueError(f"{key}には1以上の整数が必要です")
    return result


def _non_negative_int(value: dict, key: str, default: int) -> int:
    result = value.get(key, default)
    if isinstance(result, bool) or not isinstance(result, int) or result < 0:
        raise ValueError(f"{key}には0以上の整数が必要です")
    return result


def _validate_base_url(base_url: str, name: str) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{name}: base_urlはhttpまたはhttpsのURLで指定してください")
