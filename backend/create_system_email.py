"""
システムドメインのメールアドレスを作成してテストメールを送信するスクリプト
"""
from django.contrib.auth.models import User
from spin.models import UserEmail, EmailVerificationToken
from spin.email_service import send_verification_email
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import re

# システムドメインからメールアドレスのドメイン部分を抽出
site_url = settings.SITE_URL
if site_url.startswith('https://'):
    domain = site_url.replace('https://', '')
elif site_url.startswith('http://'):
    domain = site_url.replace('http://', '')
else:
    domain = site_url

print(f"✓ システムドメイン: {domain}")

# テスト用のメールアドレスを作成（システムドメインを使用）
system_email = f"test@{domain}"

print(f"✓ システムメールアドレス: {system_email}")

# adminユーザーを取得
user = User.objects.filter(username='admin').first()
if not user:
    user = User.objects.first()

if not user:
    print("❌ ユーザーが見つかりません")
    exit(1)

print(f"✓ ユーザー: {user.username} (ID: {user.id})")

# システムドメインのメールアドレスをUserEmailに追加
user_email, created = UserEmail.objects.get_or_create(
    user=user,
    email=system_email,
    defaults={
        'is_verification_email': True,
        'verified': False
    }
)

if created:
    print(f"✓ 新しいシステムメールアドレスを追加しました: {system_email}")
else:
    print(f"✓ 既存のシステムメールアドレスを使用します: {system_email}")
    user_email.is_verification_email = True
    user_email.save()

# 他のメールアドレスのis_verification_emailをFalseにする
UserEmail.objects.filter(
    user=user,
    is_verification_email=True
).exclude(pk=user_email.pk).update(is_verification_email=False)

print(f"✓ 認証メール送信用に設定しました: {system_email}")

# 認証トークンを作成
expires_at = timezone.now() + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS)
verification_token = EmailVerificationToken.objects.create(
    user=user,
    expires_at=expires_at
)

print(f"✓ 認証トークンを作成しました: {verification_token.token}")

# メールを送信（送信先はjob.kouhei.onishi@gmail.comに変更）
print(f"📧 メール送信を開始します...")
print(f"   送信元: {system_email}")
print(f"   送信先: job.kouhei.onishi@gmail.com")

# 一時的に送信先を変更するため、email_serviceを直接呼び出さずに
# send_mailを使用してメールを送信
from django.core.mail import send_mail

try:
    verification_url = f"{settings.SITE_URL}/api/auth/verify-email/?token={verification_token.token}"
    
    subject = "SalesMind - メールアドレスの認証"
    
    html_message = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #132131;">SalesMind</h1>
            <h2>メールアドレスの認証</h2>
            <p>こんにちは、{user.username}さん</p>
            <p>SalesMindへのご登録ありがとうございます。</p>
            <p>以下のリンクをクリックして、メールアドレスを認証してください：</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" 
                   style="display: inline-block; padding: 12px 30px; background-color: #132131; color: #fff; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    メールアドレスを認証する
                </a>
            </div>
            <p>または、以下のURLをブラウザにコピー＆ペーストしてください：</p>
            <p style="word-break: break-all; color: #666; font-size: 12px;">{verification_url}</p>
            <p style="color: #999; font-size: 12px; margin-top: 30px;">
                このメールは、SalesMindへの登録リクエストにより送信されました。<br>
                このリクエストをしていない場合は、このメールを無視してください。
            </p>
            <p style="color: #999; font-size: 12px;">
                このリンクは24時間有効です。
            </p>
            <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
            <p style="color: #666; font-size: 11px; margin-top: 20px;">
                送信元: {system_email}<br>
                システムドメイン: {domain}
            </p>
        </div>
    </body>
    </html>
    """
    
    plain_message = f"""
SalesMind - メールアドレスの認証

こんにちは、{user.username}さん

SalesMindへのご登録ありがとうございます。

以下のリンクをクリックして、メールアドレスを認証してください：

{verification_url}

このメールは、SalesMindへの登録リクエストにより送信されました。
このリクエストをしていない場合は、このメールを無視してください。

このリンクは24時間有効です。

---
送信元: {system_email}
システムドメイン: {domain}
    """
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=system_email,  # 送信元をシステムドメインのメールアドレスに設定
        recipient_list=['job.kouhei.onishi@gmail.com'],  # 送信先
        html_message=html_message,
        fail_silently=False,
    )
    
    print(f"✅ メール送信に成功しました！")
    print(f"   送信元: {system_email}")
    print(f"   送信先: job.kouhei.onishi@gmail.com")
    print(f"   認証URL: {verification_url}")
    
except Exception as e:
    import traceback
    print(f"❌ メール送信に失敗しました: {e}")
    traceback.print_exc()



