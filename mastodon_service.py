from mastodon import Mastodon
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MastodonService:
    """Mastodonへの投稿を管理するクラス"""
    
    def __init__(self, instance_url: str, access_token: str):
        try:
            self.mastodon = Mastodon(
                access_token=access_token,
                api_base_url=instance_url
            )
            logger.info(f"Mastodonに接続しました: {instance_url}")
        except Exception as e:
            logger.error(f"Mastodon接続エラー: {e}")
            self.mastodon = None
    
    def post_toot(self, content: str, visibility: str = "public") -> bool:
        """投稿をMastodonに送信"""
        if not self.mastodon:
            logger.error("Mastodonに接続されていません")
            return False
        
        # 公開範囲の検証
        valid_visibilities = ["public", "unlisted", "private", "direct"]
        if visibility not in valid_visibilities:
            logger.warning(f"無効な公開範囲: {visibility}. デフォルト(direct)を使用します")
            visibility = "direct"
        
        try:
            # バージョンによってメソッド名が異なる場合に対応
            if hasattr(self.mastodon, 'status_post'):
                result = self.mastodon.status_post(content, visibility=visibility)
            elif hasattr(self.mastodon, 'toot'):
                result = self.mastodon.toot(content, visibility=visibility)
            else:
                logger.error("投稿メソッドが見つかりません")
                return False
                
            logger.info(f"投稿完了 ({visibility}): {result['id']}")
            return True
            
        except Exception as e:
            logger.error(f"投稿エラー: {e}")
            logger.debug(f"投稿内容: {content[:100]}...")
            return False
    
    def verify_credentials(self) -> bool:
        """認証情報の確認"""
        if not self.mastodon:
            return False
        
        try:
            # バージョンによってメソッド名が異なる場合に対応
            if hasattr(self.mastodon, 'account_verify_credentials'):
                account = self.mastodon.account_verify_credentials()
            elif hasattr(self.mastodon, 'verify_credentials'):
                account = self.mastodon.verify_credentials()
            else:
                logger.error("認証確認メソッドが見つかりません")
                return False
                
            logger.info(f"認証確認: @{account['username']}")
            return True
        except Exception as e:
            logger.error(f"認証エラー: {e}")
            logger.error("以下を確認してください: "
                        "Mastodonアクセストークンが正しいか / "
                        "トークンに必要な権限(read, write)があるか / "
                        "インスタンスURLが正しいか")
            return False
