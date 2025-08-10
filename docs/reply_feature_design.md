# Mastodonリプライ自動返信機能 実装設計書

## 概要
Mastodonへのリプライに対してAIで自動返信する機能の実装方針と技術仕様

作成日: 2025-08-10

## 実装可能性

### 技術的実現性
- ✅ **Mastodon.py** はメンション（リプライ）の取得と返信投稿をサポート
- ✅ **会話スレッドの取得** も可能（context APIを使用）
- ✅ **OpenRouter API** で会話コンテキストを含めた返信生成が可能

### 必要な機能
1. メンション通知の監視
2. 会話スレッドコンテキストの取得
3. AIによる返信文生成
4. 返信の自動投稿
5. 処理済みメンションの管理

## 実装設計

### 新規ファイル構成

#### `reply_handler.py`
```python
import hashlib
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional
from mastodon import Mastodon
from ai_service import generate_reply
from storage import load_json, save_json
import config

@dataclass
class ProcessedReply:
    """処理済みリプライの記録"""
    mention_id: str
    replied_at: datetime
    reply_status_id: str
    
    def to_dict(self):
        data = asdict(self)
        data['replied_at'] = self.replied_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data):
        data['replied_at'] = datetime.fromisoformat(data['replied_at'])
        return cls(**data)

class ReplyHandler:
    def __init__(self, mastodon_client: Mastodon):
        self.mastodon = mastodon_client
        self.processed_file = "processed_replies.json"
        self.processed_replies = self._load_processed()
    
    def _load_processed(self) -> set:
        """処理済みリプライIDを読み込み"""
        data = load_json(self.processed_file)
        return set(data.get('mention_ids', []))
    
    def _save_processed(self, mention_id: str):
        """処理済みリプライIDを保存"""
        self.processed_replies.add(mention_id)
        save_json(self.processed_file, {
            'mention_ids': list(self.processed_replies),
            'last_updated': datetime.now().isoformat()
        })
    
    def get_conversation_context(self, status) -> List[dict]:
        """会話スレッドを取得"""
        context = []
        
        # 親投稿を遡って取得
        current = status
        while current.get('in_reply_to_id'):
            try:
                parent = self.mastodon.status(current['in_reply_to_id'])
                context.insert(0, {
                    'author': parent['account']['display_name'] or parent['account']['username'],
                    'content': self._clean_html(parent['content']),
                    'is_bot': parent['account'].get('bot', False)
                })
                current = parent
            except:
                break
        
        # 現在のメンションを追加
        context.append({
            'author': status['account']['display_name'] or status['account']['username'],
            'content': self._clean_html(status['content']),
            'is_bot': status['account'].get('bot', False)
        })
        
        return context[-5:]  # 最大5つまでのコンテキスト
    
    def _clean_html(self, html_content: str) -> str:
        """HTMLタグを除去"""
        import re
        # 基本的なHTML除去
        text = re.sub(r'<br\s*/?>', '\n', html_content)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'@\S+\s*', '', text)  # メンション除去
        return text.strip()
    
    def check_and_reply(self):
        """新しいメンションをチェックして返信"""
        try:
            # 通知を取得（メンションのみ）
            notifications = self.mastodon.notifications(
                types=['mention'],
                limit=10
            )
            
            for notification in notifications:
                mention_id = notification['id']
                
                # 既に処理済みならスキップ
                if mention_id in self.processed_replies:
                    continue
                
                status = notification['status']
                
                # 自分の投稿へのリプライはスキップ
                if status['account']['id'] == self.mastodon.me()['id']:
                    self._save_processed(mention_id)
                    continue
                
                # 会話コンテキストを取得
                context = self.get_conversation_context(status)
                
                # AI返信生成
                reply_text = generate_reply(context, config.REPLY_SETTINGS)
                
                if reply_text:
                    # 返信投稿
                    reply_status = self.mastodon.status_post(
                        f"@{status['account']['acct']} {reply_text}",
                        in_reply_to_id=status['id'],
                        visibility=status['visibility']  # 元の投稿と同じ公開範囲
                    )
                    
                    print(f"返信完了: {status['account']['acct']}への返信")
                    
                # 処理済みとして記録
                self._save_processed(mention_id)
                
        except Exception as e:
            print(f"リプライ処理エラー: {e}")
```

### 既存ファイルの拡張

#### `ai_service.py` への追加機能
```python
def generate_reply(conversation_context: List[dict], reply_settings: dict) -> Optional[str]:
    """会話コンテキストからAI返信を生成"""
    try:
        # 会話履歴を文字列化
        conversation = "\n".join([
            f"{msg['author']}: {msg['content']}" 
            for msg in conversation_context
        ])
        
        prompt = reply_settings.get('prompt_template', DEFAULT_REPLY_PROMPT).format(
            conversation=conversation
        )
        
        headers = {
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": reply_settings.get('model', config.AI_MODEL),
            "messages": [
                {"role": "system", "content": reply_settings.get('system_prompt', DEFAULT_REPLY_SYSTEM)},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": reply_settings.get('max_tokens', 200)
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            reply = response.json()['choices'][0]['message']['content']
            # 文字数制限
            if len(reply) > 500:
                reply = reply[:497] + "..."
            return reply
            
    except Exception as e:
        print(f"AI返信生成エラー: {e}")
        return None

DEFAULT_REPLY_SYSTEM = """あなたはMastodonで活動する親切なボットです。
簡潔で友好的な返信を心がけてください。
技術的な話題にも対応できます。"""

DEFAULT_REPLY_PROMPT = """以下の会話に対して、最後の発言に適切に返信してください：

{conversation}

返信は簡潔に、140文字以内でお願いします。"""
```

#### `config.py` への追加設定
```python
# リプライ設定
REPLY_SETTINGS = {
    'enabled': True,  # リプライ機能の有効/無効
    'check_interval': 300,  # チェック間隔（秒）
    'model': 'openai/gpt-3.5-turbo',  # 返信用のAIモデル（軽量版推奨）
    'max_tokens': 200,
    'system_prompt': """あなたはMastodonで活動する親切なボットです。
簡潔で友好的な返信を心がけてください。
技術的な話題にも対応できます。
絵文字を適度に使って親しみやすくしてください。""",
    'prompt_template': """以下の会話に対して、最後の発言に適切に返信してください：

{conversation}

返信は簡潔に、140文字以内でお願いします。"""
}

# リプライ禁止ワード（これらを含むメンションには返信しない）
REPLY_IGNORE_KEYWORDS = ['spam', 'unsubscribe', 'stop']
```

#### `main.py` への統合方法
```python
from reply_handler import ReplyHandler

def automated_mode():
    """自動実行モード"""
    # ...existing code...
    
    # リプライハンドラーの初期化
    reply_handler = None
    if config.REPLY_SETTINGS.get('enabled', False):
        reply_handler = ReplyHandler(mastodon)
        print("リプライ自動返信機能: 有効")
    
    while True:
        # ...existing code...
        
        # リプライチェック（5分ごと）
        if reply_handler and datetime.now().minute % 5 == 0:
            print("新しいリプライをチェック中...")
            reply_handler.check_and_reply()
        
        # ...existing code...
```

## 技術仕様

### データ構造

#### 処理済みリプライ管理
```json
{
  "mention_ids": ["12345", "12346", "12347"],
  "last_updated": "2025-08-10T12:00:00"
}
```

#### 会話コンテキスト
```python
[
    {
        "author": "ユーザー名",
        "content": "投稿内容",
        "is_bot": false
    },
    # ...最大5件
]
```

### API制限と対策

#### Mastodon API制限
- 通知取得: 300回/15分
- 投稿: 300回/15分
- 対策: 5分間隔でのチェック

#### OpenRouter API制限
- モデルによって異なる
- 対策: 軽量モデル（GPT-3.5）の使用

## 運用上の考慮事項

### セキュリティ
1. **スパム対策**
   - 禁止キーワードフィルタリング
   - 連続投稿の制限
   - ブロックユーザーの除外

2. **プライバシー**
   - 会話履歴の適切な管理
   - 個人情報の除外

### パフォーマンス
1. **レスポンス時間**
   - AI生成: 2-5秒
   - 全体処理: 10秒以内

2. **リソース使用量**
   - メモリ: 軽量維持
   - API呼び出し: 最小限

### 品質管理
1. **返信品質**
   - コンテキスト理解の精度
   - 適切な日本語返信
   - 感情的配慮

2. **エラーハンドリング**
   - ネットワークエラー
   - API制限エラー
   - 不正な入力データ

## 実装優先度

### Phase 1: 基本機能
- [ ] メンション取得機能
- [ ] 単発返信生成
- [ ] 処理済み管理

### Phase 2: 拡張機能
- [ ] 会話コンテキスト対応
- [ ] スパムフィルタ
- [ ] 設定管理UI

### Phase 3: 高度機能
- [ ] 学習機能
- [ ] 感情分析
- [ ] 多言語対応

## 想定される課題

### 技術的課題
1. **会話コンテキストの精度**
   - 長いスレッドの要約
   - 関連性の判定

2. **レート制限対応**
   - 大量メンション時の処理
   - APIクォータ管理

### 運用的課題
1. **不適切な返信**
   - 炎上リスク
   - 誤解を招く回答

2. **メンテナンス**
   - プロンプト調整
   - モデル更新

## 代替案

### 軽量版実装
- 会話コンテキストなし
- 単純なキーワード反応
- テンプレート返信

### 高機能版実装
- 感情分析
- ユーザープロファイル
- 学習機能

## 参考資料

### Mastodon API
- [Notifications API](https://docs.joinmastodon.org/methods/notifications/)
- [Statuses API](https://docs.joinmastodon.org/methods/statuses/)

### OpenRouter API
- [Chat Completions](https://openrouter.ai/docs#chat-completions)
- [Models](https://openrouter.ai/docs#models)

---

**注意**: この機能は慎重な実装と運用が必要です。特にスパム対策と品質管理に十分注意してください。
