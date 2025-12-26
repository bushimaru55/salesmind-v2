# SalesMind 本番環境ガイド

## 🚀 本番環境の状態

現在、SalesMindは本番環境で稼働中です。

- **ドメイン**: https://salesmind.mind-bridge.tech
- **Django管理画面**: https://salesmind.mind-bridge.tech/admin/
- **API**: https://salesmind.mind-bridge.tech/api/

## ✅ メール認証システム

### メール送信設定

#### 1. 送信元メールアドレス
- デフォルト: `noreply@salesmind.mind-bridge.tech`
- 管理画面から送信元メールアドレスを追加・編集可能

#### 2. メールサーバー
- **Postfix**コンテナを使用（自前メールサーバー）
- DKIM署名により送信元認証を実施
- SPF/DKIM/DMARC設定済み

#### 3. DNS設定（確認済み）

**SPF**:
```
salesmind.mind-bridge.tech. TXT "v=spf1 ip4:160.251.173.73 ~all"
```

**DKIM**:
```
s1._domainkey.salesmind.mind-bridge.tech. TXT "v=DKIM1; h=sha256; k=rsa; p=MIIBIj..."
```

**DMARC**:
```
_dmarc.salesmind.mind-bridge.tech. TXT "v=DMARC1; p=none; adkim=r; aspf=r"
```

### メール認証フロー

#### 1. 新規登録
ユーザーが登録フォームで情報を入力すると：
- ユーザーアカウントが作成される（`is_active=False`状態）
- 認証トークンが生成される（有効期限24時間）
- 登録メールアドレスに認証メールが送信される

#### 2. メール認証
認証メール内のリンクをクリックすると：
- `/api/auth/verify-email/?token=<uuid>` にアクセス
- トークンが有効であれば、ユーザーが有効化される
- 成功時: `/email_verified.html` にリダイレクト（5秒後に自動ログインページへ）
- 失敗時: `/email_verification_error.html` にリダイレクト

#### 3. ログイン
メール認証完了後、ユーザーはログイン可能になります。

### テスト方法

#### 1. 新規ユーザー登録テスト
```bash
# テストスクリプトを実行
docker compose exec web python /app/test_registration_flow.py
```

#### 2. 認証URLの動作確認
```bash
# トークンを取得
docker compose exec web python manage.py shell -c "
from spin.models import EmailVerificationToken
from django.contrib.auth.models import User
user = User.objects.get(username='<username>')
token = EmailVerificationToken.objects.filter(user=user, used=False).first()
print(f'https://salesmind.mind-bridge.tech/api/auth/verify-email/?token={token.token}')
"

# curlでテスト
curl -X GET "https://salesmind.mind-bridge.tech/api/auth/verify-email/?token=<token>"
```

#### 3. メール送信ログ確認
```bash
# Postfixログ確認
docker compose logs mailserver --tail 50

# Djangoログ確認
docker compose logs web --tail 50 | grep -i email
```

## 🔒 セキュリティ設定

### Django設定（`backend/salesmind/settings.py`）

#### 本番環境での設定
```python
DEBUG = False  # .envでDEBUG=Falseに設定
SECRET_KEY = os.getenv("SECRET_KEY", "...")  # .envで強固なキーを設定
ALLOWED_HOSTS = ["salesmind.mind-bridge.tech", "localhost", "127.0.0.1"]

# HTTPS/SSL
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# セキュリティヘッダー
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

### 環境変数（`.env`）

重要な設定は`.env`ファイルで管理：
```bash
DEBUG=False
SECRET_KEY=your-very-strong-secret-key-here
ALLOWED_HOSTS=salesmind.mind-bridge.tech
POSTGRES_PASSWORD=your-strong-db-password
OPENAI_API_KEY=your-openai-api-key
```

## 📊 監視とログ

### ログ確認

#### 1. Webアプリケーションログ
```bash
docker compose logs web --tail 100 --follow
```

#### 2. メールサーバーログ
```bash
docker compose logs mailserver --tail 100 --follow
```

#### 3. Nginxログ
```bash
docker compose logs frontend --tail 100 --follow
```

### メールキュー確認
```bash
# キューの状態を確認
docker compose exec mailserver mailq

# キューを再送信
docker compose exec mailserver postqueue -f
```

## 🛠️ メンテナンス

### データベースバックアップ

#### 1. 手動バックアップ
```bash
docker compose exec db pg_dump -U postgres salesmind > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 2. リストア
```bash
cat backup_YYYYMMDD_HHMMSS.sql | docker compose exec -T db psql -U postgres salesmind
```

### Djangoマイグレーション

新しいモデル変更があった場合：
```bash
# マイグレーションファイル作成
docker compose exec web python manage.py makemigrations

# マイグレーション適用
docker compose exec web python manage.py migrate
```

### 静的ファイル更新
```bash
docker compose exec web python manage.py collectstatic --noinput
```

## 🚨 トラブルシューティング

### メールが届かない場合

#### 1. メール送信ログ確認
```bash
docker compose logs mailserver | grep -E "status=sent|status=bounced|status=deferred"
```

#### 2. Postfixキュー確認
```bash
docker compose exec mailserver mailq
```

#### 3. DNSレコード確認
```bash
dig +short TXT s1._domainkey.salesmind.mind-bridge.tech
dig +short TXT salesmind.mind-bridge.tech
dig +short TXT _dmarc.salesmind.mind-bridge.tech
```

### 認証エラーの場合

#### 1. トークンの有効性確認
```bash
docker compose exec web python manage.py shell -c "
from spin.models import EmailVerificationToken
token = EmailVerificationToken.objects.get(token='<token-uuid>')
print(f'有効: {token.is_valid()}')
print(f'使用済み: {token.used}')
print(f'有効期限: {token.expires_at}')
"
```

#### 2. ユーザーの状態確認
```bash
docker compose exec web python manage.py shell -c "
from django.contrib.auth.models import User
user = User.objects.get(username='<username>')
print(f'is_active: {user.is_active}')
print(f'email: {user.email}')
print(f'email_verified: {user.profile.email_verified}')
"
```

## 📝 管理画面

### アクセス
https://salesmind.mind-bridge.tech/admin/

### 主要機能

#### 1. システムメールアドレス管理
- パス: Admin > メールアドレス管理 > システムメールアドレス
- 送信元メールアドレスの追加・編集・削除
- デフォルト送信元の設定

#### 2. メールテンプレート管理
- パス: Admin > メールアドレス管理 > メールテンプレート
- メール件名・本文の編集
- テスト送信機能

#### 3. ユーザー管理
- パス: Admin > Spin > ユーザープロファイル
- ユーザーのメール認証状態確認
- 業種・営業経験・利用目的の確認

## 🔄 更新とデプロイ

### コード更新手順

```bash
# 1. リポジトリから最新コードを取得
git pull origin main

# 2. コンテナを再ビルド（必要な場合）
docker compose build

# 3. コンテナを再起動
docker compose down
docker compose up -d

# 4. マイグレーション実行（必要な場合）
docker compose exec web python manage.py migrate

# 5. 静的ファイル収集（必要な場合）
docker compose exec web python manage.py collectstatic --noinput

# 6. 状態確認
docker compose ps
docker compose logs --tail 50
```

## 📞 サポート

問題が発生した場合は、以下を確認してログを収集してください：

```bash
# すべてのコンテナの状態
docker compose ps

# すべてのログ
docker compose logs > logs_$(date +%Y%m%d_%H%M%S).txt

# データベース接続確認
docker compose exec web python manage.py check --database default
```

