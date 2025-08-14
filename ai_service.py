from typing import Optional
from ai_base import AIConfig
from ai_manager import AIServiceManager
import os
import logging

logger = logging.getLogger(__name__)

class AIService:
    """
    互換性のための旧AIServiceクラス
    内部的には新しいAIServiceManagerを使用
    """
    
    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        """旧形式の初期化（後方互換性のため）"""
        # デフォルト設定でOpenRouterのみを使用
        config = AIConfig(
            name="OpenRouter",
            api_key=api_key,
            model=model,
            max_tokens=1000,
            temperature=0.3
        )
        self.manager = AIServiceManager.from_configs([config])
    
    def generate_summary(self, title: str, content: str, prompt_template: str) -> Optional[str]:
        """記事の要約を生成（旧形式API）"""
        try:
            return self.manager.generate_summary(title, content, prompt_template)
        except Exception as e:
            print(f"要約生成エラー: {e}")
            return None

def create_ai_service_manager(ai_configs: list) -> AIServiceManager:
    """設定リストからAIServiceManagerを作成"""
    configs = []
    
    for config_dict in ai_configs:
        # APIキーを環境変数から取得
        api_key = config_dict.get("api_key")
        if not api_key:
            api_key = os.getenv(f"{config_dict['name'].upper()}_API_KEY")
        
        # APIキーがない場合はスキップ
        if not api_key and config_dict["name"].lower() != "ollama":
            logger.warning(f"{config_dict['name']}のAPIキーが設定されていないためスキップします")
            continue
        
        ai_config = AIConfig(
            name=config_dict["name"],
            api_key=api_key,
            base_url=config_dict.get("base_url"),
            model=config_dict.get("model"),
            max_tokens=config_dict.get("max_tokens"),  # Noneの場合はAPIに渡さない
            temperature=config_dict.get("temperature"),  # Noneの場合はAPIに渡さない
            timeout=config_dict.get("timeout", 60),
            max_retries=config_dict.get("max_retries", 3),
            retry_delay=config_dict.get("retry_delay", 10),
            extra_params=config_dict.get("extra_params", {})
        )
        configs.append(ai_config)
    
    if not configs:
        raise ValueError("利用可能なAI APIサービスが設定されていません")
    
    return AIServiceManager.from_configs(configs)
