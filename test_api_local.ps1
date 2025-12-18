# SalesMind API テストスクリプト（ローカル環境用）
# PowerShell用の動作確認スクリプト

$baseUrl = "http://localhost:8000/api"
$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "SalesMind API 動作確認スクリプト（ローカル環境）" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. サーバー接続確認
Write-Host "[1/7] サーバー接続確認..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/admin/" -Method GET -UseBasicParsing -TimeoutSec 5
    Write-Host "✓ サーバーは正常に起動しています" -ForegroundColor Green
} catch {
    Write-Host "✗ サーバーに接続できません。バックエンドサーバーが起動しているか確認してください。" -ForegroundColor Red
    Write-Host "  起動コマンド: cd backend && `$env:USE_SQLITE='True' && python manage.py runserver" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# 2. Token取得（ローカル環境用）
Write-Host "[2/7] 認証Token取得..." -ForegroundColor Yellow
try {
    Push-Location backend
    $env:USE_SQLITE="True"
    $tokenOutput = python manage.py shell -c "from django.contrib.auth.models import User; from rest_framework.authtoken.models import Token; user, _ = User.objects.get_or_create(username='testuser', defaults={'email': 'test@example.com'}); user.set_password('testpass123'); user.save(); token, _ = Token.objects.get_or_create(user=user); print(token.key)"
    Pop-Location
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
} catch {
    Write-Host "✗ Token取得エラー: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 3. SPIN質問生成（認証不要）
Write-Host "[3/7] SPIN質問生成テスト..." -ForegroundColor Yellow
try {
    $body = @{
        industry = "IT"
        value_proposition = "クラウド導入支援サービス"
        customer_persona = "中堅IT企業のCTO"
        customer_pain = "既存システムの保守コスト削減"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$baseUrl/spin/generate/" -Method POST -Body $body -ContentType "application/json"
    Write-Host "✓ SPIN質問生成成功" -ForegroundColor Green
    Write-Host "  生成された質問数: $($response.questions.Count)"
} catch {
    Write-Host "✗ SPIN質問生成に失敗: $_" -ForegroundColor Red
}
Write-Host ""

# 4. セッション開始（詳細診断モード）
Write-Host "[4/7] セッション開始テスト（詳細診断モード）..." -ForegroundColor Yellow
try {
    $body = @{
        industry = "IT"
        value_proposition = "クラウド導入支援サービス"
        customer_persona = "中堅IT企業のCTO"
        customer_pain = "既存システムの保守コスト削減"
        mode = "detailed"
    } | ConvertTo-Json
    
    $startResponse = Invoke-RestMethod -Uri "$baseUrl/session/start/" -Method POST -Headers $headers -Body $body -ContentType "application/json"
    $sessionId = $startResponse.session_id
    Write-Host "✓ セッション開始成功" -ForegroundColor Green
    Write-Host "  セッションID: $sessionId"
    Write-Host "  モード: $($startResponse.mode)"
    Write-Host "  初期成功率: $($startResponse.success_probability)%"
    Write-Host "  現在のSPIN段階: $($startResponse.current_spin_stage)"
} catch {
    Write-Host "✗ セッション開始に失敗: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 5. チャットテスト（SPIN段階管理・成功率補正機能のテスト）
Write-Host "[5/7] チャットテスト（SPIN段階管理・成功率補正機能）..." -ForegroundColor Yellow
try {
    # 最初のメッセージ（Situation段階）
    $body = @{
        session_id = $sessionId
        message = "現在のシステム運用体制について教えてください"
    } | ConvertTo-Json
    
    $chatResponse1 = Invoke-RestMethod -Uri "$baseUrl/session/chat/" -Method POST -Headers $headers -Body $body -ContentType "application/json"
    Write-Host "✓ チャット1回目成功" -ForegroundColor Green
    Write-Host "  成功率: $($chatResponse1.success_probability)%"
    Write-Host "  変動量: $($chatResponse1.success_delta)"
    Write-Host "  SPIN段階: $($chatResponse1.spin_stage)"
    Write-Host "  段階評価: $($chatResponse1.stage_evaluation)"
    Write-Host "  セッションSPIN段階: $($chatResponse1.session_spin_stage)"
    if ($chatResponse1.system_notes) {
        Write-Host "  システムメモ: $($chatResponse1.system_notes)"
    }
    Write-Host ""
    
    # 2回目のメッセージ（Problem段階への前進）
    Start-Sleep -Seconds 2
    $body = @{
        session_id = $sessionId
        message = "運用コストが高いと感じる具体的な課題はありますか？"
    } | ConvertTo-Json
    
    $chatResponse2 = Invoke-RestMethod -Uri "$baseUrl/session/chat/" -Method POST -Headers $headers -Body $body -ContentType "application/json"
    Write-Host "✓ チャット2回目成功" -ForegroundColor Green
    Write-Host "  成功率: $($chatResponse2.success_probability)%"
    Write-Host "  変動量: $($chatResponse2.success_delta)"
    Write-Host "  SPIN段階: $($chatResponse2.spin_stage)"
    Write-Host "  段階評価: $($chatResponse2.stage_evaluation)"
    Write-Host "  セッションSPIN段階: $($chatResponse2.session_spin_stage)"
    if ($chatResponse2.system_notes) {
        Write-Host "  システムメモ: $($chatResponse2.system_notes)"
    }
} catch {
    Write-Host "✗ チャットに失敗: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "  エラー詳細: $responseBody" -ForegroundColor Red
    }
}
Write-Host ""

# 6. セッション詳細取得（段階情報の確認）
Write-Host "[6/7] セッション詳細取得テスト..." -ForegroundColor Yellow
try {
    $sessionDetail = Invoke-RestMethod -Uri "$baseUrl/session/$sessionId/" -Method GET -Headers $headers
    Write-Host "✓ セッション詳細取得成功" -ForegroundColor Green
    Write-Host "  現在の成功率: $($sessionDetail.success_probability)%"
    Write-Host "  現在のSPIN段階: $($sessionDetail.current_spin_stage)"
    Write-Host "  メッセージ数: $($sessionDetail.messages.Count)"
    Write-Host "  最後の分析理由: $($sessionDetail.last_analysis_reason)"
} catch {
    Write-Host "✗ セッション詳細取得に失敗: $_" -ForegroundColor Red
}
Write-Host ""

# 7. セッション終了・スコアリング
Write-Host "[7/7] セッション終了・スコアリングテスト..." -ForegroundColor Yellow
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
Write-Host "  - フロントエンド: http://localhost:8000/index.html" -ForegroundColor Yellow
Write-Host ""

