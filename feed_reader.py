import feedparser
from datetime import datetime
from typing import List
from models import FeedItem, FeedSource
import hashlib
from config import MIN_TITLE_LENGTH, MIN_CONTENT_LENGTH


class FeedReader:
    """RSSフィードを読み取り、記事を取得するクラス"""
    
    def _is_article_complete(self, entry, min_title_length: int = None, min_content_length: int = None) -> bool:
        """記事が完全かチェック"""
        # デフォルト値の設定
        if min_title_length is None:
            min_title_length = MIN_TITLE_LENGTH
        if min_content_length is None:
            min_content_length = MIN_CONTENT_LENGTH
        
        # タイトルチェック
        title = getattr(entry, 'title', '').strip()
        if len(title) < min_title_length:
            return False
        
        # 本文チェック（summary または content）
        content = self._extract_content(entry)
        if len(content.strip()) < min_content_length:
            return False
        
        return True
    
    def fetch_feed_items(self, feed_source: FeedSource) -> List[FeedItem]:
        """指定されたフィードから記事を取得"""
        try:
            feed = feedparser.parse(feed_source.url)
            
            if feed.bozo:
                print(f"フィード解析警告 ({feed_source.name}): {feed.bozo_exception}")
            
            items = []
            for entry in feed.entries:
                # 完全性チェック
                if not self._is_article_complete(entry):
                    print(f"不完全な記事をスキップ: {getattr(entry, 'link', 'URL不明')}")
                    continue
                
                # 記事の一意IDを生成（URLベース）
                article_id = hashlib.md5(entry.link.encode()).hexdigest()
                
                # 公開日時の取得
                published = self._parse_published_date(entry)
                
                # 内容の取得
                content = self._extract_content(entry)
                
                feed_item = FeedItem(
                    id=article_id,
                    title=entry.title,
                    content=content,
                    url=entry.link,
                    published=published,
                    source_feed=feed_source.name
                )
                items.append(feed_item)
            
            print(f"{feed_source.name}: {len(items)}件の記事を取得")
            return items
            
        except Exception as e:
            print(f"フィード取得エラー ({feed_source.name}): {e}")
            return []
    
    def _parse_published_date(self, entry) -> datetime:
        """記事の公開日時を解析"""
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except:
                pass
        
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6])
            except:
                pass
        
        # フォールバック: 現在時刻
        return datetime.now()
    
    def _extract_content(self, entry) -> str:
        """記事の内容を抽出"""
        # summary または content を試す
        if hasattr(entry, 'summary') and entry.summary:
            return entry.summary
        
        if hasattr(entry, 'content') and entry.content:
            # contentが複数ある場合は最初のものを使用
            if isinstance(entry.content, list) and len(entry.content) > 0:
                return entry.content[0].value
            return str(entry.content)
        
        if hasattr(entry, 'description') and entry.description:
            return entry.description
        
        return entry.title  # フォールバック: タイトルのみ
