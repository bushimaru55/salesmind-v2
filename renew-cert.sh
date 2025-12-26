#!/bin/bash

# Let's Encrypt証明書の更新スクリプト

echo "証明書の更新を試みます..."

# 証明書を更新
docker compose run --rm certbot renew

# nginxをリロードして新しい証明書を読み込む
docker compose exec frontend nginx -s reload

echo "証明書の更新が完了しました。"




