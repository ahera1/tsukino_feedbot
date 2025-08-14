import requests
from typing import Optional
from ai_base import AIServiceBase, AIConfig
import logging

logger = logging.getLogger(__name__)

class OllamaService(AIServiceBase):
    """Ollama API実装"""
    
    def __init__(self, config: AIConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434/api/chat"
        
    def generate_summary(self, title: str, content: str, prompt_template: str) -> str:
        """Ollama APIで要約生成"""
        prompt = prompt_template.format(title=title, content=content)
        
        data = {
            "model": self.config.model or "llama2",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                **self.config.extra_params
            }
        }
        
        # temperatureがNoneでない場合のみoptionsに追加
        if self.config.temperature is not None:
            data["options"]["temperature"] = self.config.temperature
        
        try:
            response = self._make_request_with_retry(
                "POST",
                self.base_url,
                json=data
            )
            
            result = response.json()
            if "message" in result and "content" in result["message"]:
                summary = result["message"]["content"].strip()
                logger.debug(f"{self.name}: 要約生成成功 (文字数: {len(summary)})")
                return summary
            else:
                raise ValueError(f"予期しないレスポンス形式: {result}")
                
        except requests.exceptions.ConnectionError:
            raise Exception(f"{self.name}: Ollamaサーバーに接続できません")
        except Exception as e:
            logger.error(f"{self.name}でエラーが発生: {str(e)}")
            raise
    
    def is_available(self) -> bool:
        """Ollamaサーバーが利用可能かチェック"""
        try:
            response = requests.get(f"{self.base_url.replace('/api/chat', '')}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
