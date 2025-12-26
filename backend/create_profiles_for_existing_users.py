"""
既存ユーザーにUserProfileを作成するスクリプト
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salesmind.settings')
django.setup()

from django.contrib.auth.models import User
from spin.models import UserProfile

print('=== 既存ユーザーのプロファイル作成 ===')
created = 0
for user in User.objects.all():
    profile, is_new = UserProfile.objects.get_or_create(user=user)
    if is_new:
        created += 1
        print(f'  ユーザー {user.username}: プロファイル作成')
    else:
        print(f'  ユーザー {user.username}: プロファイル既存')

print(f'\n合計 {created} 件のプロファイルを作成しました')
print(f'総プロファイル数: {UserProfile.objects.count()}')



