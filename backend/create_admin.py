#!/usr/bin/env python
"""テスト用スーパーユーザー作成スクリプト"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salesmind.settings')
django.setup()

from django.contrib.auth.models import User

username = 'admin'
password = 'admin123'
email = 'admin@test.local'

user, created = User.objects.get_or_create(
    username=username,
    defaults={
        'email': email,
        'is_superuser': True,
        'is_staff': True,
    }
)

if created:
    user.set_password(password)
    user.save()
    print(f'✅ スーパーユーザーを作成しました')
else:
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.save()
    print(f'✅ 既存のユーザーを更新しました')

print(f'ユーザー名: {username}')
print(f'パスワード: {password}')
print(f'メール: {email}')



