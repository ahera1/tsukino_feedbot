from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging
import time
import requests

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """AI APIサービスのエラー（フォールバック理由の記録用）"""

    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    MODEL_NOT_FOUND = "model_not_found"
    CREDIT_EXHAUSTED = "credit_exhausted"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    TOKEN_ERROR = "token_error"
    UNKNOWN = "unknown"

    CATEGORY_LABELS = {
        "rate_limit": "レート制限",
        "auth_error": "認証エラー",
        "model_not_found": "モデル未検出",
        "credit_exhausted": "クレジット不足",
        "server_error": "サーバーエラー",
        "timeout": "タイムアウト",
        "connection_error": "接続エラー",
        "token_error": "トークンエラー",
        "unknown": "不明なエラー",
    }

    def __init__(self, message: str, service_name: str = "", error_category: str = "unknown",
                 status_code: int = None, response_body: dict = None):
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
    """AI APIの設定"""
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None  # Noneの場合はAPIに渡さない
    temperature: Optional[float] = None  # Noneの場合はAPIに渡さない
    timeout: int = 60  # タイムアウト値（秒）
    max_retries: int = 3  # 最大リトライ回数
    retry_delay: int = 10  # リトライ間の待機時間（秒）
    extra_params: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}

class AIServiceBase(ABC):
    """AI APIの基底クラス"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.name = config.name
    
    @abstractmethod
    def generate_summary(self, title: str, content: str, prompt_template: str) -> str:
        """記事の要約を生成"""
        pass
    
    def _make_request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """リトライ機能付きHTTPリクエスト"""
        kwargs.setdefault('timeout', self.config.timeout)
        
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"{self.name}: タイムアウト (試行 {attempt + 1}/{self.config.max_retries})")
                
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else None
                if status_code in [408, 429, 500, 502, 503, 504]:
                    last_exception = e
                    logger.warning(f"{self.name}: HTTPエラー {status_code} (試行 {attempt + 1}/{self.config.max_retries})")
                else:
                    raise self._classify_http_error(e)
                    
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                logger.warning(f"{self.name}: 接続エラー (試行 {attempt + 1}/{self.config.max_retries})")
                
            except AIServiceError:
                raise
                
            except Exception as e:
                raise e
            
            if attempt < self.config.max_retries - 1:
                wait_time = self.config.retry_delay * (2 ** attempt)
                logger.info(f"{self.name}: {wait_time}秒後にリトライします...")
                time.sleep(wait_time)
        
        raise self._classify_last_error(last_exception)
    
    def _classify_http_error(self, error: requests.exceptions.HTTPError) -> AIServiceError:
        """HTTPエラーをAIServiceErrorに分類"""
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
            response_body=response_body
        )
    
    def _classify_last_error(self, error: Exception) -> AIServiceError:
        """リトライ後の最終エラーをAIServiceErrorに分類"""
        if isinstance(error, AIServiceError):
            return error
        if isinstance(error, requests.exceptions.Timeout):
            return AIServiceError(
                f"{self.name}: タイムアウト (全{self.config.max_retries}回リトライ失敗)",
                service_name=self.name, error_category=AIServiceError.TIMEOUT)
        if isinstance(error, requests.exceptions.HTTPError):
            return self._classify_http_error(error)
        if isinstance(error, requests.exceptions.ConnectionError):
            return AIServiceError(
                f"{self.name}: 接続エラー (全{self.config.max_retries}回リトライ失敗)",
                service_name=self.name, error_category=AIServiceError.CONNECTION_ERROR)
        return AIServiceError(
            f"{self.name}: {str(error)}",
            service_name=self.name, error_category=AIServiceError.UNKNOWN)
    
    def _analyze_response_usage(self, response_data: dict) -> dict:
        """レスポンスからトークン使用量を分析"""
        usage_info = {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "token_limit_reached": False,
            "token_warning": False
        }
        
        # OpenAI形式のusageフィールドをチェック
        if "usage" in response_data:
            usage = response_data["usage"]
            usage_info["input_tokens"] = usage.get("prompt_tokens")
            usage_info["output_tokens"] = usage.get("completion_tokens")
            usage_info["total_tokens"] = usage.get("total_tokens")
            
            # トークン制限チェック
            if self.config.max_tokens and usage_info["total_tokens"]:
                if usage_info["total_tokens"] >= self.config.max_tokens * 0.95:  # 95%以上で警告
                    usage_info["token_warning"] = True
                if usage_info["total_tokens"] >= self.config.max_tokens:
                    usage_info["token_limit_reached"] = True
        
        return usage_info
    
    def _detect_token_related_errors(self, error_response: dict, status_code: int) -> Optional[str]:
        """エラーレスポンスからトークン関連のエラーを検出"""
        error_text = str(error_response).lower()
        
        # 一般的なトークン不足のエラーメッセージ
        token_error_indicators = [
            "maximum context length",
            "token limit",
            "too many tokens",
            "context length exceeded",
            "input too long",
            "prompt too long",
            "max_tokens",
            "token limit exceeded"
        ]
        
        for indicator in token_error_indicators:
            if indicator in error_text:
                return f"トークン不足エラー: {indicator}"
        
        # HTTPステータスコードベースの判定
        if status_code == 413:  # Payload Too Large
            return "トークン不足エラー: リクエストが大きすぎます"
        
        return None
    
    def is_available(self) -> bool:
        """APIが利用可能かチェック"""
        return True
