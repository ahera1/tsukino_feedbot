from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import logging
import time

import requests


logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """AI APIサービスのエラー（フォールバック理由の記録用）。"""

    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    MODEL_NOT_FOUND = "model_not_found"
    CREDIT_EXHAUSTED = "credit_exhausted"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    TOKEN_ERROR = "token_error"
    RESPONSE_ERROR = "response_error"
    UNKNOWN = "unknown"

    CATEGORY_LABELS = {
        RATE_LIMIT: "レート制限",
        AUTH_ERROR: "認証エラー",
        MODEL_NOT_FOUND: "モデル未検出",
        CREDIT_EXHAUSTED: "クレジット不足",
        SERVER_ERROR: "サーバーエラー",
        TIMEOUT: "タイムアウト",
        CONNECTION_ERROR: "接続エラー",
        TOKEN_ERROR: "トークンエラー",
        RESPONSE_ERROR: "レスポンスエラー",
        UNKNOWN: "不明なエラー",
    }

    def __init__(
        self,
        message: str,
        service_name: str = "",
        error_category: str = UNKNOWN,
        status_code: Optional[int] = None,
        response_body: Optional[dict] = None,
    ):
        self.service_name = service_name
        self.error_category = error_category
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)

    @property
    def category_label(self) -> str:
        return self.CATEGORY_LABELS.get(self.error_category, "不明なエラー")


@dataclass
class AIConfig:
    """解決済みのフォールバック候補設定。"""

    id: str
    provider: str
    model: str
    api_type: str
    base_url: str
    api_key: Optional[str] = None
    auth_type: str = "bearer"
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer"
    headers: Dict[str, str] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    system_prompt: str = ""
    timeout: int = 60
    max_attempts: int = 3
    retry_delay: int = 10

    @property
    def name(self) -> str:
        """旧コードとの互換用表示名。"""
        return self.id


class AIServiceBase(ABC):
    """OpenAI互換API実装の共通基底クラス。"""

    endpoint_path = ""

    def __init__(self, config: AIConfig):
        self.config = config
        self.name = config.id

    @property
    def endpoint_url(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/{self.endpoint_path.lstrip('/')}"

    @abstractmethod
    def generate_summary(self, title: str, content: str, prompt_template: str) -> str:
        """記事の要約を生成する。"""
        raise NotImplementedError

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", **self.config.headers}
        if self.config.auth_type == "none":
            return headers
        if not self.config.api_key:
            raise AIServiceError(
                f"{self.name}: APIキーが設定されていません",
                service_name=self.name,
                error_category=AIServiceError.AUTH_ERROR,
            )

        value = self.config.api_key
        if self.config.auth_prefix:
            value = f"{self.config.auth_prefix} {value}"
        headers[self.config.auth_header] = value
        return headers

    def _post_json(self, payload: dict) -> dict:
        try:
            response = self._make_request_with_retry(
                "POST",
                self.endpoint_url,
                headers=self._build_headers(),
                json=payload,
            )
            try:
                result = response.json()
            except ValueError as error:
                raise AIServiceError(
                    f"{self.name}: JSONレスポンスを解析できません",
                    service_name=self.name,
                    error_category=AIServiceError.RESPONSE_ERROR,
                ) from error
            if not isinstance(result, dict):
                raise AIServiceError(
                    f"{self.name}: レスポンスのルートがオブジェクトではありません",
                    service_name=self.name,
                    error_category=AIServiceError.RESPONSE_ERROR,
                )
            return result
        except AIServiceError as error:
            token_error = None
            if error.status_code is not None:
                token_error = self._detect_token_related_errors(
                    error.response_body or {}, error.status_code
                )
            if token_error:
                raise AIServiceError(
                    f"{self.name}: {token_error}",
                    service_name=self.name,
                    error_category=AIServiceError.TOKEN_ERROR,
                    status_code=error.status_code,
                ) from error
            raise
        except Exception as error:
            raise AIServiceError(
                f"{self.name}: {error}",
                service_name=self.name,
                error_category=AIServiceError.UNKNOWN,
            ) from error

    def _make_request_with_retry(
        self, method: str, url: str, **kwargs
    ) -> requests.Response:
        """指数バックオフ付きHTTPリクエスト。"""
        kwargs.setdefault("timeout", self.config.timeout)
        last_exception: Optional[Exception] = None

        for attempt in range(self.config.max_attempts):
            try:
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.Timeout as error:
                last_exception = error
                logger.warning(
                    "%s: タイムアウト (試行 %d/%d)",
                    self.name,
                    attempt + 1,
                    self.config.max_attempts,
                )
            except requests.exceptions.HTTPError as error:
                status_code = error.response.status_code if error.response is not None else None
                if status_code in (408, 429, 500, 502, 503, 504):
                    last_exception = error
                    logger.warning(
                        "%s: HTTPエラー %s (試行 %d/%d)",
                        self.name,
                        status_code,
                        attempt + 1,
                        self.config.max_attempts,
                    )
                else:
                    raise self._classify_http_error(error)
            except requests.exceptions.ConnectionError as error:
                last_exception = error
                logger.warning(
                    "%s: 接続エラー (試行 %d/%d)",
                    self.name,
                    attempt + 1,
                    self.config.max_attempts,
                )
            except requests.exceptions.RequestException as error:
                raise AIServiceError(
                    f"{self.name}: HTTPリクエストエラー",
                    service_name=self.name,
                    error_category=AIServiceError.CONNECTION_ERROR,
                ) from error

            if attempt < self.config.max_attempts - 1:
                wait_time = self.config.retry_delay * (2 ** attempt)
                logger.info("%s: %d秒後にリトライします...", self.name, wait_time)
                time.sleep(wait_time)

        raise self._classify_last_error(last_exception)

    def _classify_http_error(
        self, error: requests.exceptions.HTTPError
    ) -> AIServiceError:
        status_code = error.response.status_code if error.response is not None else None
        response_body = None
        try:
            if error.response is not None:
                response_body = error.response.json()
        except (ValueError, AttributeError):
            pass

        category = AIServiceError.UNKNOWN
        if status_code == 429:
            category = AIServiceError.RATE_LIMIT
        elif status_code in (401, 403):
            category = AIServiceError.AUTH_ERROR
        elif status_code == 404:
            category = AIServiceError.MODEL_NOT_FOUND
        elif status_code == 402:
            category = AIServiceError.CREDIT_EXHAUSTED
        elif status_code and 500 <= status_code < 600:
            category = AIServiceError.SERVER_ERROR

        label = AIServiceError.CATEGORY_LABELS.get(category, "不明なエラー")
        return AIServiceError(
            f"{self.name}: {label} (HTTP {status_code})",
            service_name=self.name,
            error_category=category,
            status_code=status_code,
            response_body=response_body,
        )

    def _classify_last_error(self, error: Optional[Exception]) -> AIServiceError:
        if isinstance(error, requests.exceptions.Timeout):
            return AIServiceError(
                f"{self.name}: タイムアウト (全{self.config.max_attempts}回失敗)",
                service_name=self.name,
                error_category=AIServiceError.TIMEOUT,
            )
        if isinstance(error, requests.exceptions.HTTPError):
            return self._classify_http_error(error)
        if isinstance(error, requests.exceptions.ConnectionError):
            return AIServiceError(
                f"{self.name}: 接続エラー (全{self.config.max_attempts}回失敗)",
                service_name=self.name,
                error_category=AIServiceError.CONNECTION_ERROR,
            )
        return AIServiceError(
            f"{self.name}: 不明なHTTPエラー",
            service_name=self.name,
            error_category=AIServiceError.UNKNOWN,
        )

    def _log_usage(self, response_data: dict, output_limit: Optional[int]) -> None:
        usage = response_data.get("usage")
        if not isinstance(usage, dict):
            return

        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens"))
        total_tokens = usage.get("total_tokens")
        logger.info(
            "%s: トークン使用量 - 入力: %s, 出力: %s, 合計: %s",
            self.name,
            input_tokens,
            output_tokens,
            total_tokens,
        )

        if (
            isinstance(output_limit, int)
            and not isinstance(output_limit, bool)
            and output_limit > 0
            and isinstance(output_tokens, int)
        ):
            if output_tokens >= output_limit:
                logger.error(
                    "%s: 出力トークン上限到達 - %d/%d",
                    self.name,
                    output_tokens,
                    output_limit,
                )
            elif output_tokens >= output_limit * 0.95:
                logger.warning(
                    "%s: 出力トークン使用量警告 - %d/%d",
                    self.name,
                    output_tokens,
                    output_limit,
                )

    def _detect_token_related_errors(
        self, error_response: dict, status_code: int
    ) -> Optional[str]:
        error_text = str(error_response).lower()
        token_error_indicators = (
            "maximum context length",
            "token limit",
            "too many tokens",
            "context length exceeded",
            "input too long",
            "prompt too long",
            "max_tokens",
            "max_output_tokens",
            "token limit exceeded",
        )
        for indicator in token_error_indicators:
            if indicator in error_text:
                return f"トークン関連エラー: {indicator}"
        if status_code == 413:
            return "トークン関連エラー: リクエストが大きすぎます"
        return None

    def is_available(self) -> bool:
        """事前通信は行わず、実リクエスト結果で利用可否を判断する。"""
        return True
