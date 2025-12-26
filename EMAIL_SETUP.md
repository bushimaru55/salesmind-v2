# メール設定ガイド（本番環境）

## 概要
本番環境では、実際にメールを送信するためのSMTPサーバー設定が必要です。
開発環境ではMailHogを使用しますが、本番環境では実際のメールサーバーを使用します。

## 環境変数の設定

`.env`ファイルに以下の環境変数を設定してください：

```bash
# デバッグモード（False = 本番環境）
DEBUG=False

# メール設定
EMAIL_HOST=smtp.gmail.com          # SMTPサーバーのホスト名
EMAIL_PORT=587                     # SMTPポート（TLS用: 587, SSL用: 465）
EMAIL_USE_TLS=True                 # TLS使用（587ポートの場合はTrue）
EMAIL_USE_SSL=False                # SSL使用（465ポートの場合はTrue）
EMAIL_HOST_USER=your-email@gmail.com  # SMTP認証用のメールアドレス
EMAIL_HOST_PASSWORD=your-app-password # SMTP認証用のパスワード
DEFAULT_FROM_EMAIL=noreply@salesmind.mind-bridge.tech  # 送信元メールアドレス
```

## メールサービス別の設定例

### 1. Gmail SMTP

```bash
DEBUG=False
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password  # アプリパスワードを使用（通常のパスワードでは不可）
DEFAULT_FROM_EMAIL=noreply@salesmind.mind-bridge.tech
```

**Gmailアプリパスワードの作成方法：**
1. Googleアカウント設定 > セキュリティ > 2段階認証を有効化
2. アプリパスワードを生成
3. 生成された16文字のパスワードを`EMAIL_HOST_PASSWORD`に設定

### 2. SendGrid

```bash
DEBUG=False
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=apikey  # 固定値
EMAIL_HOST_PASSWORD=your-sendgrid-api-key  # SendGridのAPIキー
DEFAULT_FROM_EMAIL=noreply@salesmind.mind-bridge.tech
```

**SendGridのセットアップ：**
1. SendGridアカウントを作成（https://sendgrid.com/）
2. APIキーを作成
3. APIキーを`EMAIL_HOST_PASSWORD`に設定

### 3. Mailgun

```bash
DEBUG=False
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=postmaster@your-domain.mailgun.org
EMAIL_HOST_PASSWORD=your-mailgun-password
DEFAULT_FROM_EMAIL=noreply@salesmind.mind-bridge.tech
```

**Mailgunのセットアップ：**
1. Mailgunアカウントを作成（https://www.mailgun.com/）
2. ドメインを追加
3. SMTP認証情報を取得
4. `EMAIL_HOST_USER`と`EMAIL_HOST_PASSWORD`を設定

### 4. AWS SES (Simple Email Service)

```bash
DEBUG=False
EMAIL_HOST=email-smtp.region.amazonaws.com  # 例: email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-aws-access-key-id
EMAIL_HOST_PASSWORD=your-aws-secret-access-key
DEFAULT_FROM_EMAIL=noreply@salesmind.mind-bridge.tech
```

**AWS SESのセットアップ：**
1. AWS SESでドメインを認証
2. SMTP認証情報を取得
3. 認証情報を設定

## 設定の確認

設定後、以下のコマンドでメール送信をテストできます：

```bash
docker compose exec web python manage.py shell
```

```python
from django.core.mail import send_mail
from django.conf import settings

send_mail(
    'テストメール',
    'これはテストメールです。',
    settings.DEFAULT_FROM_EMAIL,
    ['your-email@example.com'],
    fail_silently=False,
)
```

## セキュリティに関する注意事項

1. **環境変数の保護**
   - `.env`ファイルをGitにコミットしないでください
   - `.gitignore`に`.env`を追加してください

2. **アプリパスワードの使用**
   - Gmailを使用する場合、通常のパスワードではなくアプリパスワードを使用してください
   - アプリパスワードは16文字のランダムな文字列です

3. **送信元メールアドレス**
   - `DEFAULT_FROM_EMAIL`は、使用するメールサービスのドメインと一致させる必要がある場合があります
   - SendGridやMailgunを使用する場合、認証済みのドメインを使用してください

## トラブルシューティング

### メールが送信されない

1. 環境変数が正しく設定されているか確認
2. SMTPサーバーに接続できるか確認
3. 認証情報が正しいか確認
4. ファイアウォールでポートがブロックされていないか確認

### Gmailでエラーが発生する

- 通常のパスワードでは認証できません。アプリパスワードを使用してください
- 2段階認証を有効化する必要があります

### メールが迷惑メールフォルダに入る

- SPF、DKIM、DMARCレコードをDNSに設定してください
- SendGridやMailgunを使用すると、これらの設定が自動的に行われます



