import feedparser
from datetime import datetime, timedelta, timezone
from typing import List
from models import FeedItem, FeedSource
import hashlib
from config import MIN_TITLE_LENGTH, MIN_CONTENT_LENGTH, FEED_INITIAL_DELAY_MINUTES


class FeedReader:
    """RSSフィードを読み取り、記事を取得するクラス"""
    
    def _is_article_too_new(self, published_time: datetime, delay_minutes: int = None) -> bool:
        """記事が新しすぎるかチェック（遅延処理が必要か）"""
        if delay_minutes is None:
            delay_minutes = FEED_INITIAL_DELAY_MINUTES
        
        # 現在時刻を取得（UTC）
        now = datetime.now(timezone.utc)
        
        # 公開時刻がタイムゾーン情報を持たない場合はUTCとして扱う
        if published_time.tzinfo is None:
            published_time = published_time.replace(tzinfo=timezone.utc)
        
        # 公開からの経過時間を計算
        time_since_published = now - published_time
        
        # 指定した遅延時間以内の記事は新しすぎると判定
        return time_since_published < timedelta(minutes=delay_minutes)
    
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
                
                # 公開日時の取得
                published = self._parse_published_date(entry)
                
                # 新しすぎる記事の遅延処理チェック
                if self._is_article_too_new(published):
                    print(f"新しすぎる記事を遅延: {getattr(entry, 'title', 'タイトル不明')} (公開: {published})")
                    continue
                
                # 記事の一意IDを生成（URLベース）
                article_id = hashlib.md5(entry.link.encode()).hexdigest()
                
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
                # published_parsedからdatetimeオブジェクトを作成
                dt = datetime(*entry.published_parsed[:6])
                # タイムゾーン情報がない場合はUTCとして扱う
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except:
                pass
        
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                # updated_parsedからdatetimeオブジェクトを作成
                dt = datetime(*entry.updated_parsed[:6])
                # タイムゾーン情報がない場合はUTCとして扱う
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except:
                pass
        
        # フォールバック: 現在時刻（UTC）
        return datetime.now(timezone.utc)
    
    def _extract_content(self, entry) -> str:
        """記事の内容を抽出（content要素を優先）"""
        # 1. content要素を最優先（通常は最も詳細な内容）
        if hasattr(entry, 'content') and entry.content:
            # contentが複数ある場合は最初のものを使用
            if isinstance(entry.content, list) and len(entry.content) > 0:
                content_value = getattr(entry.content[0], 'value', str(entry.content[0]))
                if content_value and content_value.strip():
                    return content_value
            elif hasattr(entry.content, 'value'):
                content_value = entry.content.value
                if content_value and content_value.strip():
                    return content_value
            else:
                content_str = str(entry.content)
                if content_str and content_str.strip():
                    return content_str
        
        # 2. summary要素（contentがない場合や空の場合）
        if hasattr(entry, 'summary') and entry.summary and entry.summary.strip():
            return entry.summary
        
        # 3. description要素（古いフィード形式）
        if hasattr(entry, 'description') and entry.description and entry.description.strip():
            return entry.description
        
        # 4. フォールバック: タイトルのみ
        return getattr(entry, 'title', 'タイトルなし')
