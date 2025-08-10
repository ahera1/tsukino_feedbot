import requests
from typing import Optional


class AIService:
    """OpenRouter APIを使用してAI要約を生成するクラス"""
    
    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def generate_summary(self, title: str, content: str, prompt_template: str) -> Optional[str]:
        """記事の要約を生成"""
        try:
            # プロンプトの作成
            prompt = prompt_template.format(title=title, content=content)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/ahera1/tsukino_feedbot",
                "X-Title": "Tsukino Feedbot"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.3
            }
            
            response = requests.post(self.base_url, json=data, headers=headers)
            
            # レートリミット（429）の場合は特別処理
            if response.status_code == 429:
                print("⚠️  OpenRouter APIのレートリミットに達しました。")
                print("しばらく時間をおいてから再実行してください。")
                raise SystemExit("レートリミットエラーのため終了します。")
            
            response.raise_for_status()
            
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                summary = result["choices"][0]["message"]["content"].strip()
                print(f"AI要約生成完了: {title[:50]}...")
                return summary
            else:
                print(f"AI応答形式エラー: {result}")
                return None
                
        except SystemExit:
            # レートリミットエラーは再発生させる
            raise
        except requests.exceptions.RequestException as e:
            print(f"API通信エラー: {e}")
            return None
        except Exception as e:
            print(f"要約生成エラー: {e}")
            return None
