FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY *.py ./
COPY data/ ./data/

# データディレクトリのパーミッションを設定
RUN chmod 755 /app && chmod -R 755 /app/data

# 非rootユーザーを作成
RUN useradd -m -u 1000 feedbot && chown -R feedbot:feedbot /app
USER feedbot

# デフォルトコマンド
CMD ["python", "main.py"]
