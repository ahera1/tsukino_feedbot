from ai_base import AIServiceBase, AIConfig, AIServiceError
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
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        # メッセージ配列を構築
        messages = []
        
        # システムプロンプトを設定から取得
        system_prompt = self.config.extra_params.get("system_prompt")
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            logger.debug(f"{self.name}: システムプロンプトを使用")
        
        # ユーザープロンプト
        user_prompt = prompt_template.format(title=title, content=content)
        messages.append({"role": "user", "content": user_prompt})
        
        # extra_paramsからsystem_promptを除外してdataに追加
        extra_params = {k: v for k, v in self.config.extra_params.items() if k != "system_prompt"}
        
        data = {
            "model": self.config.model or "gpt-3.5-turbo",
            "messages": messages,
            "stream": False,
            **extra_params
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
                usage_info = self._analyze_response_usage(result)
                
                if usage_info["total_tokens"]:
                    logger.info(f"{self.name}: トークン使用量 - 入力: {usage_info['input_tokens']}, "
                              f"出力: {usage_info['output_tokens']}, 合計: {usage_info['total_tokens']}")
                    
                    if usage_info["token_warning"]:
                        logger.warning(f"{self.name}: トークン使用量警告 - "
                                      f"{usage_info['total_tokens']}/{self.config.max_tokens}")
                    
                    if usage_info["token_limit_reached"]:
                        logger.error(f"{self.name}: トークン制限到達 - "
                                    f"{usage_info['total_tokens']}/{self.config.max_tokens}")
                
                summary = result["choices"][0]["message"]["content"].strip()
                logger.debug(f"{self.name}: 要約生成成功 (文字数: {len(summary)})")
                return summary
            else:
                raise ValueError(f"予期しないレスポンス形式: {result}")
                
        except AIServiceError as e:
            if e.response_body and e.status_code:
                token_error = self._detect_token_related_errors(e.response_body, e.status_code)
                if token_error:
                    logger.error(f"{self.name}: {token_error}")
                    raise AIServiceError(
                        f"{self.name}: {token_error}",
                        service_name=self.name,
                        error_category=AIServiceError.TOKEN_ERROR,
                        status_code=e.status_code)
            logger.error(f"{self.name}: {e.category_label} (HTTP {e.status_code})")
            raise
        except Exception as e:
            logger.error(f"{self.name}でエラーが発生: {str(e)}")
            raise AIServiceError(
                f"{self.name}: {str(e)}",
                service_name=self.name,
                error_category=AIServiceError.UNKNOWN)
