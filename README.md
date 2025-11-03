# SalesMind - AI営業思考トレーナー

## 概要

SalesMindは、営業担当者がAIと模擬商談を行い、SPIN思考（状況・問題・示唆・ニーズ）を鍛えるトレーニングアプリです。

## 技術スタック

- Backend: Django 5 + Django REST Framework
- AI: OpenAI GPT-4o-mini
- Database: PostgreSQL 16
- Infrastructure: Docker Compose

## セットアップ

### 必要な環境

- Docker Desktop
- Git

### 起動方法

1. リポジトリをクローン
```bash
git clone https://github.com/bushimaru55/salesmind.git
cd salesmind
```

2. 環境変数ファイルを作成
```bash
# .env.exampleをコピーして.envを作成
cp .env.example .env

# .envファイルを編集して以下を設定：
# - SECRET_KEY: Djangoのシークレットキー（自動生成可）
# - OPENAI_API_KEY: OpenAI APIキー
```

3. Docker Composeで起動
```bash
docker compose build
docker compose up -d
```

4. マイグレーション実行
```bash
docker compose exec web python manage.py migrate
```

5. スーパーユーザー作成（オプション）
```bash
docker compose exec web python manage.py createsuperuser
```

## APIエンドポイント

### 1. SPIN質問生成（認証不要）

```bash
POST http://localhost:8000/api/spin/generate/
Content-Type: application/json

{
  "industry": "IT",
  "value_proposition": "クラウド導入支援サービス",
  "customer_persona": "中堅IT企業のCTO",
  "customer_pain": "既存システムの保守コスト削減"
}
```

### 2. セッション開始（認証必須）

まず、ユーザーを作成してTokenを取得します。

```bash
# ユーザー作成とToken取得
docker compose exec web python manage.py shell -c "
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
user, _ = User.objects.get_or_create(username='testuser', defaults={'email': 'test@example.com'})
user.set_password('testpass123')
user.save()
token, _ = Token.objects.get_or_create(user=user)
print(f'Token: {token.key}')
"
```

```bash
POST http://localhost:8000/api/session/start/
Authorization: Token YOUR_TOKEN_HERE
Content-Type: application/json

{
  "industry": "IT",
  "value_proposition": "クラウド導入支援サービス",
  "customer_persona": "中堅IT企業のCTO",
  "customer_pain": "既存システムの保守コスト削減"
}
```

### 3. チャット（認証必須）

```bash
POST http://localhost:8000/api/session/chat/
Authorization: Token YOUR_TOKEN_HERE
Content-Type: application/json

{
  "session_id": "SESSION_UUID_HERE",
  "message": "現在のシステム運用体制について教えてください"
}
```

### 4. セッション終了・スコアリング（認証必須）

```bash
POST http://localhost:8000/api/session/finish/
Authorization: Token YOUR_TOKEN_HERE
Content-Type: application/json

{
  "session_id": "SESSION_UUID_HERE"
}
```

### 5. レポート取得（認証必須）

```bash
GET http://localhost:8000/api/report/1/
Authorization: Token YOUR_TOKEN_HERE
```

## 動作確認用スクリプト

### PowerShell（Windows）

```powershell
# 変数の設定
$baseUrl = "http://localhost:8000/api"
$token = "YOUR_TOKEN_HERE"

# 1. SPIN質問生成（認証不要）
$body = @{
    industry = "IT"
    value_proposition = "クラウド導入支援サービス"
    customer_persona = "中堅IT企業のCTO"
    customer_pain = "既存システムの保守コスト削減"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/spin/generate/" -Method POST -Body $body -ContentType "application/json"

# 2. セッション開始
$headers = @{
    Authorization = "Token $token"
    "Content-Type" = "application/json"
}
$body = @{
    industry = "IT"
    value_proposition = "クラウド導入支援サービス"
    customer_persona = "中堅IT企業のCTO"
    customer_pain = "既存システムの保守コスト削減"
} | ConvertTo-Json

$session = Invoke-RestMethod -Uri "$baseUrl/session/start/" -Method POST -Headers $headers -Body $body -ContentType "application/json"
$sessionId = $session.id
Write-Host "Session ID: $sessionId"

# 3. チャット
$body = @{
    session_id = $sessionId
    message = "現在のシステム運用体制について教えてください"
} | ConvertTo-Json

$chatResponse = Invoke-RestMethod -Uri "$baseUrl/session/chat/" -Method POST -Headers $headers -Body $body -ContentType "application/json"
$chatResponse.conversation | Select-Object -Last 2

# 4. セッション終了
$body = @{
    session_id = $sessionId
} | ConvertTo-Json

$finishResponse = Invoke-RestMethod -Uri "$baseUrl/session/finish/" -Method POST -Headers $headers -Body $body -ContentType "application/json"
$finishResponse | ConvertTo-Json -Depth 5

# 5. レポート取得
$reportId = $finishResponse.report_id
$report = Invoke-RestMethod -Uri "$baseUrl/report/$reportId/" -Method GET -Headers $headers
$report | ConvertTo-Json -Depth 5
```

### curl（Linux/Mac）

```bash
BASE_URL="http://localhost:8000/api"
TOKEN="YOUR_TOKEN_HERE"

# 1. SPIN質問生成
curl -X POST "$BASE_URL/spin/generate/" \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "IT",
    "value_proposition": "クラウド導入支援サービス",
    "customer_persona": "中堅IT企業のCTO",
    "customer_pain": "既存システムの保守コスト削減"
  }'

# 2. セッション開始
SESSION=$(curl -X POST "$BASE_URL/session/start/" \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "IT",
    "value_proposition": "クラウド導入支援サービス",
    "customer_persona": "中堅IT企業のCTO",
    "customer_pain": "既存システムの保守コスト削減"
  }' | jq -r '.id')

echo "Session ID: $SESSION"

# 3. チャット
curl -X POST "$BASE_URL/session/chat/" \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION\",
    \"message\": \"現在のシステム運用体制について教えてください\"
  }"

# 4. セッション終了
REPORT=$(curl -X POST "$BASE_URL/session/finish/" \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION\"
  }")

echo "$REPORT" | jq

# 5. レポート取得
REPORT_ID=$(echo "$REPORT" | jq -r '.report_id')
curl -X GET "$BASE_URL/report/$REPORT_ID/" \
  -H "Authorization: Token $TOKEN"
```

## 動作確認

### 1. サーバーが起動しているか確認

```bash
curl http://localhost:8000/admin/
```

### 2. コンテナの状態確認

```bash
docker compose ps
```

### 3. ログの確認

```bash
docker compose logs web
```

### 4. データベース確認

```bash
docker compose exec web python manage.py shell
```

## トラブルシューティング

### ポートが既に使用されている場合

`.env`ファイルでポートを変更するか、既存のプロセスを終了してください。

### データベース接続エラー

```bash
docker compose restart db
docker compose restart web
```

### 環境変数が読み込まれない

`.env`ファイルがルートディレクトリに存在することを確認してください。

## 開発

### コードの変更を反映

Docker Composeのvolumeマウントにより、コードの変更は自動的に反映されます。ただし、Djangoの設定変更などは再起動が必要です。

```bash
docker compose restart web
```

### マイグレーション

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

