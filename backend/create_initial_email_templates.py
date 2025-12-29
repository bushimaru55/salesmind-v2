#!/usr/bin/env python
"""
メールテンプレートの初期データを作成するスクリプト
"""
from spin.models import EmailTemplate, SystemEmailAddress

print("=== メールテンプレートの初期データを作成 ===")

# デフォルト送信元を取得
default_sender = SystemEmailAddress.objects.filter(is_default=True, is_active=True).first()

# 会員登録確認メールテンプレート
template, created = EmailTemplate.objects.get_or_create(
    name='registration_email',
    defaults={
        'display_name': '会員登録確認メール',
        'purpose': 'registration',
        'from_email': default_sender,
        'subject': '{site_name} - メールアドレスの確認',
        'body_text': '''こんにちは、{username}さん

{site_name}へのご登録ありがとうございます。

以下のリンクをクリックして、メールアドレスを認証してください：

{verification_url}

このメールは、{site_name}への登録リクエストにより送信されました。
このリクエストをしていない場合は、このメールを無視してください。

このリンクは24時間有効です。

---
{site_name} チーム
{site_url}
''',
        'body_html': '''<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #132131;">{site_name}</h1>
        <h2>メールアドレスの確認</h2>
        <p>こんにちは、{username}さん</p>
        <p>{site_name}へのご登録ありがとうございます。</p>
        <p>以下のリンクをクリックして、メールアドレスを認証してください：</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}" 
               style="display: inline-block; padding: 12px 30px; background-color: #132131; color: #fff; text-decoration: none; border-radius: 5px; font-weight: bold;">
                メールアドレスを認証する
            </a>
        </div>
        <p>または、以下のURLをブラウザにコピー&ペーストしてください：</p>
        <p style="word-break: break-all; color: #666; font-size: 12px;">{verification_url}</p>
        <p style="color: #999; font-size: 12px; margin-top: 30px;">
            このメールは、{site_name}への登録リクエストにより送信されました。<br>
            このリクエストをしていない場合は、このメールを無視してください。
        </p>
        <p style="color: #999; font-size: 12px;">
            このリンクは24時間有効です。
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="color: #999; font-size: 12px; text-align: center;">
            {site_name}<br>
            <a href="{site_url}" style="color: #132131;">{site_url}</a>
        </p>
    </div>
</body>
</html>''',
        'is_active': True,
        'available_variables': 'username, email, verification_url, site_name, site_url',
        'description': 'ユーザー登録時のメールアドレス確認用テンプレート'
    }
)

if created:
    print(f"✓ 作成: {template.display_name}")
else:
    print(f"○ 既存: {template.display_name}")

print("\n=== 初期データの作成完了 ===")
print(f"登録済みテンプレート数: {EmailTemplate.objects.count()}")


