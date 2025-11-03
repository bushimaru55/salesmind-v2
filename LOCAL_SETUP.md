# ローカル環境での動作確認手順

## 前提条件
- Python 3.10以上がインストールされていること
- 必要なPythonパッケージがインストールされていること

## セットアップ手順

### 1. 環境変数の設定

`backend/.env`ファイルに以下を追加（既にある場合は更新）：

```env
USE_SQLITE=True
DEBUG=True
SECRET_KEY="wj)$ge1u)hx#133eh#b!z7c*+n4i$ix%6o#hq%ufc9pqe_s@g="
OPENAI_API_KEY=your-openai-api-key-here
```

**注意**: `OPENAI_API_KEY`は実際のAPIキーに置き換えてください。

### 2. 依存パッケージのインストール

```bash
cd backend
pip install -r requirements.txt
```

### 3. データベースのマイグレーション

```bash
# Windows PowerShellの場合
$env:USE_SQLITE="True"
python manage.py migrate

# Linux/Macの場合
export USE_SQLITE=True
python manage.py migrate
```

### 4. スーパーユーザーの作成（オプション）

管理画面を使用する場合：

```bash
$env:USE_SQLITE="True"
python manage.py createsuperuser
```

### 5. 開発サーバーの起動

```bash
$env:USE_SQLITE="True"
python manage.py runserver
```

サーバーが起動すると、以下のURLでアクセスできます：
- http://localhost:8000/
- http://localhost:8000/api/ - APIエンドポイント

### 6. フロントエンドの起動

別のターミナルで：

```bash
cd frontend
# 簡単なHTTPサーバーを起動（Python 3の場合）
python -m http.server 8080
```

ブラウザで http://localhost:8080/ にアクセスします。

## 動作確認

### 簡易診断モードの確認

1. ブラウザで http://localhost:8080/ にアクセス
2. ユーザー登録またはログイン
3. 「簡易診断モード」を選択
4. 業界、価値提案、顧客像を入力
5. 「診断開始」ボタンをクリック
6. セッションが作成され、チャット画面に遷移することを確認
7. ログを確認（`backend/logs/django.log`）して、`mode=simple`が含まれていることを確認

### 詳細診断モードの確認

1. ブラウザで http://localhost:8080/ にアクセス
2. ユーザー登録またはログイン
3. 「詳細診断モード」を選択
4. 企業URLと価値提案を入力
5. 「企業情報を取得」ボタンをクリック
6. 企業情報が取得されることを確認
7. 「診断開始」ボタンをクリック
8. セッションが作成され、チャット画面に遷移することを確認
9. 企業概要が表示されることを確認
10. ログを確認して、`mode=detailed`が含まれていることを確認

## ログの確認

### Djangoログ

```bash
tail -f backend/logs/django.log
```

または、PowerShellの場合：

```powershell
Get-Content backend/logs/django.log -Tail 50 -Wait
```

ログには以下のような情報が含まれます：

```
Session started: <session-id>, mode=simple, user=<username>
AI顧客応答生成を開始: Session <session-id>, mode=simple
スコアリング開始: Session <session-id>, mode=simple, メッセージ数: <count>
```

### ブラウザのログ

ブラウザの開発者ツール（F12）のConsoleタブでログを確認できます。

## トラブルシューティング

### データベースエラー

- `.env`ファイルに`USE_SQLITE=True`が設定されているか確認
- `db.sqlite3`ファイルの権限を確認

### マイグレーションエラー

```bash
# マイグレーション状態を確認
$env:USE_SQLITE="True"
python manage.py showmigrations

# マイグレーションを再実行
python manage.py migrate
```

### OpenAI API エラー

- `.env`ファイルの`OPENAI_API_KEY`が正しく設定されているか確認
- APIキーが有効か確認

### サーバーが起動しない

- ポート8000が既に使用されていないか確認
- 別のポートを指定：`python manage.py runserver 8001`

## データ整合性チェック

マイグレーション後に、データの整合性をチェック：

```bash
$env:USE_SQLITE="True"
python manage.py shell
```

シェル内で：

```python
from spin.models import Session

# 統計情報
total = Session.objects.count()
simple = Session.objects.filter(mode='simple').count()
detailed = Session.objects.filter(mode='detailed').count()

print(f"総セッション数: {total}")
print(f"簡易診断モード: {simple}")
print(f"詳細診断モード: {detailed}")

# 整合性チェック
simple_with_company = Session.objects.filter(company__isnull=False, mode='simple').count()
detailed_without_company = Session.objects.filter(company__isnull=True, mode='detailed').count()

print(f"整合性エラー（companyがあるのにmode=simple）: {simple_with_company}件")
print(f"整合性エラー（companyがないのにmode=detailed）: {detailed_without_company}件")
```

