from mastodon import Mastodon
from typing import Optional


class MastodonService:
    """Mastodonへの投稿を管理するクラス"""
    
    def __init__(self, instance_url: str, access_token: str):
        try:
            self.mastodon = Mastodon(
                access_token=access_token,
                api_base_url=instance_url
            )
            print(f"Mastodonに接続しました: {instance_url}")
            
            # デバッグ用: 利用可能なメソッドを確認
            methods = [method for method in dir(self.mastodon) if not method.startswith('_')]
            auth_methods = [m for m in methods if 'credential' in m or 'verify' in m]
            post_methods = [m for m in methods if 'toot' in m or 'status' in m or 'post' in m]
            
            print(f"🔍 認証関連メソッド: {auth_methods}")
            print(f"🔍 投稿関連メソッド: {post_methods}")
            
        except Exception as e:
            print(f"Mastodon接続エラー: {e}")
            self.mastodon = None
    
    def post_toot(self, content: str, visibility: str = "public") -> bool:
        """投稿をMastodonに送信"""
        if not self.mastodon:
            print("Mastodonに接続されていません")
            return False
        
        # 公開範囲の検証
        valid_visibilities = ["public", "unlisted", "private", "direct"]
        if visibility not in valid_visibilities:
            print(f"無効な公開範囲: {visibility}. デフォルト(direct)を使用します")
            visibility = "direct"
        
        try:
            # バージョンによってメソッド名が異なる場合に対応
            if hasattr(self.mastodon, 'status_post'):
                result = self.mastodon.status_post(content, visibility=visibility)
            elif hasattr(self.mastodon, 'toot'):
                result = self.mastodon.toot(content, visibility=visibility)
            else:
                print("投稿メソッドが見つかりません")
                return False
                
            print(f"投稿完了 ({visibility}): {result['id']}")
            return True
            
        except Exception as e:
            print(f"投稿エラー: {e}")
            print(f"投稿内容: {content[:100]}...")
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
                print("認証確認メソッドが見つかりません")
                return False
                
            print(f"認証確認: @{account['username']}")
            return True
        except Exception as e:
            print(f"認証エラー: {e}")
            print("💡 以下を確認してください:")
            print("  - Mastodonアクセストークンが正しいか")
            print("  - トークンに必要な権限があるか (read, write)")
            print("  - インスタンスURLが正しいか")
            return False
