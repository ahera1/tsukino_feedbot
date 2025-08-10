from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

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
    
    def is_available(self) -> bool:
        """APIが利用可能かチェック"""
        return True
