from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FeedItem:
    """フィード記事のデータクラス"""
    id: str
    title: str
    content: str
    url: str
    published: datetime
    source_feed: str
    processed: bool = False
    summary: Optional[str] = None
    posted_to_mastodon: bool = False
    read_at: Optional[datetime] = None  # 読み取り日時を追加


@dataclass
class FeedSource:
    """フィードソースのデータクラス"""
    url: str
    name: str
    enabled: bool = True
    last_checked: Optional[datetime] = None
