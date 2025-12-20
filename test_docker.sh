#!/bin/bash
set -e

echo "=== Docker環境テスト開始 ==="

# Dockerデーモンの確認
if ! docker info > /dev/null 2>&1; then
    echo "エラー: Dockerデーモンが起動していません。Docker Desktopを起動してください。"
    exit 1
fi

echo "✓ Dockerデーモンは起動しています"

# 既存のコンテナを停止・削除
echo "既存のコンテナを停止・削除中..."
docker-compose down 2>/dev/null || true

# イメージをビルド
echo "Webサービスのイメージをビルド中..."
docker-compose build web

# データベースを起動
echo "データベースを起動中..."
docker-compose up -d db

# データベースの準備を待つ
echo "データベースの準備を待機中（10秒）..."
sleep 10

# Webサービスを起動
echo "Webサービスを起動中..."
docker-compose up -d web

# 起動を待つ
echo "Webサービスの起動を待機中（15秒）..."
sleep 15

# ログを確認
echo ""
echo "=== Webサービスのログ（最後の30行） ==="
docker-compose logs --tail=30 web

# コンテナの状態確認
echo ""
echo "=== コンテナの状態 ==="
docker-compose ps

# 動作確認
echo ""
echo "=== 動作確認 ==="
echo "管理画面へのアクセス確認..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/admin/ | grep -q "200\|301\|302"; then
    echo "✓ 管理画面にアクセス可能"
else
    echo "✗ 管理画面にアクセスできません"
fi

echo ""
echo "APIエンドポイントへのアクセス確認..."
if curl -s http://localhost:8000/api/ | grep -q "api\|error\|detail"; then
    echo "✓ APIエンドポイントにアクセス可能"
else
    echo "✗ APIエンドポイントにアクセスできません"
fi

echo ""
echo "=== テスト完了 ==="
echo "詳細なログを確認するには: docker-compose logs -f web"
echo "コンテナを停止するには: docker-compose down"
