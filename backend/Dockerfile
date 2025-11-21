FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージの更新と必要なツールのインストール
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python依存パッケージのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY . .

# ポート8000を公開
EXPOSE 8000

# デフォルトコマンド（docker-compose.ymlで上書き可能）
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

