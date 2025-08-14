import requests
from typing import Optional
from ai_base import AIServiceBase, AIConfig
import logging

logger = logging.getLogger(__name__)

class OpenRouterService(AIServiceBase):
    """OpenRouter API実装"""
    
    def __init__(self, config: AIConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://openrouter.ai/api/v1/chat/completions"
        
    def generate_summary(self, title: str, content: str, prompt_template: str) -> str:
        """OpenRouter APIで要約生成"""
        if not self.config.api_key:
            raise ValueError(f"{self.name}: APIキーが設定されていません")
            
        prompt = prompt_template.format(title=title, content=content)
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ahera1/tsukino_feedbot",
            "X-Title": "Tsukino Feedbot"
        }
        
        data = {
            "model": self.config.model or "google/gemini-2.0-flash-thinking-exp-1219:free",
            "messages": [{"role": "user", "content": prompt}],
            **self.config.extra_params
        }
        
        # max_tokensとtemperatureがNoneでない場合のみ追加
        if self.config.max_tokens is not None:
            data["max_tokens"] = self.config.max_tokens
        if self.config.temperature is not None:
            data["temperature"] = self.config.temperature
        
        try:
            response = self._make_request_with_retry(
                "POST", 
                self.base_url, 
                headers=headers, 
                json=data
            )
            
            result = response.json()
            if "choices" in result and result["choices"]:
                summary = result["choices"][0]["message"]["content"].strip()
                logger.debug(f"{self.name}: 要約生成成功 (文字数: {len(summary)})")
                return summary
            else:
                raise ValueError(f"予期しないレスポンス形式: {result}")
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 402:
                raise Exception(f"{self.name}: クレジットが不足しています")
            else:
                raise Exception(f"{self.name}: HTTPエラー {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"{self.name}でエラーが発生: {str(e)}")
            raise
