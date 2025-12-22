#!/bin/bash

# Let's Encrypt証明書を取得・更新するスクリプト

DOMAIN="salesmind.mind-bridge.tech"
EMAIL="admin@mind-bridge.tech"  # Let's Encryptからの通知用メールアドレス（必要に応じて変更してください）

# 証明書が既に存在するか確認
CERT_EXISTS=$(docker compose run --rm certbot certificates 2>/dev/null | grep -c "$DOMAIN" || echo "0")

if [ "$CERT_EXISTS" -gt 0 ]; then
    echo "証明書は既に存在します。更新を試みます..."
    docker compose run --rm certbot renew
    docker compose exec frontend nginx -s reload
    echo "証明書の更新が完了しました。"
else
    echo "証明書が存在しません。新規に取得します..."
    echo "初回証明書取得用のnginx設定に切り替えます..."
    
    # 初回証明書取得用のnginx設定を使用
    if [ -f "nginx.conf" ] && [ ! -f "nginx.conf.backup" ]; then
        cp nginx.conf nginx.conf.backup
    fi
    cp nginx.conf.init nginx.conf
    docker compose restart frontend
    sleep 5
    
    echo "証明書を取得しています..."
    # 証明書を取得（webroot方式）
    docker compose run --rm certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        -d $DOMAIN
    
    if [ $? -eq 0 ]; then
        echo "証明書の取得が完了しました。HTTPS用のnginx設定に切り替えます..."
        # HTTPS用のnginx設定を復元
        if [ -f "nginx.conf.backup" ]; then
            mv nginx.conf.backup nginx.conf
        else
            echo "警告: nginx.conf.backupが見つかりません。"
            echo "手動でnginx.confをHTTPS設定に更新してください。"
            echo "現在のnginx.conf.initをベースに、SSL証明書のパスを追加してください。"
            exit 1
        fi
        docker compose restart frontend
        sleep 3
        echo "SSL証明書の設定が完了しました。"
        echo "https://$DOMAIN でアクセスできることを確認してください。"
    else
        echo "証明書の取得に失敗しました。nginx設定を元に戻します..."
        if [ -f "nginx.conf.backup" ]; then
            mv nginx.conf.backup nginx.conf
            docker compose restart frontend
        fi
        exit 1
    fi
fi

