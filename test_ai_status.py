#!/usr/bin/env python3
import sys
sys.path.append('/app')

from main import FeedBot

def test_ai_status():
    bot = FeedBot()
    print('=== AI サービスの状態 ===')
    status = bot.ai_service.get_status()
    for service, info in status.items():
        available = info["available"]
        priority = info["priority"]
        print(f'  {service}: 利用可能={available}, 優先度={priority}')
    
    print('\n=== 簡易要約テスト ===')
    try:
        test_summary = bot.ai_service.generate_summary(
            "テスト記事",
            "これはAIサービスのテスト用記事です。",
            "以下の記事を50文字以内で要約してください。\n\n記事タイトル: {title}\n記事内容: {content}"
        )
        if test_summary:
            print(f'✅ 要約テスト成功: {test_summary}')
        else:
            print('❌ 要約テスト失敗: 要約が生成されませんでした')
    except Exception as e:
        print(f'❌ 要約テスト失敗: {e}')

if __name__ == "__main__":
    test_ai_status()
