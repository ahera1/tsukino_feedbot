#!/usr/bin/env python3
"""
AI Service Test - フォールバック機能のテスト用スクリプト
"""

import os
from ai_base import AIConfig
from ai_manager import AIServiceManager

def test_ai_services():
    """AI サービスのフォールバック機能をテスト"""
    
    # テスト用の設定
    configs = [
        AIConfig(
            name="OpenRouter",
            api_key=os.getenv("OPENROUTER_API_KEY", "dummy_key"),
            model="google/gemini-2.0-flash-thinking-exp-1219:free",
            max_tokens=None if os.getenv("AI_MAX_TOKENS", "").strip() == "" else 100,
            temperature=None if os.getenv("AI_TEMPERATURE", "").strip() == "" else 0.3
        ),
        AIConfig(
            name="OpenAI", 
            api_key=os.getenv("OPENAI_API_KEY", "dummy_key"),
            model="gpt-3.5-turbo",
            max_tokens=None if os.getenv("AI_MAX_TOKENS", "").strip() == "" else 100,
            temperature=None if os.getenv("AI_TEMPERATURE", "").strip() == "" else 0.3
        ),
        AIConfig(
            name="Ollama",
            base_url="http://localhost:11434/api/chat",
            model="llama2",
            max_tokens=None if os.getenv("AI_MAX_TOKENS", "").strip() == "" else 100,
            temperature=None if os.getenv("AI_TEMPERATURE", "").strip() == "" else 0.3
        )
    ]
    
    try:
        manager = AIServiceManager.from_configs(configs)
        print(f"✅ AIServiceManager初期化成功: {len(manager.services)}個のサービス")
        
        # サービス状態の確認
        status = manager.get_status()
        print("\n📊 サービス状態:")
        for service_name, info in status.items():
            available = "✅ 利用可能" if info["available"] else "❌ 利用不可"
            print(f"  {info['priority']}. {service_name}: {available}")
        
        # パラメータ設定の確認
        print(f"\n⚙️  パラメータ設定:")
        for service in manager.services:
            max_tokens_str = "未設定" if service.config.max_tokens is None else str(service.config.max_tokens)
            temperature_str = "未設定" if service.config.temperature is None else str(service.config.temperature)
            print(f"  {service.name}: max_tokens={max_tokens_str}, temperature={temperature_str}")
        
        # テスト用の要約生成
        test_title = "テスト記事"
        test_content = "これはAIサービスのテスト用の短い記事です。"
        test_prompt = "以下の記事を50文字以内で要約してください:\nタイトル: {title}\n内容: {content}"
        
        print(f"\n🧪 要約生成テスト開始...")
        print(f"記事: {test_title}")
        print(f"内容: {test_content}")
        
        try:
            summary = manager.generate_summary(test_title, test_content, test_prompt)
            print(f"\n✅ 要約生成成功:")
            print(f"要約: {summary}")
        except Exception as e:
            print(f"\n❌ 要約生成失敗: {e}")
            
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")

if __name__ == "__main__":
    print("🤖 AI Service Fallback Test")
    print("=" * 40)
    test_ai_services()
