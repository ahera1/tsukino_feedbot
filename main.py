#!/usr/bin/env python3
"""
Tsukino Feedbot - AIを活用したフィード要約・Mastodon投稿ボット
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime, timedelta, timezone
from typing import List
from pathlib import Path

# 設定の読み込みを試行
try:
    import config
except ImportError:
    print("設定ファイル config.py が見つかりません。")
    print("config.example.py を config.py にコピーして使用してください。")
    exit(1)

from storage import DataStorage
from feed_reader import FeedReader
from ai_service import create_ai_service_manager
from mastodon_service import MastodonService
from models import FeedItem, FeedSource


def setup_logging():
    """ログ設定を初期化"""
    log_level = getattr(config, 'LOG_LEVEL', 'INFO')
    log_to_file = getattr(config, 'LOG_TO_FILE', True)
    log_file_level = getattr(config, 'LOG_FILE_LEVEL', 'DEBUG')
    log_file_retention = getattr(config, 'LOG_FILE_RETENTION_DAYS', 14)
    
    # ログフォーマットの設定
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ルートロガーの設定（最も低いレベルに設定し、ハンドラー側で制御）
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 既存のハンドラーをクリア
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # コンソールハンドラー（stdout = docker logs向け、INFO以上）
    console_level = getattr(logging, log_level.upper(), logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラー（日付ローテーション、DEBUG含む全ログ）
    if log_to_file:
        from logging.handlers import TimedRotatingFileHandler
        
        logs_dir = Path('logs')
        logs_dir.mkdir(exist_ok=True)
        
        file_handler = TimedRotatingFileHandler(
            filename=logs_dir / 'feedbot.log',
            when='midnight',
            interval=1,
            backupCount=log_file_retention,
            encoding='utf-8'
        )
        file_handler.suffix = "%Y%m%d"
        file_level = getattr(logging, log_file_level.upper(), logging.DEBUG)
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 外部ライブラリのログレベル調整
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"ログ設定完了 - コンソール: {log_level}, "
                f"ファイル: {'有効 (' + log_file_level + ')' if log_to_file else '無効'}")
    
    return logger


class FeedBot:
    """フィードボットのメインクラス"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.storage = DataStorage()
        self.feed_reader = FeedReader()
        self.ai_service = create_ai_service_manager(config.AI_CONFIGS)
        self.mastodon_service = MastodonService(
            config.MASTODON_INSTANCE_URL,
            config.MASTODON_ACCESS_TOKEN
        )
        
        # 中断フラグ（シグナル受信時に設定）
        self.shutdown_requested = False
        
        # 初回起動時にフィードソースを設定から読み込み
        self._initialize_feed_sources()
        
        # シグナルハンドラーの設定
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
    
    def _handle_shutdown_signal(self, signum, frame):
        """シャットダウンシグナルを受信したときの処理"""
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        self.logger.warning(f"{signal_name}を受信しました。処理中の記事を完了後に停止します")
        self.shutdown_requested = True
    
    def _is_quiet_hours(self) -> bool:
        """現在が投稿禁止時間帯かどうかを判定"""
        if not config.ENABLE_QUIET_HOURS:
            return False
        
        # ローカル時間で判定（設定された時間帯はローカル時間ベース）
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
            self.logger.info(f"{len(sources)}個のフィードソースを初期化しました")
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
                    self.logger.info(f"{len(new_feeds)}個の新しいフィードソースを追加しました")
                    for feed in new_feeds:
                        self.logger.info(f"  - {feed.name}: {feed.url}")
                if removed_feeds:
                    self.logger.info(f"{len(removed_feeds)}個のフィードソースを無効化しました")
                    for feed in removed_feeds:
                        self.logger.info(f"  - {feed.name}: {feed.url}")
            else:
                self.logger.debug("フィードソースの変更はありませんでした")
    
    def check_feeds(self):
        """フィードをチェックして新着記事を処理"""
        self.logger.info("フィードチェック開始")
        
        # 投稿禁止時間帯チェック
        if self._is_quiet_hours():
            self.logger.info("現在は投稿禁止時間帯です。フィード取得をスキップします。")
            return
        
        # 既存記事の読み込み
        existing_articles = self.storage.load_articles()
        existing_ids = {article.id for article in existing_articles}
        
        self.logger.info(f"既存記事数: {len(existing_articles)}, 既存ID数: {len(existing_ids)}")
        
        # フィードソースの読み込み
        feed_sources = self.storage.load_feed_sources()
        new_articles = []
        
        self.logger.info(f"{len(feed_sources)}個のフィードソースを処理開始")
        
        for source in feed_sources:
            if not source.enabled:
                continue
            
            self.logger.info(f"フィード取得開始: {source.name} ({source.url})")
            
            # フィードから記事を取得
            feed_items = self.feed_reader.fetch_feed_items(source)
            
            self.logger.debug(f"フィード取得完了: {source.name} - {len(feed_items)}件")
            
            # 新着記事のフィルタリング
            skip_read = 0
            skip_old = 0
            new_count = 0
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=config.ARTICLE_RETENTION_DAYS)
            
            for item in feed_items:
                # 既読チェック（IDが存在する場合はスキップ）
                if item.id in existing_ids:
                    self.logger.debug(f"既読記事をスキップ: {item.title[:50]}...")
                    skip_read += 1
                    continue
                
                # 日付チェック（指定期間内のみ）
                published_time = item.published
                if published_time.tzinfo is None:
                    published_time = published_time.replace(tzinfo=timezone.utc)
                
                if published_time < cutoff_date:
                    self.logger.debug(f"古い記事をスキップ: {item.title} (公開日: {item.published})")
                    skip_old += 1
                    continue
                
                # 新着記事として追加（読み取り日時は処理時に設定）
                new_articles.append(item)
                new_count += 1
                self.logger.debug(f"新着記事発見: {item.title}")
            
            # フィードソースの処理サマリー
            self.logger.info(f"{source.name}: 新着{new_count}件, スキップ(既読:{skip_read}件, 古い:{skip_old}件)")
            
            # フィードソースの最終チェック時刻を更新
            source.last_checked = datetime.now(timezone.utc)
        
        # フィードソースの保存
        self.storage.save_feed_sources(feed_sources)
        
        self.logger.info(f"{len(new_articles)}件の新着記事を発見")
        
        # 新着記事を1件ずつ処理して都度保存（中断時の既読化問題を回避）
        if new_articles:
            self.logger.info(f"{len(new_articles)}件の新着記事を順次処理開始")
            
            for i, article in enumerate(new_articles, 1):
                # 中断要求チェック（次の記事処理前）
                if self.shutdown_requested:
                    remaining = len(new_articles) - i + 1
                    self.logger.warning(f"中断要求により停止。残り{remaining}件は未処理")
                    break
                
                # 処理直前に read_at を設定（この記事だけを既読化）
                article.read_at = datetime.now(timezone.utc)
                
                # 既存記事に追加して保存（この記事だけ既読化）
                existing_articles.append(article)
                self.storage.save_articles(existing_articles)
                self.logger.info(f"記事保存完了 ({i}/{len(new_articles)}): {article.title[:50]}...")
                
                # AI処理とMastodon投稿（待機なし）
                self._process_single_article(article, i, len(new_articles), wait=False)
                
                # 処理結果を反映して再保存
                self.storage.save_articles(existing_articles)
                self.logger.info(f"AI処理結果を反映して再保存 ({i}/{len(new_articles)}): {article.title}")
                
                # 次の記事処理前の待機（最後の記事以外、ループ制御下で実行）
                if i < len(new_articles):
                    wait_time = getattr(config, 'POST_WAIT', 60)
                    self.logger.debug(f"次の記事処理まで{wait_time}秒待機")
                    
                    # 待機を1秒ごとに分割して中断チェック
                    for _ in range(wait_time):
                        if self.shutdown_requested:
                            self.logger.warning("待機中に中断要求を受信")
                            break
                        time.sleep(1)
        
        # 古い記事のクリーンアップ（通常のクリーンアップ）
        cleaned_count = self.storage.cleanup_old_articles(config.ARTICLE_RETENTION_DAYS)
        if cleaned_count > 0:
            self.logger.info(f"古い記事を{cleaned_count}件クリーンアップ")
        
        # 古い読み取り記録のクリーンアップ（より積極的に削除）
        read_record_retention_days = getattr(config, 'READ_RECORD_RETENTION_DAYS', config.ARTICLE_RETENTION_DAYS // 2)
        read_cleaned_count = self.storage.cleanup_old_read_records(read_record_retention_days)
        if read_cleaned_count > 0:
            self.logger.info(f"古い読み取り記録を{read_cleaned_count}件クリーンアップ")
        
        self.logger.info("フィードチェック完了")
    
    def _process_single_article(self, article: FeedItem, current: int, total: int, wait: bool = True):
        """1件の記事を処理（要約生成とMastodon投稿）"""
        self.logger.info(f"記事処理開始 ({current}/{total}): {article.title[:50]}...")
        
        # AI要約の生成
        try:
            summary = self.ai_service.generate_summary(
                article.title,
                article.content,
                config.AI_USER_PROMPT_TEMPLATE
            )
            self.logger.info(f"AI要約生成完了: {article.title} (ID: {article.id})")
            self.logger.debug(f"要約内容: {summary}")
        except Exception as e:
            self.logger.error(f"AI要約生成エラー ({current}/{total}): {article.title[:50]}... - {str(e)}", exc_info=True)
            summary = None
        
        if summary:
            article.summary = summary
            article.processed = True
            
            # Mastodon投稿の準備
            post_content = config.POST_TEMPLATE.format(
                summary=summary,
                title=article.title,
                url=article.url
            )
            
            self.logger.debug(f"Mastodon投稿内容: {post_content}")
            
            # Mastodonに投稿
            if self.mastodon_service.post_toot(post_content, config.POST_VISIBILITY):
                article.posted_to_mastodon = True
                self.logger.info(f"Mastodon投稿完了 ({current}/{total}): {article.title[:50]}...")
            else:
                self.logger.warning(f"Mastodon投稿失敗 ({current}/{total}): {article.title[:50]}...")
                article.processed = True  # 要約は成功したので処理済みとマーク
        else:
            self.logger.warning(f"要約生成失敗 ({current}/{total}): {article.title[:50]}... - 記事は保存済み、要約なし")
        
        # 待機処理は呼び出し側で制御（wait=Falseの場合はスキップ）
        if wait and current < total:
            wait_time = getattr(config, 'POST_WAIT', 60)
            self.logger.debug(f"次の記事処理まで{wait_time}秒待機")
            time.sleep(wait_time)
    
    def run_once(self):
        """一回だけフィードチェックを実行"""
        self.logger.info("Tsukino Feedbot 単発実行開始")
        
        # Mastodon認証確認
        if not self.mastodon_service.verify_credentials():
            self.logger.error("Mastodon認証に失敗しました。設定を確認してください。")
            return
        
        self.check_feeds()
    
    def run_continuous(self):
        """継続的にフィードをチェック"""
        self.logger.info(f"Tsukino Feedbot 継続実行開始 (チェック間隔: {config.CHECK_INTERVAL_MINUTES}分)")
        
        # Mastodon認証確認
        if not self.mastodon_service.verify_credentials():
            self.logger.error("Mastodon認証に失敗しました。設定を確認してください。")
            return
        
        try:
            while True:
                # 静音時間帯チェック
                if self._is_quiet_hours():
                    self.logger.info("現在は静音時間帯です。10分後に再チェックします。")
                    time.sleep(600)
                    continue
                
                self.check_feeds()
                
                self.logger.info(f"次のチェックまで{config.CHECK_INTERVAL_MINUTES}分待機...")
                time.sleep(config.CHECK_INTERVAL_MINUTES * 60)
                
        except KeyboardInterrupt:
            self.logger.info("終了が要求されました。")
    
    def show_status(self):
        """現在の状況を表示"""
        articles = self.storage.load_articles()
        sources = self.storage.load_feed_sources()
        
        # 日付別の統計
        now = datetime.now(timezone.utc)
        today_articles = [a for a in articles if a.read_at and a.read_at.date() == now.date()]
        week_articles = [a for a in articles if a.read_at and a.read_at >= now - timedelta(days=7)]
        
        print("=== Tsukino Feedbot ステータス ===")
        print(f"フィードソース数: {len(sources)}")
        print(f"保存記事数: {len(articles)}")
        print(f"処理済み記事数: {len([a for a in articles if a.processed])}")
        print(f"投稿済み記事数: {len([a for a in articles if a.posted_to_mastodon])}")
        print(f"本日読み取り記事数: {len(today_articles)}")
        print(f"過去7日間読み取り記事数: {len(week_articles)}")
        
        # データファイルの状態確認
        articles_file = self.storage.articles_file
        feeds_file = self.storage.feeds_file
        print(f"\nデータファイル状態:")
        print(f"  articles.json: 存在={articles_file.exists()}, サイズ={articles_file.stat().st_size if articles_file.exists() else 0}bytes")
        print(f"  feeds.json: 存在={feeds_file.exists()}, サイズ={feeds_file.stat().st_size if feeds_file.exists() else 0}bytes")
        
        # 時間帯制限の状況表示
        if config.ENABLE_QUIET_HOURS:
            quiet_status = "投稿禁止時間帯" if self._is_quiet_hours() else "投稿可能時間帯"
            print(f"時間帯制限: 有効 ({config.QUIET_HOURS_START}:00-{config.QUIET_HOURS_END}:00) - 現在: {quiet_status}")
        else:
            print("時間帯制限: 無効")
        
        # ウェイト設定の表示
        post_wait = getattr(config, 'POST_WAIT', 10)
        print(f"投稿処理間ウェイト: {post_wait}秒")
        
        print("\nフィードソース:")
        for source in sources:
            status = "有効" if source.enabled else "無効"
            last_check = source.last_checked.strftime("%Y-%m-%d %H:%M") if source.last_checked else "未チェック"
            print(f"  - {source.name} ({status}) - 最終チェック: {last_check}")


def main():
    """メイン関数"""
    # ログ設定の初期化
    logger = setup_logging()
    logger.info("Tsukino Feedbot 初期化中")
    
    # 環境変数チェック
    required_env_vars = [
        'OPENROUTER_API_KEY',
        'MASTODON_INSTANCE_URL', 
        'MASTODON_ACCESS_TOKEN',
        'CHECK_INTERVAL_MINUTES',
        'ARTICLE_RETENTION_DAYS',
        'READ_RECORD_RETENTION_DAYS'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"必要な環境変数が設定されていません: {', '.join(missing_vars)}")
        logger.error(".env ファイルを確認してください。")
        return
    
    try:
        bot = FeedBot()
        logger.info("FeedBot初期化完了")
    except Exception as e:
        logger.error(f"ボット初期化エラー: {e}", exc_info=True)
        return
    
    logger.info("初期化完了")
    
    # Docker環境での入力問題を回避するため、環境変数でモード指定可能にする
    run_mode = os.getenv("RUN_MODE", "interactive")
    
    if run_mode == "once":
        logger.info("ワンショット実行モード開始")
        bot.run_once()
        logger.info("ワンショット実行モード完了")
        return
    elif run_mode == "daemon":
        logger.info("デーモンモード開始")
        bot.run_continuous()
        logger.info("デーモンモード終了")
        return
    elif run_mode == "status":
        logger.info("ステータス確認モード")
        bot.show_status()
        return
    elif run_mode == "cleanup":
        logger.info("クリーンアップモード開始")
        bot.storage.cleanup_old_articles(config.ARTICLE_RETENTION_DAYS)
        read_record_days = getattr(config, 'READ_RECORD_RETENTION_DAYS', 3)
        bot.storage.cleanup_old_read_records(read_record_days)
        logger.info("クリーンアップ完了")
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
            logger.error(f"エラーが発生しました: {e}")
            break


if __name__ == "__main__":
    main()
