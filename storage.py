import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from models import FeedItem, FeedSource


class DataStorage:
    """JSONファイルでのデータ永続化を管理するクラス"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.feeds_file = self.data_dir / "feeds.json"
        self.articles_file = self.data_dir / "articles.json"
    
    def load_feed_sources(self) -> List[FeedSource]:
        """フィードソース一覧を読み込む"""
        if not self.feeds_file.exists():
            return []
        
        try:
            with open(self.feeds_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            sources = []
            for item in data:
                last_checked = None
                if item.get('last_checked'):
                    last_checked = datetime.fromisoformat(item['last_checked'])
                
                sources.append(FeedSource(
                    url=item['url'],
                    name=item['name'],
                    enabled=item.get('enabled', True),
                    last_checked=last_checked
                ))
            return sources
        except Exception as e:
            print(f"フィードソース読み込みエラー: {e}")
            return []
    
    def save_feed_sources(self, sources: List[FeedSource]):
        """フィードソース一覧を保存"""
        try:
            data = []
            for source in sources:
                item = {
                    'url': source.url,
                    'name': source.name,
                    'enabled': source.enabled
                }
                if source.last_checked:
                    item['last_checked'] = source.last_checked.isoformat()
                data.append(item)
            
            with open(self.feeds_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"フィードソース保存エラー: {e}")
    
    def load_articles(self) -> List[FeedItem]:
        """記事一覧を読み込む"""
        if not self.articles_file.exists():
            return []
        
        try:
            with open(self.articles_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            articles = []
            for item in data:
                published = datetime.fromisoformat(item['published'])
                read_at = None
                if item.get('read_at'):
                    read_at = datetime.fromisoformat(item['read_at'])
                
                articles.append(FeedItem(
                    id=item['id'],
                    title=item['title'],
                    content=item['content'],
                    url=item['url'],
                    published=published,
                    source_feed=item['source_feed'],
                    processed=item.get('processed', False),
                    summary=item.get('summary'),
                    posted_to_mastodon=item.get('posted_to_mastodon', False),
                    read_at=read_at
                ))
            return articles
        except Exception as e:
            print(f"記事読み込みエラー: {e}")
            return []
    
    def save_articles(self, articles: List[FeedItem]):
        """記事一覧を保存"""
        try:
            data = []
            for article in articles:
                item = {
                    'id': article.id,
                    'title': article.title,
                    'content': article.content,
                    'url': article.url,
                    'published': article.published.isoformat(),
                    'source_feed': article.source_feed,
                    'processed': article.processed,
                    'summary': article.summary,
                    'posted_to_mastodon': article.posted_to_mastodon
                }
                if article.read_at:
                    item['read_at'] = article.read_at.isoformat()
                data.append(item)
            
            with open(self.articles_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"記事保存エラー: {e}")
    
    def cleanup_old_articles(self, days: int):
        """指定日数より古い記事を削除"""
        articles = self.load_articles()
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 公開日または読み取り日のいずれかが期限内のものを保持
        filtered_articles = []
        for article in articles:
            # 公開日が期限内、または読み取り日が期限内の場合は保持
            keep_article = (
                article.published >= cutoff_date or
                (article.read_at and article.read_at >= cutoff_date)
            )
            if keep_article:
                filtered_articles.append(article)
        
        if len(filtered_articles) < len(articles):
            self.save_articles(filtered_articles)
            removed_count = len(articles) - len(filtered_articles)
            print(f"{removed_count}件の古い記事を削除しました")
    
    def cleanup_old_read_records(self, days: int):
        """指定日数より古い読み取り記録のみを削除（未処理記事は保持）"""
        articles = self.load_articles()
        cutoff_date = datetime.now() - timedelta(days=days)
        
        filtered_articles = []
        for article in articles:
            should_keep = False
            
            # 未処理記事は読み取り日時に関係なく保持
            if not article.processed:
                should_keep = True
            # 処理済み記事は読み取り日時または公開日時で判定
            elif article.read_at:
                should_keep = article.read_at >= cutoff_date
            else:
                # read_atがない場合は公開日で判定（フォールバック）
                should_keep = article.published >= cutoff_date
            
            if should_keep:
                filtered_articles.append(article)
        
        if len(filtered_articles) < len(articles):
            self.save_articles(filtered_articles)
            removed_count = len(articles) - len(filtered_articles)
            print(f"{removed_count}件の古い読み取り記録を削除しました")
