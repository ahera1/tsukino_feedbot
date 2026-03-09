import time
from typing import List, Optional
from ai_base import AIServiceBase, AIConfig, AIServiceError
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
                if not service.is_available():
                    logger.warning(f"{service.name}は利用できません。スキップします。")
                    errors.append((service.name, "利用不可", None))
                    continue
                
                logger.info(f"{service.name}で要約生成を試行中... (モデル: {service.config.model})")
                start_time = time.time()
                summary = service.generate_summary(title, content, prompt_template)
                elapsed = time.time() - start_time
                
                logger.info(f"{service.name}で要約生成完了: {title[:50]}... "
                           f"(モデル: {service.config.model}, {elapsed:.1f}秒)")
                logger.debug(f"要約結果: {summary[:100]}...")
                
                if errors:
                    fallback_chain = " \u2192 ".join(
                        [f"{name}: {reason}" + (f" ({code})" if code else "") for name, reason, code in errors])
                    logger.info(f"フォールバック経緯: {fallback_chain} \u2192 {service.name}: 成功")
                
                return summary
                
            except AIServiceError as e:
                status_info = f" (HTTP {e.status_code})" if e.status_code else ""
                errors.append((service.name, e.category_label, e.status_code))
                logger.error(f"{service.name}: {e.category_label}{status_info} - {str(e)}")
                
                if i < len(self.services) - 1:
                    logger.warning(f"次のサービスに切り替えます...")
                    continue
                    
            except Exception as e:
                errors.append((service.name, "不明なエラー", None))
                logger.error(f"{service.name}でエラー: {str(e)}")
                
                if i < len(self.services) - 1:
                    logger.warning(f"次のサービスに切り替えます...")
                    continue
        
        error_summary = ", ".join(
            [f"{name}: {reason}" + (f" ({code})" if code else "") for name, reason, code in errors])
        raise Exception(f"すべてのAIサービスで要約生成に失敗: {error_summary}")
    
    def get_status(self) -> dict:
        """各サービスの状態を取得"""
        status = {}
        for service in self.services:
            status[service.name] = {
                "available": service.is_available(),
                "priority": self.services.index(service) + 1
            }
        return status
