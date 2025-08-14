from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging
import time
import requests

logger = logging.getLogger(__name__)

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
        # タイムアウト設定
        kwargs.setdefault('timeout', self.config.timeout)
        
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"{self.name}: タイムアウト発生 (試行 {attempt + 1}/{self.config.max_retries}) - {str(e)}")
                
            except requests.exceptions.HTTPError as e:
                # HTTPエラーの場合、リトライするかどうか判断
                if e.response.status_code in [408, 429, 500, 502, 503, 504]:
                    last_exception = e
                    logger.warning(f"{self.name}: リトライ可能なHTTPエラー (試行 {attempt + 1}/{self.config.max_retries}) - {e.response.status_code}")
                else:
                    # 認証エラーなどはリトライしない
                    raise e
                    
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                logger.warning(f"{self.name}: 接続エラー (試行 {attempt + 1}/{self.config.max_retries}) - {str(e)}")
                
            except Exception as e:
                # その他の例外はリトライしない
                raise e
            
            # 最後の試行でなければ待機
            if attempt < self.config.max_retries - 1:
                wait_time = self.config.retry_delay * (2 ** attempt)  # 指数バックオフ
                logger.info(f"{self.name}: {wait_time}秒後にリトライします...")
                time.sleep(wait_time)
        
        # 全ての試行が失敗した場合
        raise last_exception
    
    def is_available(self) -> bool:
        """APIが利用可能かチェック"""
        return True
