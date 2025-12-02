# 多言語対応（i18n）設計仕様書

## 📋 概要

フロントエンド（閲覧画面）を多言語対応し、以下の5言語をサポートします：
- 日本語（ja）- デフォルト
- 英語（en）
- 繁体字（zh-TW）- 台湾・香港
- 簡体字（zh-CN）- 中国本土
- 韓国語（ko）

---

## 🎯 対応範囲

### 対象
- ✅ **フロントエンド（閲覧画面）のみ**
  - ヘッダー、ボタン、メッセージ、ラベル等すべてのUI要素
  - エラーメッセージ
  - 説明文

### 対象外
- ❌ バックエンドAPI（将来的に対応可能）
- ❌ Django Admin（英語のまま）
- ❌ AIが生成するSPIN質問・チャット応答（現状は日本語のみ）

---

## 🏗️ 実装方式の選択肢

### 方式A: 言語ファイル方式（推奨・フェーズ1）

**メリット:**
- シンプルで実装が簡単
- パフォーマンスが良い（静的ファイル）
- Git管理が容易
- 初期コストが低い

**デメリット:**
- 翻訳変更時にデプロイが必要
- 非技術者が編集しにくい

**実装:**
```javascript
// frontend/i18n/ja.js
const translations_ja = {
  "header.title": "🧠 SalesMind",
  "header.subtitle": "AI営業思考トレーナー - SPINメソッドで商談スキルを向上",
  "auth.login": "ログイン",
  "auth.register": "新規登録",
  "auth.username": "ユーザー名",
  "auth.password": "パスワード",
  // ... 他の翻訳
};
```

---

### 方式B: データベース管理方式（フェーズ2）

**メリット:**
- 管理画面から翻訳を編集可能
- デプロイ不要で翻訳を更新
- 非技術者でも編集可能
- バージョン管理・履歴追跡

**デメリット:**
- 実装コストが高い
- データベース依存
- 初期読み込みが若干遅い

**実装:**
- Djangoモデル: `Translation(key, language, text)`
- API: `GET /api/translations/{lang}/`
- Admin画面: 翻訳キーと各言語の翻訳を管理

---

## 📐 推奨実装フロー

### フェーズ1: 言語ファイル方式（MVPリリース前）
1. 言語切り替えUI追加
2. 翻訳ファイル作成（5言語）
3. 既存のハードコードテキストを置き換え
4. ブラウザ言語自動検出

**実装期間**: 2-3日

### フェーズ2: データベース管理方式（将来）
1. Translationモデル追加
2. Admin管理画面追加
3. 翻訳API実装
4. フロントエンドをAPI連携に変更

**実装期間**: 3-5日

---

## 🎨 UI設計

### 言語切り替えボタン
```
┌─────────────────────────────────────┐
│ 🧠 SalesMind          🌐 日本語 ▼  │
│                                      │
│   ドロップダウンで言語選択:          │
│   - 日本語                          │
│   - English                         │
│   - 繁體中文                        │
│   - 简体中文                        │
│   - 한국어                          │
└─────────────────────────────────────┘
```

**配置場所**: ヘッダー右上

---

## 📂 ディレクトリ構造（フェーズ1）

```
frontend/
├── i18n/
│   ├── i18n.js           # 言語切り替えロジック
│   ├── ja.js             # 日本語翻訳
│   ├── en.js             # 英語翻訳
│   ├── zh-TW.js          # 繁体字翻訳
│   ├── zh-CN.js          # 簡体字翻訳
│   └── ko.js             # 韓国語翻訳
├── index.html
└── app.js
```

---

## 🔧 実装詳細（フェーズ1）

### 1. i18n.js - コアロジック

```javascript
// i18n.js
class I18n {
    constructor() {
        this.currentLang = localStorage.getItem('language') || this.detectBrowserLanguage();
        this.translations = {};
        this.fallbackLang = 'ja';
    }

    // ブラウザ言語検出
    detectBrowserLanguage() {
        const lang = navigator.language || navigator.userLanguage;
        if (lang.startsWith('ja')) return 'ja';
        if (lang.startsWith('en')) return 'en';
        if (lang === 'zh-TW' || lang === 'zh-HK') return 'zh-TW';
        if (lang === 'zh-CN' || lang.startsWith('zh')) return 'zh-CN';
        if (lang.startsWith('ko')) return 'ko';
        return 'ja'; // デフォルト
    }

    // 翻訳を読み込み
    async loadTranslations(lang) {
        try {
            const response = await fetch(`/i18n/${lang}.js`);
            const module = await response.text();
            eval(module);
            this.translations[lang] = window[`translations_${lang}`];
            this.currentLang = lang;
            localStorage.setItem('language', lang);
        } catch (error) {
            console.error(`Failed to load translations for ${lang}`, error);
        }
    }

    // 翻訳取得
    t(key, params = {}) {
        let text = this.translations[this.currentLang]?.[key] 
                || this.translations[this.fallbackLang]?.[key] 
                || key;
        
        // パラメータ置換 {name} → actual value
        Object.keys(params).forEach(param => {
            text = text.replace(`{${param}}`, params[param]);
        });
        
        return text;
    }

    // 言語切り替え
    async changeLanguage(lang) {
        await this.loadTranslations(lang);
        this.updatePage();
    }

    // ページの全要素を更新
    updatePage() {
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            element.textContent = this.t(key);
        });
        
        document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            element.placeholder = this.t(key);
        });
    }
}

// グローバル変数として初期化
window.i18n = new I18n();
```

---

### 2. 翻訳ファイル例

#### ja.js（日本語）
```javascript
const translations_ja = {
    // ヘッダー
    "header.title": "🧠 SalesMind",
    "header.subtitle": "AI営業思考トレーナー - SPINメソッドで商談スキルを向上",
    
    // 認証
    "auth.login": "ログイン",
    "auth.register": "新規登録",
    "auth.username": "ユーザー名",
    "auth.password": "パスワード",
    "auth.email": "メールアドレス（オプション）",
    "auth.logout": "ログアウト",
    "auth.welcome": "ようこそ、{username}さん",
    
    // モード選択
    "mode.select.title": "診断モードを選択してください",
    "mode.simple.title": "簡易診断モード",
    "mode.simple.description": "手軽にSPIN質問を生成してトレーニングを開始できます",
    "mode.detailed.title": "詳細診断モード",
    "mode.detailed.description": "企業情報を取得して、より実践的なトレーニングが可能です",
    
    // ... 他の翻訳
};
```

#### en.js（英語）
```javascript
const translations_en = {
    // Header
    "header.title": "🧠 SalesMind",
    "header.subtitle": "AI Sales Training - Improve your sales skills with SPIN method",
    
    // Authentication
    "auth.login": "Login",
    "auth.register": "Sign Up",
    "auth.username": "Username",
    "auth.password": "Password",
    "auth.email": "Email (Optional)",
    "auth.logout": "Logout",
    "auth.welcome": "Welcome, {username}",
    
    // Mode Selection
    "mode.select.title": "Select Diagnosis Mode",
    "mode.simple.title": "Simple Mode",
    "mode.simple.description": "Start training quickly with SPIN questions",
    "mode.detailed.title": "Detailed Mode",
    "mode.detailed.description": "Get company information for more practical training",
    
    // ... other translations
};
```

---

### 3. HTMLの修正例

**変更前（ハードコード）:**
```html
<h1>🧠 SalesMind</h1>
<p class="subtitle">AI営業思考トレーナー - SPINメソッドで商談スキルを向上</p>
```

**変更後（i18n対応）:**
```html
<h1 data-i18n="header.title">🧠 SalesMind</h1>
<p class="subtitle" data-i18n="header.subtitle">AI営業思考トレーナー - SPINメソッドで商談スキルを向上</p>
```

**プレースホルダーの場合:**
```html
<input type="text" data-i18n-placeholder="auth.username" placeholder="ユーザー名">
```

---

### 4. 言語切り替えUIの追加

```html
<!-- ヘッダーに追加 -->
<div class="language-selector">
    <button class="lang-btn" onclick="toggleLanguageMenu()">
        🌐 <span id="currentLangDisplay">日本語</span> ▼
    </button>
    <div id="languageMenu" class="lang-menu" style="display: none;">
        <button onclick="changeLanguage('ja')">🇯🇵 日本語</button>
        <button onclick="changeLanguage('en')">🇺🇸 English</button>
        <button onclick="changeLanguage('zh-TW')">🇹🇼 繁體中文</button>
        <button onclick="changeLanguage('zh-CN')">🇨🇳 简体中文</button>
        <button onclick="changeLanguage('ko')">🇰🇷 한국어</button>
    </div>
</div>
```

---

## 📝 翻訳キーの命名規則

```
カテゴリ.サブカテゴリ.要素名
```

**例:**
- `auth.login` - 認証 > ログイン
- `mode.simple.title` - モード選択 > 簡易診断 > タイトル
- `chat.send.button` - チャット > 送信ボタン
- `error.network` - エラー > ネットワークエラー

---

## 🌐 翻訳が必要な要素（概算）

| カテゴリ | 要素数（概算） |
|---------|--------------|
| ヘッダー・認証 | 15 |
| モード選択 | 20 |
| 簡易診断フロー | 30 |
| 詳細診断フロー | 40 |
| チャット画面 | 25 |
| スコアリング・レポート | 35 |
| エラーメッセージ | 20 |
| **合計** | **約185要素** |

---

## 🎯 実装優先順位

### 高優先度（フェーズ1）
1. ✅ ヘッダー・認証
2. ✅ モード選択
3. ✅ 基本的なボタン・ラベル
4. ✅ エラーメッセージ

### 中優先度（フェーズ1）
5. チャット画面
6. スコアリング画面
7. レポート画面

### 低優先度（フェーズ2）
8. ヘルプ・説明文の詳細
9. Admin画面（将来）

---

## 📊 翻訳管理方式の比較

| 項目 | 言語ファイル | データベース |
|------|------------|------------|
| 実装難易度 | ⭐⭐ 簡単 | ⭐⭐⭐⭐ 複雑 |
| 更新の手軽さ | ⭐⭐ デプロイ必要 | ⭐⭐⭐⭐⭐ Admin画面で即更新 |
| パフォーマンス | ⭐⭐⭐⭐⭐ 高速 | ⭐⭐⭐ API呼び出し |
| Git管理 | ⭐⭐⭐⭐⭐ 容易 | ⭐⭐ 困難 |
| 非技術者の編集 | ⭐⭐ 困難 | ⭐⭐⭐⭐⭐ 容易 |
| 初期コスト | ⭐⭐⭐⭐⭐ 低い | ⭐⭐ 高い |

---

## 🚀 次のステップ

### すぐに実装する場合
1. i18n.jsの実装
2. 日本語翻訳ファイルの作成（既存テキストを抽出）
3. 英語翻訳ファイルの作成
4. HTMLに`data-i18n`属性を追加
5. 言語切り替えUIの追加

### 将来的に実装する場合
1. 現状のまま日本語で運用
2. ユーザーフィードバックを収集
3. 多言語対応の必要性を確認
4. フェーズ1を実装
5. 必要に応じてフェーズ2（データベース管理）へ移行

---

## 💡 推奨

**段階的実装を推奨:**
1. **現在**: 日本語のみ運用（問題なし）
2. **フェーズ1**: 言語ファイル方式で5言語対応（2-3日）
3. **フェーズ2**: データベース管理方式へ移行（必要に応じて）

**理由:**
- MVPとして日本語のみで十分
- 将来の拡張性を確保
- 段階的にコストをかけられる

---

## 📋 実装チェックリスト

### 準備
- [ ] AIdocsにこの設計書を保存
- [ ] 翻訳が必要な全要素をリストアップ
- [ ] 翻訳キーの命名規則を確定

### フェーズ1実装
- [ ] i18n.jsの作成
- [ ] 5言語の翻訳ファイル作成
- [ ] index.htmlに`data-i18n`属性追加
- [ ] app.jsにi18n初期化コード追加
- [ ] 言語切り替えUIの追加
- [ ] CSSスタイリング
- [ ] ブラウザ言語自動検出のテスト
- [ ] 全言語での動作確認

### フェーズ2実装（将来）
- [ ] Translationモデル作成
- [ ] マイグレーション実行
- [ ] Admin画面のカスタマイズ
- [ ] 翻訳APIの実装
- [ ] フロントエンドのAPI連携
- [ ] キャッシュ機構の実装

---

## 🎉 期待される効果

### ビジネス面
- ✅ グローバル展開が可能
- ✅ 対象市場の拡大（日本・米国・中華圏・韓国）
- ✅ 国際競争力の向上

### 技術面
- ✅ 保守性の向上（テキストが分離）
- ✅ 拡張性の確保（新言語追加が容易）
- ✅ コードの可読性向上

### ユーザー体験
- ✅ 母国語でのサービス利用
- ✅ グローバルサービスとしての信頼性
- ✅ アクセシビリティの向上

---

## 📞 次のアクション

多言語対応を実装する場合、以下をお知らせください：
1. **実装タイミング**: すぐ / 1ヶ月後 / 3ヶ月後 / 未定
2. **優先言語**: 全5言語 / 英語のみ / 特定の言語
3. **実装方式**: フェーズ1（言語ファイル） / フェーズ2（データベース）
4. **翻訳担当**: 自動翻訳 / ネイティブ翻訳者 / 混合

ご要望に応じて、実装を開始します！

