#!/bin/bash
set -e

# データベース接続を待機（最大30秒）
echo "Waiting for database..."
python << 'PYEOF'
import os
import sys
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salesmind.settings')

try:
    import django
    django.setup()
    from django.db import connection
except ImportError:
    print("Error: Django not installed")
    sys.exit(1)

db_ready = False
for i in range(30):
    try:
        connection.ensure_connection()
        print("Database is ready!")
        db_ready = True
        break
    except Exception as e:
        if i < 29:
            print(f"Database is unavailable - sleeping ({i+1}/30): {e}")
            time.sleep(1)
        else:
            print(f"Database connection failed after 30 seconds: {e}")
            sys.exit(1)

if not db_ready:
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo "Failed to connect to database"
    exit 1
fi

# マイグレーション実行
echo "Running migrations..."
python manage.py migrate --noinput

# 静的ファイルの収集（本番環境用）
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# gunicornで起動
echo "Starting gunicorn..."
exec gunicorn salesmind.wsgi:application \
    --config gunicorn.conf.py \
    --bind 0.0.0.0:${PORT:-8000}

