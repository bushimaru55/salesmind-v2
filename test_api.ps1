# SalesMind API テストスクリプト
# PowerShell用の動作確認スクリプト

$baseUrl = "http://localhost:8000/api"
$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "SalesMind API 動作確認スクリプト" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. サーバー接続確認
Write-Host "[1/6] サーバー接続確認..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/admin/" -Method GET -UseBasicParsing
    Write-Host "✓ サーバーは正常に起動しています" -ForegroundColor Green
} catch {
    Write-Host "✗ サーバーに接続できません。Docker Composeが起動しているか確認してください。" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 2. Token取得（既存のテストユーザーを使用）
Write-Host "[2/6] 認証Token取得..." -ForegroundColor Yellow
$tokenOutput = docker compose exec -T web python manage.py shell -c "from django.contrib.auth.models import User; from rest_framework.authtoken.models import Token; user, _ = User.objects.get_or_create(username='testuser', defaults={'email': 'test@example.com'}); user.set_password('testpass123'); user.save(); token, _ = Token.objects.get_or_create(user=user); print(token.key)"
$token = ($tokenOutput | Select-String -Pattern '[a-zA-Z0-9]{40}' | Select-Object -First 1).Matches.Value
if ([string]::IsNullOrEmpty($token)) {
    Write-Host "✗ Tokenの取得に失敗しました" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Token取得成功: $($token.Substring(0, [Math]::Min(10, $token.Length)))..." -ForegroundColor Green
$headers = @{
    Authorization = "Token $token"
    "Content-Type" = "application/json"
}
Write-Host ""

# 3. SPIN質問生成（認証不要）
Write-Host "[3/6] SPIN質問生成テスト..." -ForegroundColor Yellow
try {
    $body = @{
        industry = "IT"
        value_proposition = "クラウド導入支援サービス"
        customer_persona = "中堅IT企業のCTO"
        customer_pain = "既存システムの保守コスト削減"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$baseUrl/spin/generate/" -Method POST -Body $body -ContentType "application/json"
    Write-Host "✓ SPIN質問生成成功" -ForegroundColor Green
    Write-Host "  生成された質問数:"
    Write-Host "  - Situation: $($response.questions.situation.Count)件"
    Write-Host "  - Problem: $($response.questions.problem.Count)件"
    Write-Host "  - Implication: $($response.questions.implication.Count)件"
    Write-Host "  - Need: $($response.questions.need.Count)件"
} catch {
    Write-Host "✗ SPIN質問生成に失敗: $_" -ForegroundColor Red
}
Write-Host ""

# 4. セッション開始
Write-Host "[4/6] セッション開始テスト..." -ForegroundColor Yellow
try {
    $body = @{
        industry = "IT"
        value_proposition = "クラウド導入支援サービス"
        customer_persona = "中堅IT企業のCTO"
        customer_pain = "既存システムの保守コスト削減"
    } | ConvertTo-Json
    
    $session = Invoke-RestMethod -Uri "$baseUrl/session/start/" -Method POST -Headers $headers -Body $body -ContentType "application/json"
    $sessionId = $session.id
    Write-Host "✓ セッション開始成功" -ForegroundColor Green
    Write-Host "  セッションID: $sessionId"
} catch {
    Write-Host "✗ セッション開始に失敗: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 5. チャット（AI顧客との対話）
Write-Host "[5/6] チャットテスト（AI顧客との対話）..." -ForegroundColor Yellow
try {
    $body = @{
        session_id = $sessionId
        message = "現在のシステム運用体制について教えてください"
    } | ConvertTo-Json
    
    $chatResponse = Invoke-RestMethod -Uri "$baseUrl/session/chat/" -Method POST -Headers $headers -Body $body -ContentType "application/json"
    Write-Host "✓ チャット成功" -ForegroundColor Green
    $lastMessages = $chatResponse.conversation | Select-Object -Last 2
    Write-Host "  会話履歴（最新2件）:"
    foreach ($msg in $lastMessages) {
        $roleName = if ($msg.role -eq 'salesperson') { "営業担当者" } else { "AI顧客" }
        $preview = $msg.message.Substring(0, [Math]::Min(50, $msg.message.Length))
        if ($msg.message.Length -gt 50) { $preview += "..." }
        Write-Host "  [$roleName]: $preview"
    }
} catch {
    Write-Host "✗ チャットに失敗: $_" -ForegroundColor Red
}
Write-Host ""

# 6. セッション終了・スコアリング
Write-Host "[6/6] セッション終了・スコアリングテスト..." -ForegroundColor Yellow
try {
    $body = @{
        session_id = $sessionId
    } | ConvertTo-Json
    
    $finishResponse = Invoke-RestMethod -Uri "$baseUrl/session/finish/" -Method POST -Headers $headers -Body $body -ContentType "application/json"
    Write-Host "✓ スコアリング成功" -ForegroundColor Green
    Write-Host "  スコア:"
    Write-Host "  - Situation: $($finishResponse.spin_scores.situation)点"
    Write-Host "  - Problem: $($finishResponse.spin_scores.problem)点"
    Write-Host "  - Implication: $($finishResponse.spin_scores.implication)点"
    Write-Host "  - Need: $($finishResponse.spin_scores.need)点"
    Write-Host "  - Total: $($finishResponse.spin_scores.total)点"
    Write-Host "  レポートID: $($finishResponse.report_id)"
    
    # レポート取得
    $reportId = $finishResponse.report_id
    $report = Invoke-RestMethod -Uri "$baseUrl/report/$reportId/" -Method GET -Headers $headers
    Write-Host "  レポート詳細取得成功" -ForegroundColor Green
} catch {
    Write-Host "✗ スコアリングに失敗: $_" -ForegroundColor Red
}
Write-Host ""

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "すべてのテストが完了しました！" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "ブラウザで確認:"
Write-Host "  - Admin: http://localhost:8000/admin/" -ForegroundColor Yellow
Write-Host ""
Write-Host "APIエンドポイント:"
Write-Host "  - SPIN質問生成: POST http://localhost:8000/api/spin/generate/" -ForegroundColor Yellow
Write-Host "  - セッション開始: POST http://localhost:8000/api/session/start/" -ForegroundColor Yellow
Write-Host "  - チャット: POST http://localhost:8000/api/session/chat/" -ForegroundColor Yellow
Write-Host "  - セッション終了: POST http://localhost:8000/api/session/finish/" -ForegroundColor Yellow
Write-Host "  - レポート取得: GET http://localhost:8000/api/report/{id}/" -ForegroundColor Yellow

