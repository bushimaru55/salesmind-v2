# 企業情報の会話への活用ロジック説明

## 📋 概要

スクレイピングで取得した企業情報を営業担当者とAI顧客の会話に活用する仕組みを説明します。

## 🔄 現在のシステムフロー（実装済み）

### ステップ1: 企業情報の取得
1. **企業URL入力またはsitemap.xmlアップロード**
   - 営業担当者が企業の公式サイトURLを入力
   - または、sitemap.xmlファイルをアップロード
   - API: `POST /api/company/scrape/` または `POST /api/company/scrape-from-sitemap/`

2. **スクレイピング実行**
   - 企業サイトから以下の情報を自動抽出：
     - 会社名
     - 業界
     - 事業内容・サービス概要
     - 所在地
     - 従業員数
     - 設立年
   - 複数URLの場合は情報を統合

3. **企業情報の保存**
   - `Company`モデルに企業情報を保存
   - `scraped_data`フィールドに生データ（HTMLなど）も保存

### ステップ2: SPIN適合性分析（オプション）
1. **価値提案と企業情報の分析**
   - 営業担当者が価値提案を入力
   - API: `POST /api/company/analyze/`
   - OpenAIが企業情報と価値提案を分析：
     - Situation（状況確認）の適合性
     - Problem（問題発見）の可能性
     - Implication（示唆）の影響度
     - Need（ニーズ確認）の適合性
   - 各要素のスコアと提案推奨事項を生成

2. **分析結果の保存**
   - `CompanyAnalysis`モデルに分析結果を保存
   - 推奨される質問例や注意事項も含まれる

### ステップ3: セッション開始（現状：手動入力）
**現在の実装状況:**
- セッション開始時に、営業担当者が以下を手動で入力：
  - `industry`: 業界
  - `value_proposition`: 価値提案
  - `customer_persona`: 顧客像（オプション）
  - `customer_pain`: 顧客の課題（オプション）

**将来的な改善案（未実装）:**
- セッション開始時に`company_id`を指定
- 自動的に企業情報から以下を取得：
  - `industry` ← Company.industry
  - `customer_persona` ← Company.business_description + Company.company_name
  - `customer_pain` ← CompanyAnalysis推奨事項または推定課題
- `company`と`company_analysis`フィールドに関連付け

### ステップ4: チャット会話（AI顧客応答生成）

**現在の実装ロジック:**

```python
def generate_customer_response(session, conversation_history):
    """AI顧客の応答を生成"""
    
    # セッション情報から顧客人格を設定
    system_prompt = f"""
    あなたは以下の顧客を演じるAIです。
    
    業界: {session.industry}
    顧客像: {session.customer_persona or '一般的な企業'}
    課題・ペインポイント: {session.customer_pain or '未設定'}
    
    営業担当者の質問に対して、設定された顧客像に基づいて自然に応答する
    """
    
    # 会話履歴と合わせてOpenAI APIを呼び出し
    # → AI顧客の応答を生成
```

**企業情報を活用する場合の改善案:**

```python
def generate_customer_response(session, conversation_history):
    """AI顧客の応答を生成（企業情報活用版）"""
    
    # セッションに関連付けられた企業情報を取得
    company = session.company
    company_analysis = session.company_analysis
    
    if company:
        # 企業情報から詳細な顧客人格を構築
        customer_persona = build_persona_from_company(company, company_analysis)
        
        system_prompt = f"""
        あなたは以下の顧客を演じるAIです。
        
        会社名: {company.company_name}
        業界: {company.industry}
        事業内容: {company.business_description}
        従業員数: {company.employee_count}
        
        現在の状況:
        - {customer_persona.get('current_situation', '未設定')}
        
        潜在的な課題:
        - {customer_persona.get('potential_problems', '未設定')}
        
        営業担当者の質問に対して、上記の企業情報に基づいて、
        リアルで具体的な応答をしてください。
        """
    else:
        # 企業情報がない場合は従来通りの処理
        system_prompt = f"""
        業界: {session.industry}
        顧客像: {session.customer_persona or '一般的な企業'}
        """
    
    # OpenAI APIでAI顧客の応答を生成
```

## 🎯 企業情報活用の効果

### 1. **リアルな会話体験**
- **従来**: 一般的な「IT企業」として応答
- **改善後**: 具体的な企業情報（従業員数、事業内容など）に基づいた応答
- **例**: 「当社は従業員50名のSaaS企業で、主に中小企業向けのCRMサービスを提供しています。現在、サーバーコストの削減に課題を感じています」

### 2. **適切な課題の提示**
- **従来**: 営業担当者が推測した課題を基に会話
- **改善後**: スクレイピングで取得した実際の企業情報から推測される課題を反映
- **例**: 企業サイトに「採用情報」が多くある → 人手不足の課題がある可能性を示唆

### 3. **SPIN適合性に基づいた提案**
- **分析結果を活用**: SPIN各要素で「提案できる」と判定された場合、その要素に関する質問に対してより積極的に応答
- **例**: Need（ニーズ確認）のスコアが高い場合、価値提案に関連する質問に対してより詳細な回答を生成

### 4. **より正確なスコアリング**
- **スコアリング時**: 実際の企業情報と照合して、営業担当者の質問が企業の実情に合っているかを評価
- **例**: 営業担当者が「従業員数は？」と聞いた場合、実際の企業情報と照合して評価

## 📊 データフロー図

```
[営業担当者]
    ↓
[企業URL入力 / sitemap.xmlアップロード]
    ↓
[スクレイピング実行]
    ↓
[企業情報取得]
    ├─ Companyモデルに保存
    └─ 価値提案があれば分析実行
        └─ CompanyAnalysisモデルに保存
    ↓
[セッション開始]
    ├─ company_idを指定
    ├─ 企業情報を自動取得
    │   ├─ industry ← Company.industry
    │   ├─ customer_persona ← Company情報から構築
    │   └─ customer_pain ← CompanyAnalysis推奨事項
    └─ Session.company, Session.company_analysisに関連付け
    ↓
[チャット会話]
    ├─ 営業担当者の質問
    └─ AI顧客応答生成
        ├─ Session.company情報を参照
        ├─ Session.company_analysis情報を参照
        └─ よりリアルで具体的な応答を生成
    ↓
[スコアリング]
    ├─ 会話履歴を分析
    ├─ 実際の企業情報と照合
    └─ SPIN各要素を評価
```

## 🔧 実装が必要な改善点

### 1. セッション開始APIの拡張
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_session(request):
    """セッション開始（企業情報対応版）"""
    # company_idが指定されている場合
    if company_id := request.data.get('company_id'):
        company = Company.objects.get(id=company_id, user=request.user)
        
        # 企業情報から自動的にセッション情報を構築
        session_data = {
            'industry': company.industry or request.data.get('industry'),
            'value_proposition': request.data.get('value_proposition'),
            'customer_persona': build_persona_from_company(company),
            'customer_pain': extract_pain_from_analysis(company.analysis) if company.analysis else None,
            'company': company,
            'company_analysis': company.analysis if hasattr(company, 'analysis') else None,
        }
    else:
        # 従来通りの手動入力
        session_data = request.data
    
    # セッション作成
    session = Session.objects.create(**session_data)
```

### 2. AI顧客応答生成の拡張
```python
def generate_customer_response(session, conversation_history):
    """AI顧客応答生成（企業情報活用版）"""
    
    # 企業情報がある場合、詳細な情報を追加
    if session.company:
        company_info = format_company_info_for_chat(session.company)
        system_prompt = build_detailed_persona(session, company_info)
    else:
        system_prompt = build_basic_persona(session)
    
    # OpenAI API呼び出し
    ...
```

## 💡 まとめ

**現在の状態:**
- ✅ 企業情報の取得機能は実装済み
- ✅ SPIN適合性分析機能は実装済み
- ⚠️ セッション開始時に企業情報を自動取得する機能は未実装
- ⚠️ チャット時に企業情報を活用する機能は部分的に未実装

**将来的な活用:**
1. セッション開始時に`company_id`を指定 → 企業情報を自動取得してセッションに反映
2. チャット時に企業情報を参照 → よりリアルで具体的なAI顧客応答を生成
3. スコアリング時に企業情報と照合 → より正確な評価

これにより、営業担当者は実際の企業情報に基づいた、より実践的なトレーニングを受けることができます。

