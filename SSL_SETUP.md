# Let's Encrypt SSL証明書の設定手順

## 概要

このプロジェクトでは、Let's Encryptを使用してSSL証明書を取得・管理します。

## 初回設定手順

### 1. 前提条件

- ドメイン `salesmind.mind-bridge.tech` がこのサーバーを指していること
- ポート80と443が開放されていること
- Docker Composeがインストールされていること

### 2. 証明書の取得

初回証明書取得時は、以下の手順を実行してください：

```bash
# 1. 初回証明書取得用のnginx設定を使用（証明書が存在しないため）
cp nginx.conf.init nginx.conf

# 2. nginxを再起動
docker compose restart frontend

# 3. 証明書を取得
./init-letsencrypt.sh
```

または、手動で証明書を取得する場合：

```bash
docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email admin@mind-bridge.tech \
    --agree-tos \
    --no-eff-email \
    -d salesmind.mind-bridge.tech
```

証明書取得後、`nginx.conf`をHTTPS設定に戻してください：

```bash
# nginx.confがバックアップされている場合は復元
mv nginx.conf.backup nginx.conf

# または、nginx.confを手動でHTTPS設定に更新

# nginxを再起動
docker compose restart frontend
```

## 証明書の更新

証明書は自動的に更新されますが、手動で更新する場合は以下のコマンドを実行してください：

```bash
./renew-cert.sh
```

または：

```bash
docker compose run --rm certbot renew
docker compose exec frontend nginx -s reload
```

## 自動更新の設定

証明書の自動更新は、certbotのデフォルトの更新メカニズムを使用します。証明書は有効期限の30日前に自動的に更新されます。

cronジョブを設定する場合は、以下のように設定してください：

```bash
# crontab -e
0 3 * * * cd /opt/salesmind && ./renew-cert.sh >> /var/log/certbot-renew.log 2>&1
```

## トラブルシューティング

### 証明書が取得できない

- ドメインが正しくこのサーバーを指しているか確認してください
- ポート80が開放されているか確認してください
- nginxが正常に起動しているか確認してください

### nginxが起動しない

証明書が存在しない状態でHTTPS設定のnginx.confを使用している場合、nginxは起動できません。
初回証明書取得時には、`nginx.conf.init`を使用してください。

### 証明書の更新に失敗する

- 証明書の有効期限を確認してください：`docker compose run --rm certbot certificates`
- ログを確認してください：`docker compose logs certbot`


