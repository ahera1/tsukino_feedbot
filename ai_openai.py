import requests
from typing import Optional
from ai_base import AIServiceBase, AIConfig
import logging

logger = logging.getLogger(__name__)

class OpenAIService(AIServiceBase):
    """OpenAI API実装"""
    
    def __init__(self, config: AIConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.openai.com/v1/chat/completions"
        
    def generate_summary(self, title: str, content: str, prompt_template: str) -> str:
        """OpenAI APIで要約生成"""
        if not self.config.api_key:
            raise ValueError(f"{self.name}: APIキーが設定されていません")
            
        prompt = prompt_template.format(title=title, content=content)
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.config.model or "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            **self.config.extra_params
        }
        
        # max_tokensとtemperatureがNoneでない場合のみ追加
        if self.config.max_tokens is not None:
            data["max_tokens"] = self.config.max_tokens
        if self.config.temperature is not None:
            data["temperature"] = self.config.temperature
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result and result["choices"]:
                return result["choices"][0]["message"]["content"].strip()
            else:
                raise ValueError(f"予期しないレスポンス形式: {result}")
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                raise Exception(f"{self.name}: レート制限に達しました")
            elif e.response.status_code in [401, 403]:
                raise Exception(f"{self.name}: 認証エラー")
            else:
                raise Exception(f"{self.name}: HTTPエラー {e.response.status_code}")
        except Exception as e:
            logger.error(f"{self.name}でエラーが発生: {str(e)}")
            raise
