# 企業URLスクレイピング機能 - 設計提案書

## 📋 概要

提案予定の企業情報をURLから自動収集し、その情報を元にSPIN法に基づいた営業提案の適合性をチェックする機能を追加します。

## 🎯 目的・価値

1. **営業効率化**: 手動で企業情報を入力する手間を削減
2. **提案精度向上**: 実際の企業情報に基づいたSPIN質問生成
3. **提案適合性チェック**: 企業の状況に応じた提案方法の最適化

## 🏗️ 機能設計

### 1. 企業URL入力・スクレイピング機能

**フロントエンド（UI）:**
- 企業URL入力欄を追加（ステップ1の前、ステップ0として追加）
- または、sitemap.xmlファイルアップロード機能
- スクレイピング実行ボタン
- スクレイピング結果表示エリア（企業情報のプレビュー）

**バックエンド（API）:**
- `POST /api/company/scrape/` - 企業URLから情報を取得（単一URL）
- `POST /api/company/scrape-from-sitemap/` - sitemap.xmlからURL一覧を取得し、各URLから情報を取得
- スクレイピング結果を一時保存（セッションまたはDB）

**sitemap.xml対応:**
- sitemap.xmlファイルをアップロード
- XMLパーサーでURL一覧を抽出
- 各URLから企業情報をスクレイピング
- 複数URLの情報を統合して企業情報を構築

### 2. スクレイピング技術選定

**推奨アプローチ:**

#### オプションA: BeautifulSoup + Requests（シンプル）
- **メリット**: 軽量、実装が簡単、静的HTML対応
- **デメリット**: JavaScript生成コンテンツに非対応
- **用途**: 企業の公式サイト、会社概要ページ

#### オプションB: Playwright（推奨）
- **メリット**: JavaScript実行対応、現代的なWebアプリ対応、Seleniumより高速
- **デメリット**: ブラウザエンジン必要（メモリ使用量増）
- **用途**: 動的コンテンツ、SPA対応

#### オプションC: 専用スクレイピングサービス
- **Scrapfly API**: 月額課金、プロキシ管理不要
- **Bright Data**: エンタープライズ向け
- **メリット**: レート制限対応、CAPTCHA回避、スケーラブル
- **デメリット**: コスト発生

**推奨**: 初期実装は **BeautifulSoup + Requests**、将来は **Playwright** に拡張

### 3. 収集する企業情報

以下の情報をスクレイピングして抽出：

1. **基本情報**
   - 会社名
   - 業界・事業領域
   - 所在地
   - 従業員数
   - 設立年

2. **事業情報**
   - 事業内容・サービス概要
   - 主要顧客・業界
   - ビジネスモデル

3. **課題・ペインポイント（推測可能な情報）**
   - 採用情報（人手不足の可能性）
   - ニュース・プレスリリース（課題のヒント）
   - 技術ブログ（技術的な課題）

4. **その他**
   - 企業URL（入力元URL）

### 4. SPIN提案適合性チェック機能

スクレイピングした企業情報を元に、以下の分析を実行：

**分析内容:**
1. **企業の状況把握（Situation）**
   - 業界・事業規模の確認
   - 現在の事業体制の把握

2. **潜在的な課題発見（Problem）**
   - 企業情報から推測される課題
   - 業界の一般的な課題との照合

3. **影響度の評価（Implication）**
   - 課題の影響範囲の推定
   - 緊急性の評価

4. **提案適合性スコア**
   - 価値提案と企業情報の適合度
   - SPIN各要素で提案できる確率
   - 推奨される提案アプローチ

**出力形式:**
```json
{
  "company_info": {
    "name": "株式会社○○",
    "industry": "IT",
    "business": "クラウドサービス",
    "employee_count": "50-100名"
  },
  "spin_suitability": {
    "situation": {
      "score": 85,
      "can_ask": true,
      "reason": "企業情報が充実している"
    },
    "problem": {
      "score": 70,
      "can_ask": true,
      "potential_problems": ["コスト削減", "効率化"]
    },
    "implication": {
      "score": 65,
      "can_ask": true,
      "estimated_impact": "中程度"
    },
    "need": {
      "score": 60,
      "can_ask": false,
      "reason": "価値提案との適合性が低い"
    }
  },
  "recommendations": {
    "proposal_approach": "まずは状況確認から始めることを推奨",
    "key_questions": [
      "現在のシステム運用体制は？",
      "コスト削減の優先度は？"
    ],
    "warnings": [
      "価値提案が企業の課題と直接関連していない可能性"
    ]
  }
}
```

## 📊 データモデル設計

### Companyモデル（新規追加）

```python
class Company(models.Model):
    SCRAPE_SOURCE_CHOICES = [
        ('url', '単一URL'),
        ('sitemap', 'sitemap.xml'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='companies')
    source_url = models.URLField(max_length=500)  # スクレイピング元URL（単一URL or sitemap.xml URL）
    scrape_source = models.CharField(max_length=20, choices=SCRAPE_SOURCE_CHOICES, default='url')
    company_name = models.CharField(max_length=200)
    industry = models.CharField(max_length=100, null=True, blank=True)
    business_description = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=200, null=True, blank=True)
    employee_count = models.CharField(max_length=100, null=True, blank=True)
    established_year = models.IntegerField(null=True, blank=True)
    scraped_urls = models.JSONField(null=True, blank=True)  # スクレイピングしたURL一覧（sitemap.xmlの場合）
    scraped_data = models.JSONField(null=True, blank=True)  # 生データ保存（複数URLのデータを統合）
    scraped_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### CompanyAnalysisモデル（新規追加）

```python
class CompanyAnalysis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='analysis')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='company_analyses')
    value_proposition = models.TextField()  # ユーザーが提案する価値提案
    spin_suitability = models.JSONField()  # SPIN適合性スコア
    recommendations = models.JSONField(null=True, blank=True)  # 提案推奨事項
    analysis_details = models.JSONField(null=True, blank=True)  # 詳細分析結果
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Sessionモデル拡張

```python
class Session(models.Model):
    # 既存フィールド...
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)  # 企業情報との関連付け
    company_analysis = models.ForeignKey(CompanyAnalysis, on_delete=models.SET_NULL, null=True, blank=True)  # 分析結果との関連付け
```

## 🔌 API仕様

### POST /api/company/scrape/

企業URLから情報をスクレイピングするエンドポイント（単一URL）。

**リクエスト:**
```json
{
  "url": "https://example-company.com/about",
  "value_proposition": "クラウド導入支援サービス"  // オプション、提案チェック用
}
```

**レスポンス（成功）:**
```json
{
  "company_id": "uuid",
  "company_info": {
    "name": "株式会社○○",
    "industry": "IT",
    "business": "クラウドサービス",
    ...
  },
  "scraped_at": "2024-01-15T10:30:00Z"
}
```

### POST /api/company/scrape-from-sitemap/

sitemap.xmlからURL一覧を取得し、各URLから企業情報をスクレイピングするエンドポイント。

**リクエスト（ファイルアップロード）:**
```
Content-Type: multipart/form-data

{
  "sitemap_file": <file>,  // sitemap.xmlファイル
  "value_proposition": "クラウド導入支援サービス"  // オプション
}
```

**または、sitemap.xmlのURLを指定:**

```json
{
  "sitemap_url": "https://example-company.com/sitemap.xml",
  "value_proposition": "クラウド導入支援サービス"  // オプション
}
```

**レスポンス（成功）:**
```json
{
  "company_id": "uuid",
  "scrape_source": "sitemap",
  "urls_found": 50,  // sitemap.xmlから見つかったURL数
  "urls_scraped": 45,  // 実際にスクレイピングできたURL数
  "company_info": {
    "name": "株式会社○○",
    "industry": "IT",
    "business": "クラウドサービス",
    ...
  },
  "scraped_urls": [
    "https://example-company.com/about",
    "https://example-company.com/services",
    ...
  ],
  "scraped_at": "2024-01-15T10:30:00Z"
}
```

### POST /api/company/analyze/

スクレイピングした企業情報を元に、SPIN提案適合性をチェックするエンドポイント。

**リクエスト:**
```json
{
  "company_id": "uuid",
  "value_proposition": "クラウド導入支援サービス"
}
```

**レスポンス（成功）:**
```json
{
  "analysis_id": "uuid",
  "spin_suitability": {
    "situation": { "score": 85, "can_ask": true, ... },
    "problem": { "score": 70, "can_ask": true, ... },
    "implication": { "score": 65, "can_ask": true, ... },
    "need": { "score": 60, "can_ask": false, ... }
  },
  "recommendations": {
    "proposal_approach": "...",
    "key_questions": [...],
    "warnings": [...]
  }
}
```

## 🤖 OpenAI活用方針

### 1. スクレイピングデータの整理・構造化

スクレイピングした生HTMLから、構造化された企業情報を抽出：
```python
def extract_company_info(html_content):
    prompt = f"""
    以下のHTMLから企業情報を抽出してください。
    
    HTML:
    {html_content[:5000]}  # 長い場合は分割
    
    以下のJSON形式で返してください：
    {{
      "company_name": "...",
      "industry": "...",
      "business_description": "...",
      "location": "...",
      "employee_count": "...",
      "potential_pain_points": ["課題1", "課題2"]
    }}
    """
    # OpenAI API呼び出し
```

### 2. SPIN提案適合性分析

企業情報と価値提案を元に、SPIN法に基づく提案適合性を評価：
```python
def analyze_spin_suitability(company_info, value_proposition):
    prompt = f"""
    以下の企業情報と価値提案を元に、SPIN法に基づく営業提案の適合性を分析してください。
    
    企業情報:
    {company_info}
    
    価値提案:
    {value_proposition}
    
    SPIN各要素（Situation, Problem, Implication, Need）について、
    この企業に対して提案できるかを評価してください。
    """
    # OpenAI API呼び出し
```

## 📁 実装ファイル構成

```
backend/
├── spin/
│   ├── models.py  # Company, CompanyAnalysisモデル追加
│   ├── serializers.py  # CompanySerializer, CompanyAnalysisSerializer追加
│   ├── views.py  # scrape_company, analyze_company エンドポイント追加
│   ├── urls.py  # URLルーティング追加
│   └── services/
│       ├── scraper.py  # スクレイピングロジック（新規）
│       ├── company_analyzer.py  # SPIN適合性分析（新規）
│       └── openai_client.py  # 既存（拡張）
```

## 🔧 実装フェーズ

### フェーズ1: 基本スクレイピング機能
- BeautifulSoup + Requestsで実装
- 基本的な企業情報抽出（会社名、業界、事業内容）
- データモデル追加・マイグレーション
- **sitemap.xmlパーサー実装**

### フェーズ2: sitemap.xml対応
- sitemap.xmlファイルアップロード機能
- sitemap.xml URL対応
- sitemap.xmlからURL一覧を抽出
- 複数URLからの情報統合機能

### フェーズ3: OpenAI連携
- スクレイピングデータの構造化
- SPIN提案適合性チェック機能
- 分析結果の表示

### フェーズ4: UI統合
- フロントエンドにURL入力欄追加
- **sitemap.xmlアップロード機能追加**
- スクレイピング結果表示
- 分析結果表示

### フェーズ5: 高度化
- Playwright対応（JavaScript生成コンテンツ）
- 複数ページからの情報収集（sitemap対応含む）
- キャッシュ機能（同じURLの再スクレイピング回避）

## ⚠️ 注意事項・制約

1. **スクレイピングの倫理・法的問題**
   - robots.txtの遵守
   - 利用規約の確認
   - レート制限の考慮
   - 個人情報の取り扱い

2. **技術的制約**
   - CAPTCHA対応が必要な場合
   - ログインが必要なページ
   - JavaScript生成コンテンツ

3. **パフォーマンス**
   - スクレイピング処理は非同期化を検討
   - タイムアウト設定
   - エラーハンドリング

4. **データ精度**
   - スクレイピング結果の精度は100%ではない
   - ユーザーによる修正機能も検討

## 💡 将来的な拡張

1. **複数ソース統合**
   - 企業URL + 会社情報サイト（例：東洋経済オンライン、企業IR情報）
   - SNS情報の活用（LinkedIn、Twitter）

2. **機械学習モデル**
   - 企業情報から課題を自動抽出するモデル
   - 提案適合性スコアの精度向上

3. **レコメンデーション機能**
   - 類似企業の提案アプローチを推薦
   - 過去の成功事例との照合

---

## 📝 確認事項

1. **スクレイピング技術**: BeautifulSoup + Requests で開始で良いか？
2. **収集する情報**: 上記リストで十分か？追加・削除したい項目は？
3. **提案チェック**: SPIN適合性スコアの出力形式で問題ないか？
4. **UI統合**: URL入力をステップ0として追加するか、既存フローに統合するか？

