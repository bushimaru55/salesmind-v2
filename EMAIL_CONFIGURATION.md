# メール設定ガイド（Djangoから直接外部SMTPを使用）

## 概要

Djangoから直接外部SMTPサーバー（Gmail、SendGrid、Mailgunなど）を使用してメールを送信します。

## .envファイルの設定

### 1. Gmail SMTPを使用する場合

```bash
# メール設定
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# 送信元メールアドレス
DEFAULT_FROM_EMAIL=noreply@salesmind.mind-bridge.tech
```

**Gmailアプリパスワードの作成方法：**
1. Googleアカウント設定 > セキュリティ > 2段階認証を有効化
2. アプリパスワードを生成
3. 生成された16文字のパスワードを`EMAIL_HOST_PASSWORD`に設定

### 2. SendGridを使用する場合

```bash
# メール設定
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key

# 送信元メールアドレス
DEFAULT_FROM_EMAIL=noreply@salesmind.mind-bridge.tech
```

**SendGridのセットアップ：**
1. SendGridアカウントを作成（https://sendgrid.com/）
2. APIキーを作成
3. APIキーを`EMAIL_HOST_PASSWORD`に設定

### 3. Mailgunを使用する場合

```bash
# メール設定
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=postmaster@your-domain.mailgun.org
EMAIL_HOST_PASSWORD=your-mailgun-password

# 送信元メールアドレス
DEFAULT_FROM_EMAIL=noreply@salesmind.mind-bridge.tech
```

**Mailgunのセットアップ：**
1. Mailgunアカウントを作成（https://www.mailgun.com/）
2. ドメインを追加
3. SMTP認証情報を取得
4. `EMAIL_HOST_USER`と`EMAIL_HOST_PASSWORD`を設定

### 4. AWS SESを使用する場合

```bash
# メール設定
EMAIL_HOST=email-smtp.region.amazonaws.com  # 例: email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-aws-access-key-id
EMAIL_HOST_PASSWORD=your-aws-secret-access-key

# 送信元メールアドレス
DEFAULT_FROM_EMAIL=noreply@salesmind.mind-bridge.tech
```

## 設定の確認

設定後、以下のコマンドでメール送信をテストできます：

```bash
docker compose exec web python manage.py shell
```

```python
from django.core.mail import send_mail
from django.conf import settings

send_mail(
    'SalesMind - テストメール',
    'これはテストメールです。',
    settings.DEFAULT_FROM_EMAIL,
    ['your-email@example.com'],
    fail_silently=False,
)
```

## 開発環境でMailHogを使用する場合

開発環境でMailHogを使用する場合は、`.env`ファイルに以下を追加：

```bash
USE_MAILHOG=True
```

これにより、メールはMailHogに送信され、`http://localhost:8025`で確認できます。

## トラブルシューティング

### メールが送信されない場合

1. `.env`ファイルの設定を確認
2. メールサービスの認証情報が正しいか確認
3. ファイアウォールでポート587がブロックされていないか確認
4. Gmailを使用する場合、アプリパスワードを使用しているか確認（通常のパスワードでは不可）

### Gmailでエラーが発生する場合

- 通常のパスワードでは認証できません。アプリパスワードを使用してください
- 2段階認証を有効化する必要があります

### メールが迷惑メールフォルダに入る場合

- SPF、DKIM、DMARCレコードをDNSに設定してください
- SendGridやMailgunを使用すると、これらの設定が自動的に行われます



