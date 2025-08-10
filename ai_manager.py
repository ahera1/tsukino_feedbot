from typing import List, Optional
from ai_base import AIServiceBase, AIConfig
from ai_openrouter import OpenRouterService
from ai_openai import OpenAIService
from ai_ollama import OllamaService
import logging

logger = logging.getLogger(__name__)

class AIServiceManager:
    """複数のAI APIを管理し、フォールバック機能を提供"""
    
    def __init__(self, services: List[AIServiceBase]):
        """
        Args:
            services: 優先順位順のAIサービスリスト（最初が最優先）
        """
        self.services = services
        if not services:
            raise ValueError("少なくとも1つのAIサービスが必要です")
    
    @classmethod
    def from_configs(cls, configs: List[AIConfig]) -> 'AIServiceManager':
        """設定リストからAIサービスマネージャーを作成"""
        services = []
        
        for config in configs:
            if config.name.lower() == "openrouter":
                service = OpenRouterService(config)
            elif config.name.lower() == "openai":
                service = OpenAIService(config)
            elif config.name.lower() == "ollama":
                service = OllamaService(config)
            else:
                logger.warning(f"未知のAIサービス: {config.name}")
                continue
                
            services.append(service)
        
        return cls(services)
    
    def generate_summary(self, title: str, content: str, prompt_template: str) -> str:
        """
        要約を生成。プライマリAPIでエラーが発生した場合、
        セカンダリAPIにフォールバック
        """
        errors = []
        
        for i, service in enumerate(self.services):
            try:
                # サービスが利用可能かチェック
                if not service.is_available():
                    logger.warning(f"{service.name}は利用できません。スキップします。")
                    errors.append(f"{service.name}: 利用不可")
                    continue
                
                logger.info(f"{service.name}で要約生成を試行中...")
                summary = service.generate_summary(title, content, prompt_template)
                logger.info(f"{service.name}で要約生成に成功")
                logger.debug(f"要約結果: {summary[:100]}...")
                print(f"✅ {service.name}で要約生成完了: {title[:50]}...")
                return summary
                
            except Exception as e:
                error_msg = str(e)
                errors.append(f"{service.name}: {error_msg}")
                logger.error(f"{service.name}でエラー: {error_msg}")
                print(f"❌ {service.name}でエラー: {error_msg}")
                
                # 最後のサービスでなければ次を試行
                if i < len(self.services) - 1:
                    print(f"⏭️  次のサービスに切り替えます...")
                    continue
        
        # すべてのサービスで失敗
        error_summary = "\n".join(errors)
        raise Exception(f"すべてのAIサービスで要約生成に失敗しました:\n{error_summary}")
    
    def get_status(self) -> dict:
        """各サービスの状態を取得"""
        status = {}
        for service in self.services:
            status[service.name] = {
                "available": service.is_available(),
                "priority": self.services.index(service) + 1
            }
        return status
