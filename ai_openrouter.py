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
    
    def _extract_final_response(self, content: str) -> str:
        """thinking部分を除去して最終的な要約のみを抽出"""
        # assistantfinalマーカーがある場合はその後の内容を取得
        if "assistantfinal" in content:
            parts = content.split("assistantfinal", 1)
            if len(parts) > 1:
                final_content = parts[1].strip()
                logger.debug(f"{self.name}: assistantfinalマーカーで最終内容を抽出しました")
                return final_content
        
        # analysisから始まる場合のパターンマッチング
        if content.startswith("analysis"):
            # 日本語の段落を探す（ひらがな・カタカナ・漢字を含む行）
            import re
            lines = content.split('\n')
            japanese_pattern = re.compile(r'[ひらがなカタカナ漢字一-龯あ-ん ア-ヶー]')
            
            for line in reversed(lines):
                line = line.strip()
                if (line and 
                    len(line) > 30 and  # 最低限の長さ
                    japanese_pattern.search(line) and  # 日本語を含む
                    not line.startswith(("analysis", "We need", "Let's", "Count", "=", '"')) and
                    not line.endswith(('?"', '"'))):  # 英語の引用文でない
                    logger.debug(f"{self.name}: analysis部分から日本語要約を抽出しました")
                    return line
            
            # 最後の手段として、最も長い日本語行を探す
            japanese_lines = []
            for line in lines:
                line = line.strip()
                if (line and 
                    len(line) > 30 and 
                    japanese_pattern.search(line) and
                    not line.startswith(("analysis", "We need", "Let's", "Count"))):
                    japanese_lines.append(line)
            
            if japanese_lines:
                # 最も長い行を選択
                best_line = max(japanese_lines, key=len)
                logger.debug(f"{self.name}: 最長の日本語行を抽出しました")
                return best_line
        
        # マーカーが見つからない場合はそのまま返す
        logger.debug(f"{self.name}: 特殊処理なしでそのまま返します")
        return content
        
    def generate_summary(self, title: str, content: str, prompt_template: str) -> str:
        """OpenRouter APIで要約生成"""
        if not self.config.api_key:
            raise ValueError(f"{self.name}: APIキーが設定されていません")
            
        # プロンプトに明確な出力指示を追加
        base_prompt = prompt_template.format(title=title, content=content)
        prompt = f"{base_prompt}\n\n直接的な要約のみを出力してください。thinking過程や分析は含めないでください。"
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ahera1/tsukino_feedbot",
            "X-Title": "Tsukino Feedbot"
        }
        
        data = {
            "model": self.config.model or "google/gemini-2.0-flash-thinking-exp-1219:free",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
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
                # トークン使用量を分析
                usage_info = self._analyze_response_usage(result)
                
                # トークン使用量をログ出力
                if usage_info["total_tokens"]:
                    logger.info(f"{self.name}: トークン使用量 - 入力: {usage_info['input_tokens']}, "
                              f"出力: {usage_info['output_tokens']}, 合計: {usage_info['total_tokens']}")
                    
                    if usage_info["token_warning"]:
                        logger.warning(f"{self.name}: トークン使用量が制限の95%に達しました")
                        print(f"⚠️  {self.name}: トークン使用量警告 - {usage_info['total_tokens']}/{self.config.max_tokens}")
                    
                    if usage_info["token_limit_reached"]:
                        logger.error(f"{self.name}: トークン制限に達しました")
                        print(f"🚫 {self.name}: トークン制限達成 - {usage_info['total_tokens']}/{self.config.max_tokens}")
                
                content = result["choices"][0]["message"]["content"].strip()
                
                # Gemini-2.0-flash-thinking-expモデルの場合、thinking部分を除去
                summary = self._extract_final_response(content)
                
                logger.debug(f"{self.name}: 要約生成成功 (文字数: {len(summary)})")
                return summary
            else:
                raise ValueError(f"予期しないレスポンス形式: {result}")
                
        except requests.exceptions.HTTPError as e:
            error_response = {}
            try:
                error_response = e.response.json() if e.response else {}
            except:
                pass
            
            # トークン関連エラーをチェック
            token_error = self._detect_token_related_errors(error_response, e.response.status_code)
            if token_error:
                logger.error(f"{self.name}: {token_error}")
                print(f"🚫 {self.name}: {token_error}")
                raise Exception(f"{self.name}: {token_error}")
            
            if e.response.status_code == 402:
                raise Exception(f"{self.name}: クレジットが不足しています")
            else:
                raise Exception(f"{self.name}: HTTPエラー {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"{self.name}でエラーが発生: {str(e)}")
            raise
