#!/usr/bin/env python
"""
システムメールアドレスの初期データを作成するスクリプト

注意: emailフィールドはuniqueなので、同じメールアドレスで複数のpurposeは登録できません。
会員登録用もデフォルトと同じnoreply@を使うため、会員登録専用のレコードは作成せず、
デフォルトレコードを会員登録にも使用します。
"""
from spin.models import SystemEmailAddress

print("=== システムメールアドレスの初期データを作成 ===")

# デフォルト送信元（会員登録などすべての用途で使用）
obj, created = SystemEmailAddress.objects.get_or_create(
    email='noreply@salesmind.mind-bridge.tech',
    defaults={
        'name': 'SalesMind',
        'purpose': 'default',
        'is_active': True,
        'is_default': True,
        'description': 'デフォルトの送信元メールアドレス（会員登録、通知等すべての用途で使用）'
    }
)
if created:
    print(f"✓ 作成: {obj.email} ({obj.get_purpose_display()}) - デフォルト")
else:
    print(f"○ 既存: {obj.email} ({obj.get_purpose_display()})")

# サポート用（将来的に使用、現在は無効）
obj, created = SystemEmailAddress.objects.get_or_create(
    email='support@salesmind.mind-bridge.tech',
    defaults={
        'name': 'SalesMind サポート',
        'purpose': 'support',
        'is_active': False,  # まだメールアドレス未作成の場合
        'description': 'サポート問い合わせ用（要DKIM設定追加）'
    }
)
if created:
    print(f"✓ 作成: {obj.email} ({obj.get_purpose_display()}) - 無効")
else:
    print(f"○ 既存: {obj.email} ({obj.get_purpose_display()})")

print("\n=== 初期データの作成完了 ===")
print(f"登録済みシステムメールアドレス数: {SystemEmailAddress.objects.count()}")
print("\n※ 会員登録用メールは 'registration' 専用レコードではなく、")
print("  デフォルトレコードが自動的に使用されます。")

