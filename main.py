#!/usr/bin/env python3
"""
Tsukino Feedbot - AIを活用したフィード要約・Mastodon投稿ボット
"""

import os
import time
from datetime import datetime, timedelta
from typing import List

# 設定の読み込みを試行
try:
    import config
except ImportError:
    print("設定ファイル config.py が見つかりません。")
    print("config.example.py を config.py にコピーして使用してください。")
    exit(1)

from storage import DataStorage
from feed_reader import FeedReader
from ai_service import AIService
from mastodon_service import MastodonService
from models import FeedItem, FeedSource


class FeedBot:
    """フィードボットのメインクラス"""
    
    def __init__(self):
        self.storage = DataStorage()
        self.feed_reader = FeedReader()
        self.ai_service = AIService(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
        self.mastodon_service = MastodonService(
            config.MASTODON_INSTANCE_URL,
            config.MASTODON_ACCESS_TOKEN
        )
        
        # 初回起動時にフィードソースを設定から読み込み
        self._initialize_feed_sources()
    
    def _is_quiet_hours(self) -> bool:
        """現在が投稿禁止時間帯かどうかを判定"""
        if not config.ENABLE_QUIET_HOURS:
            return False
        
        now = datetime.now()
        current_hour = now.hour
        start = config.QUIET_HOURS_START
        end = config.QUIET_HOURS_END
        
        if start <= end:
            # 日をまたがない場合（例: 9-17）
            return start <= current_hour < end
        else:
            # 日をまたぐ場合（例: 23-7）
            return current_hour >= start or current_hour < end
    
    def _initialize_feed_sources(self):
        """設定からフィードソースを初期化"""
        existing_sources = self.storage.load_feed_sources()
        existing_urls = {source.url for source in existing_sources}
        
        # 設定ファイルに定義されたフィードURL
        config_urls = {feed_config["url"] for feed_config in config.FEED_URLS}
        
        sources_updated = False
        
        if not existing_sources:
            # 初回初期化：設定からフィードソースを作成
            sources = []
            for feed_config in config.FEED_URLS:
                source = FeedSource(
                    url=feed_config["url"],
                    name=feed_config["name"]
                )
                sources.append(source)
            
            self.storage.save_feed_sources(sources)
            print(f"{len(sources)}個のフィードソースを初期化しました")
        else:
            # 設定ファイルにある新しいフィードを追加
            new_feeds = []
            for feed_config in config.FEED_URLS:
                if feed_config["url"] not in existing_urls:
                    new_feed = FeedSource(
                        url=feed_config["url"],
                        name=feed_config["name"]
                    )
                    existing_sources.append(new_feed)
                    new_feeds.append(new_feed)
                    sources_updated = True
            
            # 設定ファイルから削除されたフィードを無効化（削除はしない）
            removed_feeds = []
            for source in existing_sources:
                if source.url not in config_urls and source.enabled:
                    source.enabled = False
                    removed_feeds.append(source)
                    sources_updated = True
            
            if sources_updated:
                self.storage.save_feed_sources(existing_sources)
                if new_feeds:
                    print(f"{len(new_feeds)}個の新しいフィードソースを追加しました:")
                    for feed in new_feeds:
                        print(f"  - {feed.name}: {feed.url}")
                if removed_feeds:
                    print(f"{len(removed_feeds)}個のフィードソースを無効化しました:")
                    for feed in removed_feeds:
                        print(f"  - {feed.name}: {feed.url}")
            else:
                print("フィードソースの変更はありませんでした")
    
    def check_feeds(self):
        """フィードをチェックして新着記事を処理"""
        print(f"フィードチェック開始: {datetime.now()}")
        
        # 投稿禁止時間帯チェック
        if self._is_quiet_hours():
            print("現在は投稿禁止時間帯です。フィード取得をスキップします。")
            return
        
        # 既存記事の読み込み
        existing_articles = self.storage.load_articles()
        existing_ids = {article.id for article in existing_articles}
        
        # フィードソースの読み込み
        feed_sources = self.storage.load_feed_sources()
        new_articles = []
        
        for source in feed_sources:
            if not source.enabled:
                continue
            
            # フィードから記事を取得
            feed_items = self.feed_reader.fetch_feed_items(source)            # 新着記事のフィルタリング
            for item in feed_items:
                # 既読チェック
                if item.id in existing_ids:
                    continue
                
                # 日付チェック（指定期間内のみ）
                cutoff_date = datetime.now() - timedelta(days=config.ARTICLE_RETENTION_DAYS)
                if item.published < cutoff_date:
                    continue
                
                # 読み取り日時を設定
                item.read_at = datetime.now()
                new_articles.append(item)
            
            # フィードソースの最終チェック時刻を更新
            source.last_checked = datetime.now()
        
        # フィードソースの保存
        self.storage.save_feed_sources(feed_sources)
        
        print(f"{len(new_articles)}件の新着記事を発見")
        
        # 新着記事の処理
        if new_articles:
            self._process_new_articles(new_articles)
            
            # 記事の保存
            all_articles = existing_articles + new_articles
            self.storage.save_articles(all_articles)
        
        # 古い記事のクリーンアップ（通常のクリーンアップ）
        self.storage.cleanup_old_articles(config.ARTICLE_RETENTION_DAYS)
        
        # 古い読み取り記録のクリーンアップ（より積極的に削除）
        read_record_retention_days = getattr(config, 'READ_RECORD_RETENTION_DAYS', config.ARTICLE_RETENTION_DAYS // 2)
        self.storage.cleanup_old_read_records(read_record_retention_days)
        
        print("フィードチェック完了")
    
    def _process_new_articles(self, articles: List[FeedItem]):
        """新着記事を処理（要約生成とMastodon投稿）"""
        for article in articles:
            print(f"記事処理中: {article.title}")
            
            # AI要約の生成
            summary = self.ai_service.generate_summary(
                article.title,
                article.content,
                config.SUMMARY_PROMPT
            )
            
            if summary:
                article.summary = summary
                article.processed = True
                
                # Mastodon投稿の準備
                post_content = config.POST_TEMPLATE.format(
                    summary=summary,
                    title=article.title,
                    url=article.url
                )
                
                # Mastodonに投稿
                if self.mastodon_service.post_toot(post_content, config.POST_VISIBILITY):
                    article.posted_to_mastodon = True
                    print(f"投稿完了: {article.title}")
                else:
                    print(f"投稿失敗: {article.title}")
            else:
                print(f"要約生成失敗: {article.title}")
            
            # APIレート制限対策で少し待機
            time.sleep(2)
    
    def run_once(self):
        """一回だけフィードチェックを実行"""
        print("=== Tsukino Feedbot 単発実行 ===")
        
        # Mastodon認証確認
        if not self.mastodon_service.verify_credentials():
            print("Mastodon認証に失敗しました。設定を確認してください。")
            return
        
        self.check_feeds()
    
    def run_continuous(self):
        """継続的にフィードをチェック"""
        print("=== Tsukino Feedbot 継続実行開始 ===")
        print(f"チェック間隔: {config.CHECK_INTERVAL_MINUTES}分")
        
        # Mastodon認証確認
        if not self.mastodon_service.verify_credentials():
            print("Mastodon認証に失敗しました。設定を確認してください。")
            return
        
        try:
            while True:
                # 静音時間帯チェック
                if self._is_quiet_hours():
                    print("現在は静音時間帯です。次のチェックまで待機します。")
                    time.sleep(60)  # 1分待機してから再チェック
                    continue
                
                self.check_feeds()
                
                print(f"次のチェックまで{config.CHECK_INTERVAL_MINUTES}分待機...")
                time.sleep(config.CHECK_INTERVAL_MINUTES * 60)
                
        except KeyboardInterrupt:
            print("\n終了が要求されました。")
    
    def show_status(self):
        """現在の状況を表示"""
        articles = self.storage.load_articles()
        sources = self.storage.load_feed_sources()
        
        # 日付別の統計
        now = datetime.now()
        today_articles = [a for a in articles if a.read_at and a.read_at.date() == now.date()]
        week_articles = [a for a in articles if a.read_at and a.read_at >= now - timedelta(days=7)]
        
        print("=== Tsukino Feedbot ステータス ===")
        print(f"フィードソース数: {len(sources)}")
        print(f"保存記事数: {len(articles)}")
        print(f"処理済み記事数: {len([a for a in articles if a.processed])}")
        print(f"投稿済み記事数: {len([a for a in articles if a.posted_to_mastodon])}")
        print(f"本日読み取り記事数: {len(today_articles)}")
        print(f"過去7日間読み取り記事数: {len(week_articles)}")
        
        # 時間帯制限の状況表示
        if config.ENABLE_QUIET_HOURS:
            quiet_status = "投稿禁止時間帯" if self._is_quiet_hours() else "投稿可能時間帯"
            print(f"時間帯制限: 有効 ({config.QUIET_HOURS_START}:00-{config.QUIET_HOURS_END}:00) - 現在: {quiet_status}")
        else:
            print("時間帯制限: 無効")
        
        print("\nフィードソース:")
        for source in sources:
            status = "有効" if source.enabled else "無効"
            last_check = source.last_checked.strftime("%Y-%m-%d %H:%M") if source.last_checked else "未チェック"
            print(f"  - {source.name} ({status}) - 最終チェック: {last_check}")


def main():
    """メイン関数"""
    print("=== Tsukino Feedbot 初期化中 ===")
    
    # 環境変数チェック
    required_env_vars = [
        'OPENROUTER_API_KEY',
        'MASTODON_INSTANCE_URL', 
        'MASTODON_ACCESS_TOKEN',
        'CHECK_INTERVAL_MINUTES',
        'ARTICLE_RETENTION_DAYS'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 必要な環境変数が設定されていません: {', '.join(missing_vars)}")
        print("💡 .env ファイルを確認してください。")
        return
    
    try:
        bot = FeedBot()
    except Exception as e:
        print(f"❌ ボット初期化エラー: {e}")
        return
    
    print("✅ 初期化完了")
    
    # Docker環境での入力問題を回避するため、環境変数でモード指定可能にする
    run_mode = os.getenv("RUN_MODE", "interactive")
    
    if run_mode == "once":
        print("🚀 ワンショット実行モード")
        bot.run_once()
        return
    elif run_mode == "daemon":
        print("🔄 デーモンモード")
        bot.run_continuous()
        return
    elif run_mode == "status":
        print("📊 ステータス確認モード")
        bot.show_status()
        return
    elif run_mode == "cleanup":
        print("🧹 クリーンアップモード")
        bot.storage.cleanup_old_articles(config.ARTICLE_RETENTION_DAYS)
        read_record_days = getattr(config, 'READ_RECORD_RETENTION_DAYS', 3)
        bot.storage.cleanup_old_read_records(read_record_days)
        print("✅ クリーンアップ完了")
        return
    
    # インタラクティブモード
    print("\n=== Tsukino Feedbot メニュー ===")
    print("1. 一回だけ実行")
    print("2. 継続実行")
    print("3. ステータス確認")
    print("4. フィード設定の同期")
    print("5. データクリーンアップ")
    print("6. 終了")
    print("\n💡 Docker環境では環境変数 RUN_MODE でも実行可能:")
    print("   RUN_MODE=once    # ワンショット実行")
    print("   RUN_MODE=daemon  # デーモン実行")
    print("   RUN_MODE=status  # ステータス確認")
    print("   RUN_MODE=cleanup # クリーンアップ")
    
    while True:
        try:
            print("\n" + "="*50)
            
            # より堅牢な入力処理
            try:
                choice = input("選択してください (1-6): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 終了します。")
                break
            except Exception as e:
                print(f"⚠️  入力エラー: {e}")
                print("💡 Docker環境では環境変数での実行を推奨します")
                choice = "5"  # 自動終了
            
            if choice == "1":
                print("🚀 ワンショット実行を開始...")
                bot.run_once()
                break
            elif choice == "2":
                print("🔄 継続実行を開始...")
                bot.run_continuous()
                break
            elif choice == "3":
                print("📊 ステータス確認中...")
                bot.show_status()
            elif choice == "4":
                print("🔄 フィード設定を同期中...")
                bot._initialize_feed_sources()
            elif choice == "5":
                print("🧹 データクリーンアップを実行中...")
                bot.storage.cleanup_old_articles(config.ARTICLE_RETENTION_DAYS)
                read_record_days = getattr(config, 'READ_RECORD_RETENTION_DAYS', 3)
                bot.storage.cleanup_old_read_records(read_record_days)
                print("✅ クリーンアップ完了")
            elif choice == "6":
                print("👋 終了します。")
                break
            else:
                print("❌ 無効な選択です。1-6を選択してください。")
                
        except KeyboardInterrupt:
            print("\n👋 終了が要求されました。")
            break
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            break


if __name__ == "__main__":
    main()
