# Tsukino Feedbot - Docker コマンド集

## 基本操作

### 初回セットアップ
```bash
# 環境変数ファイル作成
copy .env.example .env

# .env ファイルを編集してAPIキー等を設定
```

### 実行方法

#### インタラクティブモード（推奨）
```bash
docker-compose up --build
```
- メニューから操作を選択
- Ctrl+C で停止

#### デーモンモード（本番運用）
```bash
# バックグラウンド実行開始
docker-compose --profile daemon up -d --build

# ログ確認
docker-compose logs -f tsukino-feedbot-daemon

# 停止
docker-compose --profile daemon down
```

#### ワンショット実行
```bash
# 一回だけフィードチェック
docker-compose run --rm tsukino-feedbot python -c "from main import FeedBot; bot = FeedBot(); bot.run_once()"
```

#### ステータス確認
```bash
# 現在の状況確認
docker-compose run --rm tsukino-feedbot python -c "from main import FeedBot; bot = FeedBot(); bot.show_status()"
```

#### データクリーンアップ
```bash
# 手動クリーンアップ実行
docker-compose run --rm tsukino-feedbot python -c "
from main import FeedBot
import config
bot = FeedBot()
bot.storage.cleanup_old_articles(config.ARTICLE_RETENTION_DAYS)
bot.storage.cleanup_old_read_records(config.READ_RECORD_RETENTION_DAYS)
print('クリーンアップ完了')
"
```

## トラブルシューティング

### Mastodon投稿エラーの場合

#### 1. 認証情報の確認
```bash
# デバッグ情報付きでワンショット実行
docker-compose --profile once up --build
```

#### 2. Mastodonアクセストークンの確認項目
- **インスタンスURL**: `https://your.mastodon.instance` (末尾にスラッシュなし)
- **アクセストークン**: Mastodonの設定 > 開発 > アプリケーションで作成
- **必要な権限**: `read` および `write` 権限が必要

#### 3. 手動でアクセストークンを取得する方法
1. Mastodonインスタンスにログイン
2. 設定 > 開発 > アプリケーション
3. 「新しいアプリケーション」を作成
4. 権限で `read` と `write` にチェック
5. 生成されたアクセストークンを `.env` に設定

### コンテナ状態確認
```bash
# 実行中のコンテナ確認
docker-compose ps

# すべてのコンテナ確認
docker-compose ps -a
```

### ログ確認
```bash
# インタラクティブモードのログ
docker-compose logs tsukino-feedbot

# デーモンモードのログ
docker-compose logs tsukino-feedbot-daemon

# リアルタイムログ監視
docker-compose logs -f tsukino-feedbot-daemon
```

### データ確認
```bash
# データディレクトリ確認
ls -la data/

# 記事データ確認（JSON整形して表示）
docker-compose run --rm tsukino-feedbot python -c "
import json
with open('data/articles.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f'記事数: {len(data)}')
for i, article in enumerate(data[:5]):  # 最新5件
    print(f'{i+1}. {article[\"title\"][:50]}...')
"
```

### 完全リセット
```bash
# 全コンテナ停止・削除
docker-compose down
docker-compose --profile daemon down

# 全データ削除（注意：データが消えます）
rm -rf data/* logs/*

# イメージ再ビルド
docker-compose build --no-cache
```
